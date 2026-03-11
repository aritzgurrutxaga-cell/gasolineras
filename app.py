import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
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

# AJUSTES DE ESPACIADO
st.markdown("""
    <style>
        .block-container {padding-top: 2.8rem;}
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) {
            margin-top: 1.2rem;
        }
        div[data-testid="stSlider"] {margin-bottom: -2.2rem;}
        h1 {margin-top: -0.8rem; margin-bottom: 1.2rem;}
    </style>
""", unsafe_allow_html=True)

# Título adaptable
st.markdown(
    """
    <h1 style='text-align: center; font-size: clamp(22px, 7vw, 38px); white-space: nowrap; overflow: hidden;'>
        ⛽ Buscador Gasolineras
    </h1>
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
    
    try:
        r = session.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        lista = r.json()["ListaEESSPrecio"]
        pd.DataFrame(lista).to_csv(archivo_backup, index=False)
        return lista, datetime.datetime.now()
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            fecha = datetime.datetime.fromtimestamp(os.path.getmtime(archivo_backup))
            return df_rec.to_dict('records'), fecha
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- LÓGICA DE DATOS ---
datos, fecha_act = cargar_datos()

# Mover la fecha aquí (entre el título y el recuadro)
if fecha_act:
    st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.8rem; margin-bottom: 10px;'>Actualizado: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</div>", unsafe_allow_html=True)

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

    # --- BLOQUE RADIO ---
    radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)

    if 'tipo_orden' not in st.session_state:
        st.session_state.tipo_orden = "Diésel"
    col_orden = "Precio_Diesel" if st.session_state.tipo_orden == "Diésel" else "Precio_G95"

    # --- RESULTADOS ---
    if lat_ref and lon_ref:
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[
            (df["Distancia"] <= radio_km) & 
            ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
        ].sort_values(col_orden, na_position='last')

        st.divider()
        st.caption(f"Resultados ordenados por precio de: {st.session_state.tipo_orden}")
        
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

    # --- BLOQUE FINAL ---
    st.write("---")
    st.caption("Configuración de ordenación:")
    st.session_state.tipo_orden = st.radio(
        "Filtrar y ordenar por:", ["Diésel", "G95"], horizontal=True, label_visibility="collapsed",
        index=0 if st.session_state.tipo_orden == "Diésel" else 1
    )

else:
    st.error("Sin conexión a los datos oficiales.")
