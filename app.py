import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
from streamlit_js_eval import get_geolocation, streamlit_js_eval
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- FUNCIONES DE APOYO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="gasolina.eus", page_icon="⛽", layout="centered")

# --- CSS MEJORADO PARA MÓVIL ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 10vh !important; }
        header {visibility: hidden !important;}
        .titulo-app {
            text-align: center; font-size: clamp(30px, 9vw, 45px); 
            font-weight: 800; margin-bottom: 1.5rem; color: #d32f2f;
            letter-spacing: -1px;
        }
        .resumen-filtros {
            text-align: center; font-size: 0.9rem; margin-bottom: 1rem; 
            padding: 8px; border-radius: 8px; border: 1px solid #444;
            background-color: rgba(255,255,255,0.05);
        }
        /* Botón Gigante Inicial */
        div[data-testid="stButton"] button[kind="primary"] {
            min-height: 120px !important; border-radius: 16px !important;
            background-color: #d32f2f !important; color: white !important;
            width: 100% !important; border: none !important;
        }
        div[data-testid="stButton"] button[kind="primary"] p {
            font-size: 1.6rem !important; font-weight: 800 !important;
        }
        /* Tarjetas de gasolineras */
        .stMetric { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- ESTADO DE LA SESIÓN ---
if 'solicitar_gps' not in st.session_state: st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state: st.session_state.municipio_guardado = None
if 'radio_km' not in st.session_state: st.session_state.radio_km = 5
if 'tipo_combustible' not in st.session_state: st.session_state.tipo_combustible = "Diésel"

# Recuperar del LocalStorage (JS)
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# --- CARGA DE DATOS (MINISTERIO) ---
@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    try:
        r = session.get(url, timeout=20)
        return r.json()["ListaEESSPrecio"]
    except: return None

datos = cargar_datos()
if not datos:
    st.error("Error de conexión con el servidor de precios. Reintenta en unos segundos.")
    st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# --- LÓGICA DE GEOLOCALIZACIÓN (PROTEGIDA) ---
lat_gps, lon_gps = None, None
if st.session_state.solicitar_gps and not st.session_state.municipio_guardado:
    loc = get_geolocation()
    if loc and 'coords' in loc:
        lat_gps = loc['coords'].get('latitude')
        lon_gps = loc['coords'].get('longitude')
    elif loc and 'error' in loc:
        st.error("Permiso de ubicación denegado.")
        st.session_state.solicitar_gps = False
    else:
        st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
        st.info("🌐 Esperando respuesta del GPS... Acepta el permiso en tu navegador.")
        st.stop()

# --- PANTALLA A: BIENVENIDA ---
if not (lat_gps or st.session_state.municipio_guardado) and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    if st.button("📍 Mostrar gasolineras", type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.stop()

# --- PANTALLA B: SELECCIÓN MANUAL (SI FALLA GPS) ---
if not lat_gps and not st.session_state.municipio_guardado:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    st.subheader("Selecciona tu ubicación")
    muni_sel = st.selectbox("Municipio:", options=municipios_unicos, index=None, placeholder="Escribe para buscar...")
    if st.button("✅ Confirmar municipio", use_container_width=True):
        if muni_sel:
            st.session_state.municipio_guardado = muni_sel
            streamlit_js_eval(js_expressions=f"parent.window.localStorage.setItem('muni_gasolineras', '{muni_sel}')")
            st.rerun()
    st.stop()

# --- PANTALLA C: RESULTADOS ---
st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)

# Punto de referencia
if lat_gps:
    lat_ref, lon_ref = lat_gps, lon_gps
    df["dist_temp"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
else:
    muni_ref = st.session_state.municipio_guardado
    fila = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila["lat_num"], fila["lon_num"]

# Menú de Ajustes
with st.expander("⚙️ Ajustar filtros"):
    n_muni = st.selectbox("Municipio:", options=municipios_unicos, index=municipios_unicos.index(muni_ref))
    n_radio = st.select_slider("Radio de búsqueda (km):", options=[2, 5, 10, 20, 50], value=st.session_state.radio_km)
    n_tipo = st.radio("Combustible:", ["Diésel", "G95"], index=0 if st.session_state.tipo_combustible == "Diésel" else 1, horizontal=True)
    
    if st.button("🔍 Actualizar resultados", use_container_width=True):
        st.session_state.municipio_guardado = n_muni
        st.session_state.radio_km = n_radio
        st.session_state.tipo_combustible = n_tipo
        # Al cambiar manualmente, desactivamos GPS para que mande el municipio elegido
        st.session_state.solicitar_gps = False 
        st.rerun()

# Procesamiento de datos
col_orden = "Precio_Diesel" if st.session_state.tipo_combustible == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[(df["Distancia"] <= st.session_state.radio_km) & (df[col_orden].notna())].sort_values(col_orden)

# Cabecera de resultados
st.markdown(f"<div class='resumen-filtros'>📍 {muni_ref} | 🚗 {st.session_state.radio_km}km | ⛽ {st.session_state.tipo_combustible}</div>", unsafe_allow_html=True)

if res.empty:
    st.warning("No hay gasolineras cercanas. Intenta ampliar el radio en los ajustes.")
else:
    for _, g in res.head(15).iterrows():
        with st.container(border=True):
            col_txt, col_btn = st.columns([0.7, 0.3], vertical_alignment="center")
            with col_txt:
                st.markdown(f"**{g['Rótulo']}**")
                precio = g[col_orden]
                st.markdown(f"### {precio:.3f} €/L")
                st.caption(f"{g['Dirección'].title()} ({g['Distancia']:.1f} km)")
            with col_btn:
                # URL Universal compatible con iOS/Android
                maps_url = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                st.link_button("🗺️ Ver", maps_url, use_container_width=True)

st.divider()
st.caption("Datos actualizados: " + datetime.datetime.now().strftime("%H:%M"))
