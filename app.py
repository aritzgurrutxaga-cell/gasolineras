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
        .block-container {
            padding-top: 1rem !important; 
            padding-bottom: 25vh !important; 
        }
        header {visibility: hidden !important;}
        
        /* Eliminar huecos de Javascript */
        iframe { display: none !important; height: 0px !important; }
        .element-container:has(iframe) { display: none !important; height: 0px !important; margin: 0 !important; }
        
        /* Título gasolina.eus */
        .titulo-app {
            text-align: center; 
            font-size: clamp(28px, 9vw, 42px); 
            white-space: nowrap; 
            font-weight: 800;
            margin-top: -1rem;
            margin-bottom: 1.5rem;
            color: #ff4b4b;
            letter-spacing: -1px;
        }
        
        /* DISEÑO DE LA CAJA DE TEXTO (Altura de 56px para que el texto respire) */
        div[data-baseweb="select"] > div {
            padding: 10px 12px !important; 
            min-height: 56px !important;   
            border-radius: 12px !important;
            font-size: 1.15rem !important;
            display: flex !important;
            align-items: center !important;
        }

        /* FUERZA RADIO KM EN UNA FILA */
        div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            justify-content: space-between !important;
            gap: 2px !important;
        }

        .resumen-filtros {
            text-align: center; 
            font-size: 0.95rem; 
            margin-bottom: 1.5rem; 
            padding: 10px; 
            border-radius: 8px;
            border: 1px solid #444;
            background-color: #f0f2f6;
            color: #111;
        }

        /* --- BOTÓN ROJO INICIAL GIGANTE (Con estilo de App Nativa 3D) --- */
        .btn-gigante-container div[data-testid="stButton"] button {
            min-height: 120px !important; 
            border-radius: 20px !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 20px !important;
            background: linear-gradient(135deg, #ff4b4b 0%, #e62e2e 100%) !important;
            color: white !important;
            border: 2px solid #ff7b7b !important;
            box-shadow: 0 6px 14px rgba(255, 75, 75, 0.3) !important;
            transition: all 0.1s ease-in-out !important;
        }
        
        /* Efecto al pulsar el botón gigante */
        .btn-gigante-container div[data-testid="stButton"] button:active {
            transform: scale(0.96) !important;
            box-shadow: 0 2px 6px rgba(255, 75, 75, 0.3) !important;
        }
        
        /* Textos del botón gigante */
        .btn-gigante-container div[data-testid="stButton"] button p {
            font-size: 1.5rem !important;
            margin: 0 !important;
            font-weight: 800 !important;
        }
        
        .btn-gigante-container div[data-testid="stButton"] button::after {
            content: "👆 Es recomendable la ubicación para buscar";
            font-size: 0.95rem !important;
            font-weight: normal !important;
            opacity: 0.95;
            margin-top: 10px;
            display: block;
        }

    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE MEMORIA ---
if 'solicitar_gps' not in st.session_state: st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state: st.session_state.municipio_guardado = None
if 'gps_fallido' not in st.session_state: st.session_state.gps_fallido = False
if 'override_manual' not in st.session_state: st.session_state.override_manual = False

# Variables de los ajustes guardadas en memoria para que no se reinicien solas
if 'radio_km' not in st.session_state: st.session_state.radio_km = 5
if 'tipo_combustible' not in st.session_state: st.session_state.tipo_combustible = "Diésel"

# LocalStorage
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

if 'guardar_js' in st.session_state and st.session_state.guardar_js:
    js_code = f"parent.window.localStorage.setItem('muni_gasolineras', '{st.session_state.guardar_js}')"
    streamlit_js_eval(js_expressions=js_code, key=f"set_{st.session_state.guardar_js}")
    st.session_state.guardar_js = None

js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")
gps_denegado = (estado_permiso == "denied") or st.session_state.gps_fallido

# CARGA DE DATOS
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
    st.error("Error de conexión con los datos oficiales.")
    st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# ==========================================
# PANTALLA 1: INICIO (Con el Botón Gigante Aislado)
# ==========================================
if not (estado_permiso == "granted" or st.session_state.municipio_guardado) and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    
    # Encapsulamos el botón en el contenedor CSS para que sea enorme y parezca un botón real
    st.markdown('<div class="btn-gigante-container">', unsafe_allow_html=True)
    if st.button("📍 Mostrar gasolineras", use_container_width=True, type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# PROCESO GPS
# ==========================================
loc = None
lat_gps, lon_gps = None, None
if (estado_permiso == "granted" or st.session_state.solicitar_gps) and not (gps_denegado or st.session_state.municipio_guardado or st.session_state.override_manual):
    loc = get_geolocation()
    if loc is None:
        st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
        st.info("⏳ Localizando tu posición...")
        st.stop()
    elif 'coords' not in loc:
        st.session_state.gps_fallido = True
        gps_denegado = True
        st.rerun()
    else:
        lat_gps, lon_gps = loc['coords']['latitude'], loc['coords']['longitude']

# ==========================================
# SELECCIÓN MANUAL (PRIMERA VEZ)
# ==========================================
if not lat_gps and not st.session_state.municipio_guardado:
    st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; opacity: 0.8;'>📍 Escribe tu municipio:</p>", unsafe_allow_html=True)
    
    municipio_sel = st.selectbox("Municipio:", options=municipios_unicos, index=None, placeholder="Buscar...", label_visibility="collapsed")
    
    if municipio_sel:
        st.markdown("<script>window.parent.document.activeElement.blur();</script>", unsafe_allow_html=True)

    if st.button("✅ Confirmar selección", type="primary", use_container_width=True):
        if municipio_sel:
            st.session_state.municipio_guardado = municipio_sel
            st.session_state.guardar_js = municipio_sel
            st.session_state.override_manual = True
            st.rerun()
    st.stop()

# ==========================================
# PANTALLA 3: RESULTADOS Y AJUSTES
# ==========================================
st.markdown("<div class='titulo-app'>gasolina.eus</div>", unsafe_allow_html=True)

lat_ref, lon_ref, muni_ref = None, None, None
if lat_gps and not st.session_state.override_manual:
    lat_ref, lon_ref = lat_gps, lon_gps
    df["dist_temp"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
else:
    muni_ref = st.session_state.municipio_guardado
    fila = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila["lat_num"], fila["lon_num"]

# --- EL EXPANDER CLÁSICO SIN FORZAR CIERRES ---
# Ya no le pasamos el parámetro 'expanded'. Así Streamlit lo gestiona de forma nativa 
# y no se cerrará al tocar las opciones de dentro.
with st.expander("⚙️ Ajustes de búsqueda"):
    idx_muni = municipios_unicos.index(muni_ref) if muni_ref in municipios_unicos else 0
    nuevo_muni = st.selectbox("Cambiar municipio:", options=municipios_unicos, index=idx_muni)
    
    if nuevo_muni != muni_ref:
        st.markdown("<script>window.parent.document.activeElement.blur();</script>", unsafe_allow_html=True)
        
    nuevo_radio = st.radio("Radio de búsqueda:", [5, 10, 20, 50], 
                           index=[5, 10, 20, 50].index(st.session_state.radio_km),
                           format_func=lambda x: f"{x} km", horizontal=True)
    
    nuevo_tipo = st.radio("Ordenar por precio de:", ["Diésel", "G95"], 
                          index=0 if st.session_state.tipo_combustible == "Diésel" else 1,
                          horizontal=True)
    
    st.write("")
    if st.button("🔍 Buscar", use_container_width=True, type="primary"):
        st.session_state.municipio_guardado = nuevo_muni
        st.session_state.guardar_js = nuevo_muni
        st.session_state.radio_km = nuevo_radio
        st.session_state.tipo_combustible = nuevo_tipo
        st.session_state.override_manual = True
        st.rerun()

# Lógica de filtrado (Muestra si tiene AL MENOS el precio del combustible elegido)
col_orden = "Precio_Diesel" if st.session_state.tipo_combustible == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[
    (df["Distancia"] <= st.session_state.radio_km) & 
    ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
].sort_values(col_orden, na_position='last')

st.markdown(f"<div class='resumen-filtros'>📍 <b>{muni_ref}</b> | 🚗 <b>{st.session_state.radio_km} km</b> | ⛽ <b>{st.session_state.tipo_combustible}</b></div>", unsafe_allow_html=True)

for _, g in res.head(20).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
        with c1:
            st.write(f"### {g['Rótulo']} - {g['Municipio']}")
            p_diesel = f"{g['Precio Gasoleo A']}€" if pd.notnull(g['Precio_Diesel']) else "N/A"
            p_g95 = f"{g['Precio Gasolina 95 E5']}€" if pd.notnull(g['Precio_G95']) else "N/A"
            st.write(f"⛽ **D:** {p_diesel} | **G95:** {p_g95}")
            st.caption(f"📍 A {g['Distancia']:.2f} km")
        with c2:
            st.link_button("🗺️ Ir allí", f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}", use_container_width=True)
