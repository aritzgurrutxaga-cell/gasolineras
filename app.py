import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
from streamlit_js_eval import get_geolocation, streamlit_js_eval
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import streamlit.components.v1 as components

# --- FUNCIONES DE APOYO ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def cerrar_teclado_movil():
    components.html(
        """
        <script>
        const inputs = window.parent.document.querySelectorAll('input');
        inputs.forEach(input => input.blur());
        window.parent.document.body.focus();
        </script>
        """,
        height=0,
    )

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

# --- AJUSTES DE DISEÑO CSS (INTACTOS) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;800&display=swap');
        .block-container { padding-top: 1rem !important; padding-bottom: 25vh !important; }
        header {visibility: hidden !important;}
        iframe { display: none !important; height: 0px !important; }
        .element-container:has(iframe) { display: none !important; }
        
        div[data-baseweb="select"] > div {
            padding: 4px 12px !important; min-height: 54px !important;
            border-radius: 12px !important; font-size: 1.15rem !important; 
            border: 1px solid #e2e8f0 !important; background-color: white !important;
            display: flex !important; align-items: center !important;
        }
        
        .titulo-app {
            text-align: center; font-family: 'Poppins', sans-serif;
            font-size: clamp(32px, 9vw, 46px); font-weight: 800;
            color: #1e293b; letter-spacing: -1.5px; margin-bottom: 0.5rem;
        }
        .titulo-app span { color: #ef4444; }
        
        .subtitulo-app {
            text-align: center; color: #64748b; font-size: 1.05rem; 
            margin-bottom: 2rem; margin-top: -0.5rem;
            font-family: 'Poppins', sans-serif; font-weight: 500;
        }
        
        div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div {
            flex-direction: row !important; justify-content: space-between !important; gap: 2px !important;
        }

        .resumen-filtros {
            text-align: center; font-size: 0.95rem; margin-bottom: 1.5rem; 
            padding: 12px 20px; border-radius: 40px; border: 1px solid #e2e8f0;
            background-color: #ffffff; color: #334155;
            box-shadow: 0 2px 10px rgba(0,0,0,0.02);
            font-family: 'Poppins', sans-serif; font-weight: 500;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: #ffffff !important; border: 1px solid #f1f5f9 !important;
            border-radius: 16px !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04) !important;
            padding: 0.8rem !important; margin-bottom: 0.5rem !important;
        }

        div[data-testid="stButton"] button[kind="primary"] {
            min-height: 100px !important; border-radius: 15px !important;
            font-weight: bold !important; width: 100% !important;
            display: flex !important; flex-direction: column !important;
            align-items: center !important; justify-content: center !important;
            box-shadow: 0 4px 14px rgba(239, 68, 68, 0.25) !important;
        }
        div[data-testid="stButton"] button[kind="primary"] p { font-size: 1.4rem !important; margin: 0 !important; }
        div[data-testid="stButton"] button[kind="primary"]::after {
            content: "Es recomendable la ubicación para buscar";
            font-size: 0.85rem !important; font-weight: normal !important;
            opacity: 0.9; display: block; margin-top: 8px;
        }
        details div[data-testid="stButton"] button[kind="primary"] {
            min-height: 48px !important; padding: 0.5rem 1rem !important; box-shadow: none !important;
        }
        details div[data-testid="stButton"] button[kind="primary"]::after { content: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN ---
if 'solicitar_gps' not in st.session_state: st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state: st.session_state.municipio_guardado = None
if 'gps_fallido' not in st.session_state: st.session_state.gps_fallido = False
if 'override_manual' not in st.session_state: st.session_state.override_manual = False
if 'radio_km' not in st.session_state: st.session_state.radio_km = 5
if 'tipo_combustible' not in st.session_state: st.session_state.tipo_combustible = "Diésel"

# Recuperar caché persistente
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

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
if not datos: st.error("Error de conexión."); st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# Permisos GPS
js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")

# --- LÓGICA DE NAVEGACIÓN ---
if not st.session_state.municipio_guardado and not st.session_state.solicitar_gps:
    st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo-app'>Compara precios en tiempo real y ahorra en cada repostaje.</p>", unsafe_allow_html=True)
    if st.button("📍 Mostrar gasolineras", use_container_width=True, type="primary"):
        st.session_state.solicitar_gps = True; st.rerun()
    st.stop()

loc = None; lat_gps, lon_gps = None, None
if (estado_permiso == "granted" or st.session_state.solicitar_gps) and not (st.session_state.gps_fallido or st.session_state.municipio_guardado or st.session_state.override_manual):
    loc = get_geolocation()
    if loc is None:
        st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)
        st.info("⏳ Localizando..."); st.stop()
    elif 'coords' in loc:
        lat_gps, lon_gps = loc['coords']['latitude'], loc['coords']['longitude']
    else:
        st.session_state.gps_fallido = True; st.rerun()

