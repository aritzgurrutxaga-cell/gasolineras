import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
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

# --- CSS ESTRUCTURAL ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 10vh !important; }
        header {visibility: hidden !important;}
        .titulo-app {
            text-align: center; font-size: clamp(32px, 10vw, 48px); 
            font-weight: 800; margin-bottom: 1.5rem; color: #d32f2f;
        }
        .resumen-filtros {
            text-align: center; font-size: 0.95rem; margin-bottom: 1rem; 
            padding: 10px; border-radius: 8px; border: 1px solid #444;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            min-height: 120px !important; border-radius: 16px !important;
            background-color: #d32f2f !important; color: white !important;
            width: 100% !important; font-size: 1.5rem !important; font-weight: 800 !important;
        }
        div[data-testid="stButton"] button[kind="primary"]::after {
            content: "Pulsa para buscar gasolineras cercanas";
            font-size: 0.9rem; font-weight: 400; display: block; margin-top: 5px;
        }
        /* Estilo para las tarjetas */
        .card-price { font-size: 1.2rem; font-weight: bold; color: #d32f2f; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'solicitar_gps' not in st.session_state: st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state: st.session_state.municipio_guardado = None
if 'gps_fallido' not in st.session_state: st.session_state.gps_fallido = False
if 'radio_km' not in st.session_state: st.session_state.radio_km = 5
if 'tipo_combustible' not in st.session_state: st.session_state.tipo_combustible = "Diésel"

# LocalStorage
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# CARGA DE DATOS
@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    try:
        r = session.get(url, timeout=25)
        return r.json()["ListaEESSPrecio"]
    except: return None

datos = cargar_datos()
if not datos:
    st.error("Error al conectar con el Ministerio. Reintenta en unos minutos.")
    st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# Lógica de GPS
js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")

# --- PANTALLA 1: INICIO ---
if not (estado_permiso == "granted" or st.session_state.municipio_guardado) and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    if st.button("📍 Mostrar gasolineras", type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.stop()

# Obtención de coordenadas
lat_gps, lon_gps = None, None
if st.session_state.solicitar_gps and not st.session_state.municipio_guardado:
    loc = get_geolocation()
    if loc:
        lat_gps, lon_gps = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        st.info("Buscando señal GPS...")
        st.stop()

# --- PANTALLA 2: SELECCIÓN MANUAL SI NO HAY GPS ---
if not lat_gps and not st.session_state.municipio_guardado:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    muni_sel = st.selectbox("Selecciona tu municipio:", options=municipios_unicos, index=None, placeholder="Escribe para buscar...")
    if st.button("✅ Confirmar", type="secondary", use_container_width=True):
        if muni_sel:
            st.session_state.municipio_guardado = muni_sel
            streamlit_js_eval(js_expressions=f"parent.window.localStorage.setItem('muni_gasolineras', '{muni_sel}')")
            st.rerun()
    st.stop()

# --- PANTALLA 3: RESULTADOS ---
st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)

# Definir punto de referencia
if lat_gps:
    lat_ref, lon_ref = lat_gps, lon_gps
    df["dist_temp"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
else:
    muni_ref = st.session_state.municipio_guardado
    fila = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila["lat_num"], fila["lon_num"]

# Ajustes
with st.expander("⚙️ Ajustar búsqueda"):
    n_muni = st.selectbox("Cambiar municipio:", options=municipios_unicos, index=municipios_unicos.index(muni_ref))
    n_radio = st.radio("Radio (km):", [5, 10, 20, 50], index=[5, 10, 20, 50].index(st.session_state.radio_km), horizontal=True)
    n_tipo = st.radio("Combustible:", ["Diésel", "G95"], index=0 if st.session_state.tipo_combustible == "Diésel" else 1, horizontal=True)
    
    if st.button("🔍 Aplicar cambios", use_container_width=True):
        st.session_state.municipio_guardado = n_muni
        st.session_state.radio_km = n_radio
        st.session_state.tipo_combustible = n_tipo
        st.rerun()

# Filtrado y Ordenación
col_orden = "Precio_Diesel" if st.session_state.tipo_combustible == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[(df["Distancia"] <= st.session_state.radio_km) & (df[col_orden].notna())].sort_values(col_orden)

st.markdown(f"<div class='resumen-filtros'>📍 {muni_ref} | 🚗 {st.session_state.radio_km}km | ⛽ {st.session_state.tipo_combustible}</div>", unsafe_allow_html=True)

if res.empty:
    st.warning("No hay gasolineras en este radio. Prueba a ampliarlo en Ajustes.")
else:
    for _, g in res.head(15).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([0.65, 0.35], vertical_alignment="center")
            with c1:
                st.markdown(f"**{g['Rótulo'][:25]}**")
                p_d = f"{g['Precio_Diesel']:.3f}€" if pd.notnull(g['Precio_Diesel']) else "--"
                p_g = f"{g['Precio_G95']:.3f}€" if pd.notnull(g['Precio_G95']) else "--"
                st.markdown(f"<span class='card-price'>{p_d if st.session_state.tipo_combustible == 'Diésel' else p_g}</span> <small>({g['Distancia']:.1f} km)</small>", unsafe_allow_html=True)
                st.caption(f"{g['Dirección'].title()}")
            with c2:
                # URL corregida para Google Maps
                maps_url = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                st.link_button("🗺️ Ir", maps_url, use_container_width=True)

