import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
from streamlit_js_eval import get_geolocation, streamlit_js_eval
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="gasolina.eus", page_icon="⛽")

st.markdown("""
    <style>
        header {visibility: hidden;}
        .titulo-app {
            text-align: center; font-size: 40px; font-weight: 800;
            color: #ff4b4b; margin-bottom: 20px;
        }
        /* Botón Inicial: Serio y Minimalista */
        div.stButton > button:first-child {
            min-height: 100px; border-radius: 15px;
            background-color: #d32f2f; color: white;
            font-size: 20px; font-weight: bold; border: none;
            width: 100%; display: flex; flex-direction: column;
        }
        /* Ajuste de altura del selector de municipio */
        div[data-baseweb="select"] > div {
            min-height: 60px !important; border-radius: 12px !important;
        }
        .info-gps { text-align: center; font-size: 14px; opacity: 0.8; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- MEMORIA Y DATOS ---
if 'municipio' not in st.session_state: st.session_state.municipio = None
if 'gps_activado' not in st.session_state: st.session_state.gps_activado = False

@st.cache_data(ttl=3600)
def cargar_datos():
    try:
        url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
        r = requests.get(url, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except: return None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

raw_data = cargar_datos()
if not raw_data:
    st.error("Error de conexión con el Ministerio.")
    st.stop()

df = pd.DataFrame(raw_data)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios = sorted(list(set([str(g["Municipio"]) for g in raw_data])))

# ==========================================
# FLUJO DE PANTALLAS
# ==========================================

st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)

# PANTALLA 1: INICIO
if not st.session_state.municipio and not st.session_state.gps_activado:
    if st.button("📍 BUSCAR GASOLINERAS"):
        st.session_state.gps_activado = True
        st.rerun()
    st.markdown("<div class='info-gps'>Es necesaria la ubicación para empezar</div>", unsafe_allow_html=True)
    st.stop()

# PANTALLA 2: PROCESO GPS O SELECCIÓN
if st.session_state.gps_activado and not st.session_state.municipio:
    loc = get_geolocation()
    if loc and 'coords' in loc:
        lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
        df["dist_tmp"] = calcular_distancia(lat, lon, df["lat_num"], df["lon_num"])
        st.session_state.municipio = df.sort_values("dist_tmp").iloc[0]["Municipio"]
        st.rerun()
    else:
        st.write("📍 Escribe tu municipio:")
        m_sel = st.selectbox("muni", options=municipios, index=None, placeholder="Escribe aquí...", label_visibility="collapsed")
        if m_sel:
            st.session_state.municipio = m_sel
            st.rerun()
        st.stop()

# PANTALLA 3: RESULTADOS
muni_ref = st.session_state.municipio
fila_m = df[df["Municipio"] == muni_ref].iloc[0]
lat_r, lon_r = fila_m["lat_num"], fila_m["lon_num"]

with st.expander("⚙️ Ajustes de búsqueda"):
    muni_cambio = st.selectbox("Cambiar municipio:", options=municipios, index=municipios.index(muni_ref))
    km = st.select_slider("Radio (km):", options=[5, 10, 20, 50], value=5)
    tipo = st.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
    if st.button("Aplicar cambios"):
        st.session_state.municipio = muni_cambio
        st.rerun()

col_p = "Precio_Diesel" if tipo == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_r, lon_r, df["lat_num"], df["lon_num"])
res = df[(df["Distancia"] <= km) & (df[col_p].notna())].sort_values(col_p)

st.info(f"📍 {muni_ref} | {km} km | {tipo}")

for _, g in res.head(15).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write(f"**{g['Rótulo']}**")
            st.write(f"{g[col_p]} €/L ({tipo})")
            st.caption(f"A {g['Distancia']:.2f} km")
        with c2:
            st.link_button("🗺️ Ir", f"https://www.google.com/maps?q={g['lat_num']},{g['lon_num']}")
