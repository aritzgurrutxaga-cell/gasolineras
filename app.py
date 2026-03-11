import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np

# 1. Configuración de la página
st.set_page_config(page_title="Precios Combustible", page_icon="⛽", layout="centered")

# Estilos personalizados para móvil y limpieza de interfaz
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {
            padding: 1rem !important;
        }
        hr {
            margin: 0.8rem 0 !important;
        }
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid #ccc !important;
        }
        .titulo-una-linea {
            text-align: center;
            white-space: nowrap;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Función JS para ocultar teclado en móviles tras seleccionar
def ocultar_teclado():
    components.html(
        """<script>
        var inputs = window.parent.document.querySelectorAll('input');
        for (var i=0; i<inputs.length; i++) { inputs[i].blur(); }
        window.parent.document.activeElement.blur();
        </script>""", height=0, width=0
    )

# 3. Carga de Datos con Headers de Navegador (Solución al bloqueo)
@st.cache_data(ttl=3600, show_spinner="Actualizando precios oficiales...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    
    # Simular un navegador real para evitar bloqueos del Ministerio
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        # Aumentamos el timeout porque el servidor del gobierno suele ser lento
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()["ListaEESSPrecio"]
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# 4. Cálculo de distancia (Fórmula de Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0 # Radio de la Tierra en km
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

# --- INTERFAZ DE USUARIO ---
st.markdown("<div class='titulo-una-linea'>⛽ Precios Combustible</div>", unsafe_allow_html=True)

datos = cargar_datos()

if datos:
    df = pd.DataFrame(datos)
    municipios_unicos = sorted(list(set([g["Municipio"] for g in datos])))
    
    # Panel de control
    with st.container(border=True):
        municipio_sel = st.selectbox(
            "🔍 Tu ubicación (Municipio):",
            options=municipios_unicos,
            index=None,
            placeholder="Escribe o elige tu municipio..."
        )
        
        col_radio, col_tipo = st.columns(2)
        with col_radio:
            radio_km = st.slider("Radio de búsqueda (Km):", 1, 50, 10)
        with col_tipo:
            combustible = st.radio("Combustible:", ["Diésel", "G95"], horizontal=True)
            col_precio = "Precio Gasoleo A" if combustible == "Diésel" else "Precio Gasolina 95 E5"

    if municipio_sel:
        ocultar_teclado()
        
        # Limpieza de coordenadas y precios (el Ministerio usa comas)
        df["lat_num"] = pd.to_numeric(df["Latitud"].str.replace(",", "."), errors='coerce')
        df["lon_num"] = pd.to_numeric(df["Longitud (WGS84)"].str.replace(",", "."), errors='coerce')
        df["precio_num"] = pd.to_numeric(df[col_precio].str.replace(",", "."), errors='coerce')
        
        # Obtener coordenadas del municipio de referencia
        ref = df[df["Municipio"] == municipio_sel].iloc[0]
        lat_ref, lon_ref = ref["lat_num"], ref["lon_num"]
        
        # Calcular distancias
        df["Distancia"] = calcular_distancia(lat_ref, lon_ref, df["lat_num"], df["lon_num"])
        
        # Filtrar por radio y precio válido, luego ordenar
        resultados = df[(df["Distancia"] <= radio_km) & (df["precio_num"].notna())].sort_values(by="precio_num")

        st.divider()
        st.write(f"### 📉 {combustible} más barato cerca de {municipio_sel}")
        
        if not resultados.empty:
            for _, g in resultados.head(15).iterrows():
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"**{g['Rótulo']}**")
                        st.caption(f"{g['Dirección']} ({g['Municipio']})")
                        st.write(f"💰 **{g[col_precio]} €/L** |  📍 {g['Distancia']:.1f} km")
                    
                    with col_btn:
                        # URL corregida para Google Maps
                        map_url = f"https://www.google.com/maps/search/?api=1&query={g['lat_num']},{g['lon_num']}"
                        st.link_button("📍 Ir", map_url, use_container_width=True)
        else:
            st.warning("No se encontraron gasolineras con ese combustible en el radio seleccionado.")

else:
    st.error("No se ha podido obtener la información. Inténtalo de nuevo en unos minutos.")
