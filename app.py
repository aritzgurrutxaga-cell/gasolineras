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

# --- FUNCIONES DE APOYO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- ADAPTADOR SSL ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="gasolina.eus", page_icon="⛽", layout="centered")

# AJUSTES DE DISEÑO CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;800&display=swap');
        .block-container { padding-top: 1rem !important; padding-bottom: 25vh !important; }
        header {visibility: hidden !important;}
        iframe { display: none !important; height: 0px !important; }
        .element-container:has(iframe) { display: none !important; }
        
        div[data-baseweb="select"] > div {
            padding: 8px 12px !important; border-radius: 12px !important;
            font-size: 1.1rem !important; border: 1px solid #e2e8f0 !important;
        }
        
        .titulo-app {
            text-align: center; font-family: 'Poppins', sans-serif;
            font-size: clamp(32px, 9vw, 46px); font-weight: 800;
            color: #1e293b; letter-spacing: -1.5px; margin-bottom: 0.5rem;
        }
        .titulo-app span { color: #ef4444; }
        
        .subtitulo-app {
            text-align: center; color: #64748b; font-size: 1.05rem; 
            margin-bottom: 2rem; font-family: 'Poppins', sans-serif;
        }
        
        div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div {
            flex-direction: row !important; justify-content: space-between !important;
        }

        .resumen-filtros {
            text-align: center; font-size: 0.95rem; margin-bottom: 1.5rem; 
            padding: 12px 20px; border-radius: 40px; border: 1px solid #e2e8f0;
            background-color: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,0.02);
            font-family: 'Poppins', sans-serif;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: #ffffff !important; border: 1px solid #f1f5f9 !important;
            border-radius: 16px !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04) !important;
            padding: 0.8rem !important; margin-bottom: 0.5rem !important;
        }

        /* BOTÓN BUSCAR */
        div[data-testid="stButton"] button[kind="primary"] {
            min-height: 100px !important; border-radius: 15px !important;
            font-weight: bold !important; width: 100% !important;
            box-shadow: 0 4px 14px rgba(239, 68, 68, 0.25) !important;
        }
        
        div[data-testid="stButton"] button[kind="primary"]::after {
            content: "Es recomendable la ubicación para buscar";
            font-size: 0.85rem !important; font-weight: normal !important;
            display: block; margin-top: 8px;
        }
        
        /* BOTÓN DENTRO DE AJUSTES */
        details div[data-testid="stButton"] button[kind="primary"] {
            min-height: 50px !important;
        }
        details div[data-testid="stButton"] button[kind="primary"]::after {
            content: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'solicitar_gps' not in st.session_state: st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state: st.session_state.municipio_guardado = None
if 'gps_fallido' not in st.session_state: st.session_state.gps_fallido = False
if 'override_manual' not in st.session_state: st.session_state.override_manual = False
if 'radio_km' not in st.session_state: st.session_state.radio_km = 5
if 'tipo_combustible' not in st.session_state: st.session_state.tipo_combustible = "Diésel"

muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# Carga de datos
@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    try:
        r = session.get(url, timeout=25)
        return r.json()["ListaEESSPrecio"], datetime.datetime.now()
    except: return None, None

datos, fecha_act = cargar_datos()
if not datos:
    st.error("Error de conexión.")
    st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# Lógica GPS
js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")

# PANTALLA INICIO
if not (estado_permiso == "granted" or st.session_state.municipio_guardado) and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo-app'>Compara precios en tiempo real y ahorra en cada repostaje.</p>", unsafe_allow_html=True)
    if st.button("📍 Mostrar gasolineras", use_container_width=True, type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.stop()

# Localización GPS
loc = None
lat_gps, lon_gps = None, None
if (estado_permiso == "granted" or st.session_state.solicitar_gps) and not (st.session_state.gps_fallido or st.session_state.municipio_guardado or st.session_state.override_manual):
    loc = get_geolocation()
    if loc is None:
        st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)
        st.info("⏳ Localizando...")
        st.stop()
    elif 'coords' in loc:
        lat_gps, lon_gps = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        st.session_state.gps_fallido = True
        st.rerun()

# SELECCIÓN MANUAL (SI NO HAY GPS NI CACHÉ)
if not lat_gps and not st.session_state.municipio_guardado:
    st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>📍 Escribe tu municipio:</p>", unsafe_allow_html=True)
    municipio_sel = st.selectbox("Municipio:", options=municipios_unicos, index=None, placeholder="Buscar...", label_visibility="collapsed")
    if st.button("✅ Confirmar selección", type="primary", use_container_width=True):
        if municipio_sel:
            st.session_state.municipio_guardado = municipio_sel
            streamlit_js_eval(js_expressions=f"parent.window.localStorage.setItem('muni_gasolineras', '{municipio_sel}')")
            st.session_state.override_manual = True
            st.rerun()
    st.stop()

# RESULTADOS
st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)

# Lógica de Referencia
if lat_gps and not st.session_state.override_manual:
    lat_ref, lon_ref = lat_gps, lon_gps
    df["dist_temp"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
else:
    muni_ref = st.session_state.municipio_guardado
    fila = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila["lat_num"], fila["lon_num"]

# AJUSTES DE BÚSQUEDA (CORREGIDO)
with st.expander("⚙️ Ajustes de búsqueda"):
    # Vinculamos directamente a session_state usando 'key'
    st.selectbox("Cambiar municipio:", options=municipios_unicos, 
                 index=municipios_unicos.index(muni_ref) if muni_ref in municipios_unicos else None,
                 key="municipio_guardado")
    
    st.radio("Radio de búsqueda:", [5, 10, 20, 50], 
             format_func=lambda x: f"{x} km", horizontal=True,
             key="radio_km")
    
    st.radio("Ordenar por precio de:", ["Diésel", "G95"], 
             horizontal=True, key="tipo_combustible")
    
    if st.button("🔍 Cerrar ajustes", use_container_width=True, type="primary"):
        st.session_state.override_manual = True
        st.rerun()

# Filtrado dinámico
col_orden = "Precio_Diesel" if st.session_state.tipo_combustible == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[
    (df["Distancia"] <= st.session_state.radio_km) & 
    ((df[col_orden].notna()))
].sort_values(col_orden)

# Resumen y Lista
st.markdown(f"<div class='resumen-filtros'>📍 <b>{st.session_state.municipio_guardado}</b> | 🚗 <b>{st.session_state.radio_km} km</b> | ⛽ <b>{st.session_state.tipo_combustible}</b></div>", unsafe_allow_html=True)

for _, g in res.head(20).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
        with c1:
            st.write(f"#### {g['Rótulo']}")
            st.write(f"<span style='color: #64748b; font-size: 0.9rem;'>{g['Municipio']}</span>", unsafe_allow_html=True)
            p_diesel = f"{g['Precio Gasoleo A']}€" if pd.notnull(g['Precio_Diesel']) else "N/A"
            p_g95 = f"{g['Precio Gasolina 95 E5']}€" if pd.notnull(g['Precio_G95']) else "N/A"
            st.write(f"⛽ **D:** {p_diesel} | **G95:** {p_g95}")
            st.caption(f"📍 A {g['Distancia']:.2f} km")
        with c2:
            st.link_button("🗺️ Ir allí", f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}", use_container_width=True)
