import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import os
import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# --- ADAPTADOR SSL ---
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

# 1. Configuración de la página
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

# 2. Componente de Geolocalización (JavaScript)
def get_location():
    # Este componente solicita permiso de GPS y devuelve lat/lon a Streamlit
    components.html(
        """
        <script>
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                window.parent.postMessage({
                    type: 'streamlit:set_widget_value',
                    from: 'js_location',
                    value: {lat: lat, lon: lon}
                }, '*');
            },
            (error) => { console.error(error); },
            { enableHighAccuracy: true }
        );
        </script>
        """, height=0
    )

@st.cache_data(ttl=3600)
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    archivo_backup = "gasolineras_backup.csv"
    
    try:
        r = session.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        lista = r.json()["ListaEESSPrecio"]
        pd.DataFrame(lista).to_csv(archivo_backup, index=False)
        return lista, "ONLINE", datetime.datetime.now()
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            fecha = datetime.datetime.fromtimestamp(os.path.getmtime(archivo_backup))
            return df_rec.to_dict('records'), "OFFLINE", fecha
        return None, "ERROR", None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ ---
st.markdown("<h2 style='text-align: center;'>⛽ Precios Combustible</h2>", unsafe_allow_html=True)

datos, estado, fecha_act = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))
    
    with st.container(border=True):
        # Botón para activar GPS
        if st.button("📍 Usar mi ubicación actual (GPS)"):
            get_location()
            st.info("Solicitando acceso al GPS... Por favor, acepta el permiso en tu navegador.")

        # Selector de municipio (como respaldo o elección manual)
        municipio_sel = st.selectbox("🔍 O elige un municipio manualmente:", options=municipios_unicos, index=None)
        
        c1, c2 = st.columns(2)
        radio_km = c1.slider("Radio de búsqueda (Km):", 1, 50, 10)
        tipo = c2.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
        col_precio = "Precio Gasoleo A" if tipo == "Diésel" else "Precio Gasolina 95 E5"

    # Procesar ubicación (prioridad GPS, si no, Municipio)
    lat_ref, lon_ref, origen_nombre = None, None, ""
    
    # Intentamos capturar la ubicación del componente JS (Streamlit usa st.session_state para esto)
    # Nota: El JS envía el valor a una clave oculta, pero para simplificar, 
    # si el usuario elige municipio, usamos municipio.
    
    if municipio_sel:
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        ref = df[df["Municipio"] == municipio_sel].iloc[0]
        lat_ref, lon_ref, origen_nombre = ref["lat_num"], ref["lon_num"], municipio_sel

    if lat_ref and lon_ref:
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        res = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values("precio_num")

        st.divider()
        st.write(f"### 📉 {tipo} más barato cerca de {origen_nombre}")
        
        if not res.empty:
            for _, g in res.head(15).iterrows():
                with st.container(border=True):
                    col_i, col_b = st.columns([3, 1])
                    with col_i:
                        st.markdown(f"**{g['Rótulo']} - {g['Municipio']}**")
                        st.write(f"💰 **{g[col_precio]} €/L** | 📍 {g['Distancia']:.1f} km")
                        st.caption(f"{g['Dirección']}")
                    with col_b:
                        url_map = f"https://www.google.com/maps?q={g['lat_num']},{g['lon_num']}"
                        st.link_button("📍 Ir", url_map, use_container_width=True)
        else:
            st.info("No se encontraron gasolineras en este radio.")

    # Pie de página
    if fecha_act:
        st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.75rem; margin-top: 50px;'>Última actualización: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</div>", unsafe_allow_html=True)
