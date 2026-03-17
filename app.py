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

# AJUSTES DE ESPACIADO PRECISOS Y DISEÑO CSS
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 25vh !important; 
            margin-top: 0rem !important;
        }
        header {visibility: hidden !important;}
        #MainMenu {visibility: hidden !important;}
        
        /* Eliminar huecos fantasmas de Javascript */
        iframe {
            display: none !important;
            height: 0px !important;
        }
        .element-container:has(iframe) {
            display: none !important;
            height: 0px !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* ========================================================= */
        /* --- DISEÑO PREMIUM DEL DESPLEGABLE (SELECTBOX) --- */
        /* ========================================================= */
        
        /* 1. Caja de texto con ALTURA Y AIRE correctos */
        div[data-baseweb="select"] > div {
            padding: 10px 15px !important; /* Más espacio vertical para que no sea estrecho */
            min-height: 50px !important;   /* Altura mínima para que sea cómodo al dedo */
            border-radius: 12px !important;
            font-size: 1.1rem !important;
            display: flex !important;
            align-items: center !important;
        }
        
        /* 2. Lista flotante optimizada */
        ul[role="listbox"] {
            max-height: 40vh !important; 
            border-radius: 12px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        }
        
        /* 3. Opciones de la lista */
        li[role="option"] {
            padding: 15px !important;
            font-size: 1.1rem !important;
            border-bottom: 1px solid rgba(150, 150, 150, 0.1) !important;
        }
        
        /* ========================================================= */

        div[data-testid="stRadio"] > label {font-weight: bold; margin-bottom: -0.5rem;}
        div[data-testid="stRadio"] {margin-bottom: 0.5rem;}
        
        hr {margin-top: 0.5rem; margin-bottom: 1rem;}
        
        /* Título en una sola línea sin romperse */
        .titulo-app {
            text-align: center; 
            font-size: clamp(20px, 6.5vw, 32px); 
            white-space: nowrap; 
            font-weight: bold;
            margin-top: -1rem;
            margin-bottom: 1rem;
        }
        
        .resumen-filtros {
            text-align: center; 
            color: inherit; 
            font-size: 0.95rem; 
            margin-bottom: 1.5rem; 
            background-color: transparent; 
            padding: 10px; 
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        /* --- BOTÓN GIGANTE --- */
        div[data-testid="stButton"] button[kind="primary"] {
            font-size: 1.2rem !important;
            font-weight: bold !important;
            padding: 1rem !important;
            border-radius: 12px !important;
            margin-top: 1rem !important; /* Espacio extra respecto a la caja */
        }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA ---
if 'solicitar_gps' not in st.session_state:
    st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state:
    st.session_state.municipio_guardado = None
if 'gps_fallido' not in st.session_state:
    st.session_state.gps_fallido = False
if 'override_manual' not in st.session_state:
    st.session_state.override_manual = False

# Recuperamos la caché persistente
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# Guardar en caché permanente
if 'guardar_js' in st.session_state and st.session_state.guardar_js:
    js_code = f"parent.window.localStorage.setItem('muni_gasolineras', '{st.session_state.guardar_js}')"
    streamlit_js_eval(js_expressions=js_code, key=f"set_{st.session_state.guardar_js}")
    st.session_state.guardar_js = None

# Consultar permisos GPS
js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")
gps_denegado = (estado_permiso == "denied") or st.session_state.gps_fallido

# ==========================================
# ESTADO 1: PANTALLA INICIAL
# ==========================================
if not (estado_permiso == "granted" or st.session_state.municipio_guardado) and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>⛽ Buscador Gasolineras</div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; font-size: 1.1rem;'>Encuentra el mejor precio al instante</h3>", unsafe_allow_html=True)
    
    if st.button("📍 Mostrar gasolineras", use_container_width=True, type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.stop() 

# ==========================================
# PROCESAMIENTO GPS
# ==========================================
loc = None
lat_gps, lon_gps = None, None
if (estado_permiso == "granted" or st.session_state.solicitar_gps) and not (gps_denegado or st.session_state.municipio_guardado or st.session_state.override_manual):
    loc = get_geolocation()
    if loc is None:
        st.markdown("<div class='titulo-app'>⛽ Buscador Gasolineras</div>", unsafe_allow_html=True)
        st.info("⏳ Localizando...")
        st.stop() 
    elif 'coords' not in loc:
        st.session_state.gps_fallido = True
        gps_denegado = True
        st.rerun() 
    else:
        lat_gps = loc['coords']['latitude']
        lon_gps = loc['coords']['longitude']

# ==========================================
# CARGA DE DATOS
# ==========================================
@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    try:
        r = session.get(url, headers=headers, timeout=25)
        return r.json()["ListaEESSPrecio"], datetime.datetime.now()
    except:
        return None, None

datos, fecha_act = cargar_datos()

if not datos:
    st.error("Error al cargar datos oficiales.")
    st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# ==========================================
# ESTADO 2: SELECCIÓN MANUAL (DISEÑO AMPLIADO)
# ==========================================
if not lat_gps and not st.session_state.municipio_guardado:
    st.markdown("<div class='titulo-app'>⛽ Buscador Gasolineras</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; opacity: 0.8;'>📍 Escribe tu municipio:</p>", unsafe_allow_html=True)
    
    municipio_sel = st.selectbox(
        "Municipio:", 
        options=municipios_unicos,
        index=None,
        placeholder="Toca aquí para buscar...",
        label_visibility="collapsed"
    )

    if st.button("✅ Confirmar selección", type="primary", use_container_width=True):
        if municipio_sel:
            st.session_state.municipio_guardado = municipio_sel
            st.session_state.guardar_js = municipio_sel
            st.session_state.override_manual = True
            st.rerun() 
    st.stop() 

# ==========================================
# ESTADO 3: RESULTADOS
# ==========================================
st.markdown("<div class='titulo-app'>⛽ Buscador Gasolineras</div>", unsafe_allow_html=True)

lat_ref, lon_ref, muni_ref = None, None, None
if lat_gps and not st.session_state.override_manual:
    lat_ref, lon_ref = lat_gps, lon_gps
    df["dist_temp"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
else:
    muni_ref = st.session_state.municipio_guardado
    fila = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila["lat_num"], fila["lon_num"]

with st.expander("⚙️ Ajustes de búsqueda"):
    muni_cambio = st.selectbox("Cambiar municipio:", options=municipios_unicos, index=municipios_unicos.index(muni_ref) if muni_ref in municipios_unicos else None)
    if st.button("Actualizar"):
        st.session_state.municipio_guardado = muni_cambio
        st.session_state.guardar_js = muni_cambio
        st.session_state.override_manual = True
        st.rerun()
    radio_km = st.radio("Radio:", [5, 10, 20, 50], format_func=lambda x: f"{x} km", horizontal=True)
    tipo = st.radio("Ordenar por:", ["Diésel", "G95"], horizontal=True)

col_orden = "Precio_Diesel" if tipo == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[(df["Distancia"] <= radio_km) & (df[col_orden].notna())].sort_values(col_orden)

st.markdown(f"<div class='resumen-filtros'>📍 <b>{muni_ref}</b> | 🚗 <b>{radio_km} km</b> | ⛽ <b>{tipo}</b></div>", unsafe_allow_html=True)

for _, g in res.head(20).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
        with c1:
            st.write(f"### {g['Rótulo']} - {g['Municipio']}")
            st.write(f"⛽ **D:** {g['Precio Gasoleo A']}€ | **G95:** {g['Precio Gasolina 95 E5']}€")
            st.caption(f"📍 A {g['Distancia']:.2f} km")
        with c2:
            st.link_button("🗺️ Ir allí", f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}", use_container_width=True)

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
