import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
import pytz
from streamlit_js_eval import get_geolocation
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- ADAPTADOR SSL PARA EL MINISTERIO ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# --- AJUSTES DE ESTILO REFINADOS (CSS) ---
st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
        
        .header-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.2rem;
            margin-top: -1rem;
        }

        .header-icon { width: 40px; height: 40px; margin-bottom: 4px; }

        /* Título con escala reducida para asegurar ajuste en móviles */
        .header-title {
            color: #1E3A8A;
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            font-size: clamp(20px, 6.5vw, 32px);
            margin: 0px;
            line-height: 1.1;
            text-align: center;
            white-space: nowrap;
        }

        .header-subtitle {
            color: #10B981;
            font-family: 'Inter', sans-serif;
            font-weight: 400;
            font-size: clamp(12px, 3.5vw, 15px);
            margin-top: 2px;
            margin-bottom: 0.5rem;
            text-align: center;
        }

        /* Ajustes de espaciado específicos para compactar la UI */
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) { margin-top: 0.8rem; }
        div[data-testid="stSlider"] {margin-bottom: -1rem;}
        div[data-testid="stRadio"] {margin-bottom: -1.5rem;}
        hr {margin-top: 0.5rem; margin-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- CABECERA PROFESIONAL ---
st.markdown(
    """
    <div class='header-container'>
        <svg class='header-icon' viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 19V8H20V6H19V4H5V6H4V8H5V19H4V21H20V19H19Z" fill="#1E3A8A"/>
            <path d="M8 8H11V11H8V8Z" fill="#10B981"/>
            <path d="M13 8H16V11H13V8Z" fill="white"/>
            <path d="M8 13H11V16H8V13Z" fill="white"/>
            <path d="M13 13H16V16H13V13Z" fill="white"/>
            <path d="M7 6H17V17H7V6Z" stroke="#1E3A8A" stroke-width="2"/>
        </svg>
        <h1 class='header-title'>Buscador Gasolineras</h1>
        <p class='header-subtitle'>Ahorro Inteligente en Combustible</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# 2. Carga de Datos
@st.cache_data(ttl=3600, show_spinner="Actualizando Base de Datos, un momento por favor")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    archivo_backup = "gasolineras_backup.csv"
    tz_madrid = pytz.timezone('Europe/Madrid')
    
    try:
        r = session.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        lista = r.json()["ListaEESSPrecio"]
        pd.DataFrame(lista).to_csv(archivo_backup, index=False)
        return lista, datetime.datetime.now(tz_madrid)
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            mtime = os.path.getmtime(archivo_backup)
            fecha_utc = datetime.datetime.fromtimestamp(mtime, pytz.utc)
            return df_rec.to_dict('records'), fecha_utc.astimezone(tz_madrid)
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- FLUJO DE LA APP ---
datos, fecha_act = cargar_datos()

# Log de actualización (Compacto y centrado)
if fecha_act:
    st.markdown(f"<div style='text-align: center; color: #9CA3AF; font-size: 0.75rem; margin-top: -8px; margin-bottom: 12px;'>Datos actualizados: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')} (Madrid)</div>", unsafe_allow_html=True)

if datos:
    df = pd.DataFrame(datos)
    # Limpieza numérica
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    # Localización GPS
    loc = get_geolocation()
    lat_gps, lon_gps, muni_gps = None, None, None

    if loc and 'coords' in loc:
        lat_gps = loc['coords']['latitude']
        lon_gps = loc['coords']['longitude']
        df["dist_temp"] = calcular_distancia(lat_gps, lon_gps, df["lat_num"], df["lon_num"])
        muni_gps = df.sort_values("dist_temp").iloc[0]["Municipio"]

    # --- BLOQUE UBICACIÓN ---
    with st.container(border=True):
        idx = municipios_unicos.index(muni_gps) if muni_gps in municipios_unicos else None
        municipio_manual = st.selectbox("📍 Ubicación:", options=municipios_unicos, index=idx)
        
        if lat_gps and (municipio_manual == muni_gps or municipio_manual is None):
            lat_ref, lon_ref = lat_gps, lon_gps
            st.success("✅ GPS Activo")
        elif municipio_manual:
            ref = df[df["Municipio"] == municipio_manual].iloc[0]
            lat_ref, lon_ref = ref["lat_num"], ref["lon_num"]
        else:
            lat_ref, lon_ref = None, None
            st.info("⌛ Esperando ubicación...")

    # --- BLOQUE CONFIGURACIÓN ---
    radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)
    tipo_combustible = st.radio("Resultados ordenados por precio de:", ["Diésel", "G95"], horizontal=True)
    col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

    # --- RESULTADOS ---
    if lat_ref and lon_ref:
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        
        # Filtro: radio + que tenga al menos un precio
        res = df[
            (df["Distancia"] <= radio_km) & 
            ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
        ].sort_values(col_orden, na_position='last')

        st.divider()
        
        if not res.empty:
            for _, g in res.head(20).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([2.4, 1.6])
                    with col_info:
                        st.write(f"### {g['Rótulo']} - {g['Municipio']}")
                        p_diesel = f"{g['Precio Gasoleo A']} €" if pd.notnull(g['Precio_Diesel']) else "N/A"
                        p_g95 = f"{g['Precio Gasolina 95 E5']} €" if pd.notnull(g['Precio_G95']) else "N/A"
                        st.write(f"⛽ **D:** {p_diesel} | **G95:** {p_g95}")
                        st.caption(f"📍 {g['Distancia']:.2f} km | {g['Dirección']}")
                    with col_btn:
                        # Enlace directo a Google Maps
                        url_map = f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}"
                        st.link_button("📍 Navegar", url_map, use_container_width=True)
        else:
            st.warning("No hay resultados en este radio.")
else:
    st.error("Sin conexión a los datos oficiales.")
