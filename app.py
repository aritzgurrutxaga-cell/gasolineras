import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
import pytz
from streamlit_js_eval import get_geolocation, streamlit_js_eval
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- FUNCIONES ---
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

# 1. Configuración
st.set_page_config(page_title="gasolina.eus", page_icon="⛽", layout="centered")

# 2. CSS REDISEÑO TOTAL
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; }
        header {visibility: hidden !important;}
        
        /* Título gasolina.eus */
        .titulo-app {
            text-align: center; 
            font-size: clamp(28px, 9vw, 42px); 
            font-weight: 800;
            color: #ff4b4b;
            margin-bottom: 1rem;
        }

        /* DISEÑO CAJA MUNICIPIO (60px alto) */
        div[data-baseweb="select"] > div {
            min-height: 60px !important;
            border-radius: 12px !important;
            font-size: 1.1rem !important;
            display: flex; align-items: center;
        }

        /* ESTILO PESTAÑAS (TABS) */
        button[data-baseweb="tab"] {
            font-size: 1.1rem !important;
            font-weight: bold !important;
            height: 50px !important;
        }

        /* --- EL BOTÓN GIGANTE INICIAL (INMUNE) --- */
        /* Buscamos el primer botón de la página cuando no hay nada más */
        .stButton > button {
            transition: all 0.2s;
        }
        
        /* Definimos un ID único por CSS para el primer botón que encuentre */
        section[data-testid="stSidebar"] + section .element-container:first-of-type button {
            min-height: 120px !important;
            background-color: #d32f2f !important;
            border-radius: 20px !important;
            border: none !important;
            box-shadow: 0 6px 15px rgba(0,0,0,0.2) !important;
        }
        
        /* Subtexto para el botón inicial */
        .inicio-msg {
            text-align: center;
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: -10px;
            margin-bottom: 20px;
        }

        .resumen-filtros {
            text-align: center; 
            font-size: 0.9rem; 
            padding: 8px;
            background-color: #f0f2f6;
            border-radius: 8px;
            margin-bottom: 1rem;
            color: #31333F;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Memoria
if 'solicitar_gps' not in st.session_state: st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state: st.session_state.municipio_guardado = None
if 'radio_km' not in st.session_state: st.session_state.radio_km = 5
if 'tipo_combustible' not in st.session_state: st.session_state.tipo_combustible = "Diésel"

# LocalStorage
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# 4. Datos
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
if not datos: st.error("Sin conexión."); st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# ==========================================
# FLUJO DE PANTALLAS
# ==========================================

# A. PANTALLA INICIAL (Botón Rojo Gigante)
if not st.session_state.municipio_guardado and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    if st.button("📍 MOSTRAR GASOLINERAS", use_container_width=True):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.markdown("<div class='inicio-msg'>Es necesaria la ubicación para buscar</div>", unsafe_allow_html=True)
    st.stop()

# B. GPS / SELECCIÓN MANUAL (Solo si no hay municipio)
if st.session_state.solicitar_gps and not st.session_state.municipio_guardado:
    loc = get_geolocation()
    if loc:
        lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
        df["dist_t"] = calcular_distancia(lat, lon, df["lat_num"], df["lon_num"])
        st.session_state.municipio_guardado = df.sort_values("dist_t").iloc[0]["Municipio"]
        st.rerun()
    else:
        st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>📍 Elige tu municipio:</p>", unsafe_allow_html=True)
        m_sel = st.selectbox("Municipio", options=municipios_unicos, index=None, placeholder="Escribe aquí...", label_visibility="collapsed")
        if st.button("Confirmar selección", use_container_width=True):
            if m_sel:
                st.session_state.municipio_guardado = m_sel
                st.rerun()
        st.stop()

# C. PANTALLA PRINCIPAL (REDISÉÑO CON TABS)
st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)

tab_lista, tab_ajustes = st.tabs(["📍 Gasolineras", "⚙️ Filtros"])

# --- TAB DE AJUSTES (FIJO, NO SE CIERRA) ---
with tab_ajustes:
    st.write("Configura tu búsqueda:")
    muni_ref = st.session_state.municipio_guardado
    idx_m = municipios_unicos.index(muni_ref) if muni_ref in municipios_unicos else 0
    
    nuevo_muni = st.selectbox("Cambiar municipio:", options=municipios_unicos, index=idx_m)
    nuevo_radio = st.select_slider("Radio de búsqueda:", options=[5, 10, 20, 50], value=st.session_state.radio_km, format_func=lambda x: f"{x} km")
    nuevo_tipo = st.radio("Ordenar por:", ["Diésel", "G95"], index=0 if st.session_state.tipo_combustible == "Diésel" else 1, horizontal=True)
    
    if st.button("🔍 Aplicar cambios", use_container_width=True):
        st.session_state.municipio_guardado = nuevo_muni
        st.session_state.radio_km = nuevo_radio
        st.session_state.tipo_combustible = nuevo_tipo
        st.rerun()

# --- TAB DE LISTA ---
with tab_lista:
    muni_ref = st.session_state.municipio_guardado
    fila_m = df[df["Municipio"] == muni_ref].iloc[0]
    lat_r, lon_r = fila_m["lat_num"], fila_m["lon_num"]
    
    col_o = "Precio_Diesel" if st.session_state.tipo_combustible == "Diésel" else "Precio_G95"
    df["Distancia"] = calcular_distancia(lat_r, lon_r, df["lat_num"], df["lon_num"])
    
    res = df[
        (df["Distancia"] <= st.session_state.radio_km) & 
        ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
    ].sort_values(col_o, na_position='last')

    st.markdown(f"<div class='resumen-filtros'>📍 {muni_ref} | 🚗 {st.session_state.radio_km} km | ⛽ {st.session_state.tipo_combustible}</div>", unsafe_allow_html=True)

    for _, g in res.head(15).iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
            with c1:
                st.write(f"### {g['Rótulo']}")
                st.write(f"⛽ **D:** {g['Precio Gasoleo A']}€ | **G95:** {g['Precio Gasolina 95 E5']}€")
                st.caption(f"📍 {g['Distancia']:.2f} km")
            with c2:
                st.link_button("🗺️ Ir allí", f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}", use_container_width=True)