if not lat_gps and not st.session_state.municipio_guardado:
    st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>📍 Escribe tu municipio:</p>", unsafe_allow_html=True)
    muni_sel = st.selectbox("Municipio:", options=municipios_unicos, index=None, placeholder="Buscar...", label_visibility="collapsed")
    if muni_sel: cerrar_teclado_movil()
    if st.button("✅ Confirmar selección", type="primary", use_container_width=True):
        if muni_sel:
            st.session_state.municipio_guardado = muni_sel
            streamlit_js_eval(js_expressions=f"parent.window.localStorage.setItem('muni_gasolineras', '{muni_sel}')")
            st.session_state.override_manual = True; st.rerun()
    st.stop()

# --- PANTALLA 3: RESULTADOS ---
st.markdown("<div class='titulo-app'>gasolina<span>.eus</span></div>", unsafe_allow_html=True)

if lat_gps and not st.session_state.override_manual:
    lat_ref, lon_ref = lat_gps, lon_gps
    df["dist_temp"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
else:
    muni_ref = st.session_state.municipio_guardado
    fila = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila["lat_num"], fila["lon_num"]

# AJUSTES PLEGADOS POR DEFECTO
with st.expander("⚙️ Ajustes de búsqueda", expanded=False):
    nuevo_muni = st.selectbox("Cambiar municipio:", options=municipios_unicos, index=municipios_unicos.index(muni_ref) if muni_ref in municipios_unicos else None)
    if nuevo_muni != muni_ref: cerrar_teclado_movil()
    nuevo_radio = st.radio("Radio de búsqueda:", [5, 10, 20], index=[5, 10, 20].index(st.session_state.radio_km), format_func=lambda x: f"{x} km", horizontal=True)
    nuevo_tipo = st.radio("Ordenar por precio de:", ["Diésel", "G95"], index=0 if st.session_state.tipo_combustible == "Diésel" else 1, horizontal=True)
    if st.button("🔍 Buscar", use_container_width=True, type="primary"):
        st.session_state.municipio_guardado = nuevo_muni
        streamlit_js_eval(js_expressions=f"parent.window.localStorage.setItem('muni_gasolineras', '{nuevo_muni}')")
        st.session_state.radio_km = nuevo_radio
        st.session_state.tipo_combustible = nuevo_tipo
        st.session_state.override_manual = True; st.rerun()

col_orden = "Precio_Diesel" if st.session_state.tipo_combustible == "Diésel" else "Precio_G95"
df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[df["Distancia"] <= st.session_state.radio_km].sort_values(col_orden, na_position='last')

st.markdown(f"<div class='resumen-filtros'>📍 <b>{muni_ref}</b> | 🚗 <b>{st.session_state.radio_km} km</b> | ⛽ <b>{st.session_state.tipo_combustible}</b></div>", unsafe_allow_html=True)

for _, g in res.head(20).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([2.5, 1.5], vertical_alignment="center")
        with c1:
            st.write(f"#### {g['Rótulo']} - {g['Municipio']}")
            p_diesel = f"{g['Precio Gasoleo A']}€" if pd.notnull(g['Precio_Diesel']) else "N/A"
            p_g95 = f"{g['Precio Gasolina 95 E5']}€" if pd.notnull(g['Precio_G95']) else "N/A"
            st.write(f"⛽ **Diesel:** {p_diesel} | **G95:** {p_g95}")
            st.caption(f"📍 A {g['Distancia']:.2f} km")
        with c2:
            st.link_button("Navegar", f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}", use_container_width=True)
