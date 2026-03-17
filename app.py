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
            padding-bottom: 2rem !important;
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
        
        div[data-testid="stRadio"] > label {font-weight: bold; margin-bottom: -0.5rem;}
        div[data-testid="stRadio"] {margin-bottom: 0.5rem;}
        hr {margin-top: 0.5rem; margin-bottom: 1rem;}
        h1 {margin-top: -1rem; margin-bottom: 0.5rem;}
        
        .resumen-filtros {
            text-align: center; 
            color: #444; 
            font-size: 0.95rem; 
            margin-bottom: 1.5rem; 
            background-color: #f0f2f6; 
            padding: 10px; 
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }

        /* --- CSS PARA EL BOTÓN GIGANTE --- */
        div[data-testid="stButton"] button[kind="primary"] {
            font-size: 1.4rem !important;
            font-weight: bold !important;
            padding: 1.5rem !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
            transition: all 0.2s ease-in-out !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 14px rgba(0,0,0,0.2) !important;
        }
    </style>
""", unsafe_allow_html=True)

# Título SIEMPRE VISIBLE
st.markdown(
    """
    <h1 style='text-align: center; font-size: clamp(22px, 7vw, 38px);'>
        ⛽ Buscador Gasolineras
    </h1>
    """, 
    unsafe_allow_html=True
)

# --- INICIALIZACIÓN DE MEMORIA Y LOCAL STORAGE ---
if 'solicitar_gps' not in st.session_state:
    st.session_state.solicitar_gps = False
if 'municipio_guardado' not in st.session_state:
    st.session_state.municipio_guardado = None
if 'gps_fallido' not in st.session_state:
    st.session_state.gps_fallido = False
if 'override_manual' not in st.session_state:
    st.session_state.override_manual = False

# Recuperamos la caché persistente del navegador
muni_cache = streamlit_js_eval(js_expressions="parent.window.localStorage.getItem('muni_gasolineras')", key="get_muni_cache")
if muni_cache and muni_cache != "null" and not st.session_state.municipio_guardado:
    st.session_state.municipio_guardado = muni_cache

# Guardar en caché permanente en segundo plano
if 'guardar_js' in st.session_state and st.session_state.guardar_js:
    js_code = f"parent.window.localStorage.setItem('muni_gasolineras', '{st.session_state.guardar_js}')"
    streamlit_js_eval(js_expressions=js_code, key=f"set_{st.session_state.guardar_js}")
    st.session_state.guardar_js = None

# Consultar permisos de ubicación
js_permiso = "navigator.permissions ? navigator.permissions.query({name: 'geolocation'}).then(res => res.state) : 'prompt'"
estado_permiso = streamlit_js_eval(js_expressions=js_permiso, key="permiso_gps")
gps_denegado = (estado_permiso == "denied") or st.session_state.gps_fallido

# ==========================================
# ESTADO 1: PANTALLA INICIAL PURA (Botón rojo)
# ==========================================
# Solo la mostramos si no hay GPS concedido, no hay caché, y no ha pulsado el botón aún.
mostrar_pantalla_inicial = True
if estado_permiso == "granted" or st.session_state.municipio_guardado:
    mostrar_pantalla_inicial = False

if mostrar_pantalla_inicial and not st.session_state.solicitar_gps:
    st.markdown("<h3 style='text-align: center; color: #555; font-size: 1.1rem; margin-top: 1.5rem; margin-bottom: 1rem;'>Descubre al instante dónde repostar más barato</h3>", unsafe_allow_html=True)
    if st.button("📍 Mostrar gasolineras", use_container_width=True, type="primary"):
        st.session_state.solicitar_gps = True
        st.rerun()
    st.stop() 

# ==========================================
# PROCESAMIENTO DE UBICACIÓN
# ==========================================
loc = None
lat_gps, lon_gps = None, None

# Intentamos GPS si ya está concedido, o si pulsaron el botón (y no está denegado)
intentar_gps = (estado_permiso == "granted") or (st.session_state.solicitar_gps and not gps_denegado)

# Si el usuario cambió de pueblo a mano EN ESTA SESIÓN, no le forzamos el GPS de nuevo hasta que reinicie
if intentar_gps and not st.session_state.override_manual:
    loc = get_geolocation()
    if loc is None:
        st.info("⏳ Localizando tu posición...")
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
@st.cache_data(ttl=3600, show_spinner="Descargando precios oficiales...")
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

if not datos:
    st.error("Sin conexión a los datos oficiales.")
    st.stop()

df = pd.DataFrame(datos)
df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
df["Precio_Diesel"] = pd.to_numeric(df["Precio Gasoleo A"].str.replace(",", "."), errors='coerce')
df["Precio_G95"] = pd.to_numeric(df["Precio Gasolina 95 E5"].str.replace(",", "."), errors='coerce')
municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

# ==========================================
# ESTADO 2: PANTALLA DE SELECCIÓN MANUAL ÚNICA
# Solo salta si no hay GPS, no hay caché y no se ha activado el override
# ==========================================
if not lat_gps and not lon_gps and not st.session_state.municipio_guardado:
    st.markdown("""
        <div style='text-align: center; margin-top: 1rem; margin-bottom: 2rem;'>
            <h3 style='color: #333;'>📍 Elige tu ubicación</h3>
            <p style='color: #666; font-size: 0.95rem;'>Busca y selecciona tu municipio para empezar:</p>
        </div>
    """, unsafe_allow_html=True)
    
    municipio_seleccionado_inicio = st.selectbox(
        "Municipio:", 
        options=municipios_unicos,
        index=None,
        placeholder="Escribe o selecciona tu municipio...",
        label_visibility="collapsed"
    )

    if st.button("✅ Confirmar y buscar", type="primary", use_container_width=True):
        if municipio_seleccionado_inicio:
            st.session_state.municipio_guardado = municipio_seleccionado_inicio
            st.session_state.guardar_js = municipio_seleccionado_inicio
            st.session_state.override_manual = True
            st.rerun() 
        else:
            st.error("Por favor, selecciona un municipio válido de la lista antes de continuar.")
    
    st.stop() 

# ==========================================
# ESTADO 3: PANTALLA DE RESULTADOS Y AJUSTES
# ==========================================
lat_ref, lon_ref, muni_ref = None, None, None

# LA REGLA DE ORO: Si hay GPS (y no lo acaban de cambiar a mano en los ajustes), PREVALECE SIEMPRE
if lat_gps and lon_gps and not st.session_state.override_manual:
    df["dist_temp"] = calcular_distancia(lat_gps, lon_gps, df["lat_num"], df["lon_num"])
    muni_ref = df.sort_values("dist_temp").iloc[0]["Municipio"]
    lat_ref, lon_ref = lat_gps, lon_gps
elif st.session_state.municipio_guardado:
    # Si no hay GPS (o si acaban de forzar el manual temporalmente), tira de caché
    muni_ref = st.session_state.municipio_guardado
    fila_muni = df[df["Municipio"] == muni_ref].iloc[0]
    lat_ref, lon_ref = fila_muni["lat_num"], fila_muni["lon_num"]

# Panel de ajustes
with st.expander("⚙️ Ajustes de búsqueda", expanded=False):
    st.write("Cambia tu ubicación manual o ajusta los filtros:")
    
    idx_actual = municipios_unicos.index(muni_ref) if muni_ref in municipios_unicos else None
    
    municipio_cambio = st.selectbox(
        "Cambiar municipio:", 
        options=municipios_unicos,
        index=idx_actual,
        placeholder="Busca un nuevo municipio..."
    )
            
    if st.button("Actualizar municipio"):
        if municipio_cambio and municipio_cambio != muni_ref:
            st.session_state.municipio_guardado = municipio_cambio
            st.session_state.guardar_js = municipio_cambio
            st.session_state.override_manual = True # Forzamos que se salte el GPS temporalmente
            st.rerun()

    st.write("") 
    
    if st.button("🗑️ Borrar ubicación y reiniciar", type="secondary", use_container_width=True):
        st.session_state.municipio_guardado = None
        st.session_state.solicitar_gps = False
        st.session_state.gps_fallido = False
        st.session_state.override_manual = False
        streamlit_js_eval(js_expressions="parent.window.localStorage.removeItem('muni_gasolineras')", key="borrar_cache")
        st.rerun()

    st.divider()

    col_km, col_gas = st.columns(2)
    with col_km:
        radio_km = st.radio(
            "Radio de búsqueda:",
            options=[5, 10, 20, 50],
            format_func=lambda x: f"{x} km",
            index=0, 
            horizontal=True
        )
    with col_gas:
        tipo_combustible = st.radio(
            "Ordenar por precio de:", 
            ["Diésel", "G95"], 
            horizontal=True
        )

col_orden = "Precio_Diesel" if tipo_combustible == "Diésel" else "Precio_G95"

df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
res = df[
    (df["Distancia"] <= radio_km) & 
    ((df["Precio_Diesel"].notna()) | (df["Precio_G95"].notna()))
].sort_values(col_orden, na_position='last')

if muni_ref:
    st.markdown(f"<div class='resumen-filtros'>📍 <b>{muni_ref}</b>  |  🚗 <b>{radio_km} km</b>  |  ⛽ <b>{tipo_combustible}</b></div>", unsafe_allow_html=True)

if not res.empty:
    for _, g in res.head(20).iterrows():
        with st.container(border=True):
            col_info, col_btn = st.columns([2.4, 1.6], vertical_alignment="center")
            with col_info:
                # AQUÍ ESTÁ EL CAMBIO: Rótulo + Municipio
                st.write(f"### {g['Rótulo']} - {g['Municipio']}")
                p_diesel = f"{g['Precio Gasoleo A']} €" if pd.notnull(g['Precio_Diesel']) else "N/A"
                p_g95 = f"{g['Precio Gasolina 95 E5']} €" if pd.notnull(g['Precio_G95']) else "N/A"
                st.write(f"⛽ **D:** {p_diesel} | **G95:** {p_g95}")
                st.caption(f"📍 A {g['Distancia']:.2f} km | {g['Dirección']}")
            with col_btn:
                url_map = f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}"
                st.link_button("🗺️ Ir allí", url_map, use_container_width=True)
else:
    st.warning(f"No hay resultados a {radio_km} km. Puedes cambiar el radio o el municipio en los Ajustes.")

if fecha_act:
    st.markdown(f"<div style='text-align: center; color: #a3a8b8; font-size: 0.75rem; margin-top: 25px;'>Última actualización MINETUR: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</div>", unsafe_allow_html=True)
