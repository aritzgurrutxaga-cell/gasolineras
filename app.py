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

# --- ADAPTADOR SSL ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="Buscador Gasolineras", page_icon="⛽", layout="centered")

# --- CSS: DISEÑO CHULO Y AJUSTE MILIMÉTRICO ---
st.markdown("""
    <style>
        /* 1. Bajar el contenido para que no se pegue al marco superior del móvil */
        .block-container {padding-top: 3rem; padding-bottom: 0rem;}
        
        /* 2. Diseño del Título: Degradado profesional y forzado a una línea */
        .cool-title {
            text-align: center;
            font-family: 'Inter', system-ui, sans-serif;
            font-weight: 900;
            /* Fórmula restrictiva: mínimo 16px, ideal 5.5% del ancho, máximo 32px */
            font-size: clamp(16px, 5.5vw, 32px); 
            white-space: nowrap; 
            overflow: hidden; 
            margin-top: 0;
            margin-bottom: 0.2rem;
            letter-spacing: -0.5px;
            /* Efecto Degradado de Azul Marino a Verde Esmeralda */
            background: linear-gradient(90deg, #1E3A8A, #059669);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* 3. Ajustes de compresión para el resto de elementos */
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) { margin-top: 1rem; }
        div[data-testid="stSlider"] {margin-bottom: -1rem;}
        div[data-testid="stRadio"] {margin-bottom: -1rem;}
    </style>
""", unsafe_allow_html=True)

# --- CABECERA DE DISEÑO ---
st.markdown("<h1 class='cool-title'>Buscador Gasolineras</h1>", unsafe_allow_html=True)

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

datos, fecha_act = cargar_datos()

# Fecha de actualización con un margen refinado respecto al nuevo título
if fecha_act:
    st.markdown(f"<p style='text-align: center; color: #6B7280; font-size: 0.8rem; margin-top: 0; margin-bottom: 1.5rem;'>Actualizado: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</p>", unsafe_allow_html=True)

if datos:
    df = pd.DataFrame(datos)
    df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
    df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
    df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
    df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
    
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    loc = get_geolocation()
    lat_gps, lon_gps, muni_gps = None, None, None

    if loc and 'coords' in loc:
        lat_gps = loc['coords']['latitude']
        lon_gps = loc['coords']['longitude']
        df["dist_temp"] = calcular_distancia(lat_gps, lon_gps, df["lat_num"], df["lon_num"])
        muni_gps = df.sort_values("dist_temp").iloc[0]["Municipio"]

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

    radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)
    
    tipo_combustible = st.radio(
        "Resultados ordenados por precio de:", 
        ["Diésel", "G95"], 
        horizontal=True
    )
    col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

    if lat_ref and lon_ref:
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[(df["Distancia"] <= radio_km) & ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))].sort_values(col_orden, na_position='last')

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
                        url_map = f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}"
                        st.link_button("📍 Navegar", url_map, use_container_width=True)
        else:
            st.warning("No hay resultados en este radio.")
else:
    st.error("Sin conexión a los datos oficiales.")
