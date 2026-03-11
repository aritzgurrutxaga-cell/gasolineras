import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- PARCHE PARA EL ERROR SSL UNEXPECTED_EOF ---
# Esto obliga a requests a usar configuraciones de cifrado más compatibles
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers('DEFAULT@SECLEVEL=1') # Baja el nivel de seguridad para evitar el rechazo del servidor
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container { padding: 1rem !important; }
        .titulo-una-linea {
            text-align: center;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Función JS para ocultar teclado
def ocultar_teclado():
    components.html("<script>window.parent.document.activeElement.blur();</script>", height=0, width=0)

# 3. Carga de Datos con Adaptador SSL
@st.cache_data(ttl=3600, show_spinner="Actualizando precios...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    session = requests.Session()
    # Montamos el adaptador especial para la URL del ministerio
    session.mount("https://", SSLAdapter())
    
    try:
        r = session.get(url, headers=headers, timeout=30, verify=True)
        r.raise_for_status()
        return r.json()["ListaEESSPrecio"]
    except Exception as e:
        # Si sigue fallando, mostramos el error para debug
        st.error(f"Error técnico: {e}")
        return None

# 4. Cálculo de distancia
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    with st.container(border=True):
        municipio_sel = st.selectbox("🔍 Tu ubicación:", options=municipios_unicos, index=None, placeholder="Elige municipio...")
        col_radio, col_tipo = st.columns(2)
        with col_radio:
            radio_km = st.slider("Radio (Km):", 1, 50, 10)
        with col_tipo:
            combustible = st.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if combustible == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        ocultar_teclado()
        
        # Procesar datos
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        ref = df[df["Municipio"] == municipio_sel].iloc[0]
        df["Distancia"] = calcular_distancia(ref["lat_num"], ref["lon_num"], df["lat_num"], df["lon_num"])
        
        resultados = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values(by="precio_num")

        st.divider()
        if not resultados.empty:
            for _, g in resultados.head(15).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{g['Rótulo']}**")
                        st.write(f"💰 **{g[col_precio]} €/L** | 📍 {g['Distancia']:.1f} km")
                    with col_btn:
                        map_url = f"https://www.google.com/maps?q={g['lat_num']},{g['lon_num']}"
                        st.link_button("📍 Ir", map_url, use_container_width=True)
        else:
            st.warning("No hay resultados en ese radio.")
else:
    st.info("Intentando conectar con el servicio oficial... Si el error persiste, el servidor del Ministerio podría estar caído temporalmente.")
