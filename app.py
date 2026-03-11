import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
from streamlit_js_eval import get_geolocation
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
st.set_page_config(page_title="Gasolineras Baratas", page_icon="⛽", layout="centered")

# 2. Carga de Datos con Backup
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
        return lista, datetime.datetime.now()
    except Exception:
        if os.path.exists(archivo_backup):
            df_rec = pd.read_csv(archivo_backup)
            fecha = datetime.datetime.fromtimestamp(os.path.getmtime(archivo_backup))
            return df_rec.to_dict('records'), fecha
        return None, None

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ ---
st.markdown("<h2 style='text-align: center;'>⛽ Gasolineras más baratas</h2>", unsafe_allow_html=True)

datos, fecha_act = cargar_datos()

if datos:
    # 3. Obtener ubicación GPS (con validación de seguridad)
    loc = get_geolocation()
    
    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([str(g["Municipio"]) for g in datos])))

    with st.container(border=True):
        col_radio, col_tipo = st.columns(2)
        radio_km = col_radio.slider("Radio de búsqueda (Km):", 1, 50, 10)
        combustible = col_tipo.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
        col_precio = "Precio Gasoleo A" if combustible == "Diésel" else "Precio Gasolina 95 E5"
        
        # Plan B: Selector manual por si falla el GPS
        municipio_manual = st.selectbox("📍 O busca por municipio (si el GPS no carga):", 
                                       options=municipios_unicos, index=None)

    lat_user, lon_user, origen = None, None, ""

    # VALIDACIÓN DE SEGURIDAD PARA EL GPS
    if loc and 'coords' in loc:
        lat_user = loc['coords']['latitude']
        lon_user = loc['coords']['longitude']
        origen = "tu ubicación actual"
        st.success("📍 Usando tu ubicación GPS")
    elif municipio_manual:
        # Si no hay GPS pero hay municipio manual
        ref = df[df["Municipio"] == municipio_manual].iloc[0]
        # Limpiamos coordenadas del municipio (vienen con comas)
        lat_user = float(str(ref["Latitud"]).replace(",", "."))
        lon_user = float(str(ref["Longitud (WGS84)"]).replace(",", "."))
        origen = municipio_manual
    else:
        st.info("⌛ Esperando permiso de ubicación o selecciona un municipio arriba...")

    # Si logramos obtener alguna coordenada (vía GPS o Manual)
    if lat_user and lon_user:
        # Limpieza de datos general
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        df["Distancia"] = calcular_distancia(lat_user, lon_user, df["lat_num"], df["lon_num"])
        res = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values("precio_num")

        st.divider()
        st.write(f"### 📉 {combustible} más barato cerca de {origen}")
        
        if not res.empty:
            for _, g in res.head(15).iterrows():
                with st.container(border=True):
                    col_i, col_b = st.columns([3, 1])
                    with col_i:
                        st.markdown(f"**{g['Rótulo']} - {g['Municipio']}**")
                        st.write(f"💰 **{g[col_precio]} €/L** | 📍 {g['Distancia']:.2f} km")
                        st.caption(f"{g['Dirección']}")
                    with col_b:
                        # Enlace directo a ruta en Google Maps
                        url_map = f"https://www.google.com/maps/dir/?api=1&destination={g['lat_num']},{g['lon_num']}"
                        st.link_button("Ir", url_map, use_container_width=True)
        else:
            st.warning("No hay resultados en este radio.")

    # Pie de página
    if fecha_act:
        st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.75rem; margin-top: 50px;'>Sincronizado: {fecha_act.strftime('%d/%m/%Y %H:%M:%S')}</div>", unsafe_allow_html=True)
else:
    st.error("Error al cargar los datos.")
