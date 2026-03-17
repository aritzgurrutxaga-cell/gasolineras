import streamlit as st
import pandas as pd
import datetime

# 1. Configuración de la página (esto siempre debe ir primero)
st.set_page_config(page_title="gasolina.eus", page_icon="⛽", layout="centered")

# --- BLOQUE CSS PERSONALIZADO (Aquí están los cambios) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;700;800&display=swap');

    /* Ocultar el header de Streamlit y el menú 'Manage app' */
    header {visibility: hidden;}
    .stAppDeployButton {display: none;}
    #stDecoration {display: none;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    .reportview-container .main .footer {display: none;}

    /* Limpiar espacios innecesarios */
    .block-container { padding-top: 2rem !important; }

    /* Estilo para el logotipo 'gasolina.eus' */
    .logo-container {
        text-align: center;
        margin-bottom: 0px;
    }
    .logo-main {
        font-family: 'Poppins', sans-serif;
        font-size: 38px;
        font-weight: 800;
        color: #263238; /* Azul oscuro/gris */
    }
    .logo-eus {
        color: #ef4444; /* Rojo */
    }

    /* Estilo para el Expander de Ajustes */
    div[data-testid="stExpander"] {
        background-color: #f1f5f9;
        border-radius: 12px;
        border: none;
        margin-bottom: 1.5rem;
    }

    /* Estilo para los botones de radio (Diésel / G95) */
    div[data-testid="stRadio"] > div {
        flex-direction: row;
        gap: 20px;
    }

    /* Estilo para el botón rojo 'Buscar' */
    div[data-testid="stButton"] button {
        background-color: #ef4444;
        color: white;
        border-radius: 20px;
        font-weight: bold;
        width: 100%;
        border: none;
        padding: 10px;
        font-family: 'Poppins', sans-serif;
        transition: background-color 0.3s ease;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #dc2626;
        border: none;
    }

    /* Píldora de resumen de filtros */
    .filter-summary {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 30px;
        padding: 10px 20px;
        text-align: center;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        font-family: 'Poppins', sans-serif;
        font-weight: 500;
        color: #263238;
        font-size: 14px;
    }

    /* Estilo para las tarjetas de las gasolineras */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 15px !important;
        padding: 20px 20px 10px 20px !important; /* Reducido padding inferior interno */
        margin-bottom: 1rem !important;
    }

    /* Botón de navegación personalizado (CORREGIDO) */
    .link-button-custom {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #f1f5f9; /* Gris suave */
        color: #263238 !important; /* Texto oscuro */
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 20px;
        text-decoration: none !important;
        font-family: 'Poppins', sans-serif;
        font-weight: 500;
        font-size: 14px;
        
        /* CAMBIOS AQUÍ */
        width: 90% !important; /* Un "pelín menos" que el ancho completo (antes era auto o mayor) */
        margin: 15px auto 15px auto !important; /* Centrado horizontal + margen inferior aumentado (para subirlo) */
        
        transition: all 0.3s ease;
        text-align: center;
    }
    .link-button-custom:hover {
        background-color: #e2e8f0;
        transform: translateY(-2px);
    }
    .link-button-custom img {
        margin-right: 10px;
        width: 18px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATOS DE EJEMPLO (Basados en la imagen) ---
@st.cache_data
def obtener_datos_ejemplo():
    return pd.DataFrame({
        'Empresa': ['PETROPRIX - Anoeta', 'BALLENOIL - Irura', 'PLENERGY - Irura'],
        'Municipio': ['Tolosa', 'Irura', 'Irura'],
        'Precio_Diesel': [1.799, 1.799, 1.829],
        'Precio_G95': [1.689, 1.689, 1.719],
        'Distancia': [1.77, 4.15, 6.20], # Distancias estimadas
        'Lat': [43.136, 43.155, 43.160], # Coordenadas para Maps
        'Lon': [-2.067, -2.050, -2.045]
    })

df = obtener_datos_ejemplo()

# --- HEADER (gasolina.eus) ---
st.markdown("""
<div class="logo-container">
    <span class="logo-main">gasolina<span class="logo-eus">.eus</span></span>
</div>
""", unsafe_allow_html=True)

# --- AJUSTES DE BÚSQUEDA (Zumarraga por defecto) ---
with st.expander("⚙️ Ajustes de búsqueda", expanded=False):
    st.selectbox("Cambiar municipio:", options=["Zumarraga", "Tolosa", "San Sebastián"], index=0)
    
    # Radios con 4 opciones (como en image_0.png)
    radio_cols = st.columns(1)
    with radio_cols[0]:
        st.radio("Radio de búsqueda:", options=["5 km", "10 km", "20 km", "50 km"], index=0, horizontal=True)
    
    # Combustible
    fuel_cols = st.columns(1)
    with fuel_cols[0]:
        st.radio("Ordenar por precio de:", options=["Diésel", "G95"], index=0, horizontal=True)
    
    st.button("🔍 Buscar")

# --- PÍLDORA DE RESUMEN DE FILTROS (Tolosa, Diésel como en la imagen) ---
# Usando iconos emojis para simular los de la imagen
st.markdown("""
<div class="filter-summary">
    📍 Tolosa | 🚗 5 km | ⛽ Diésel
</div>
""", unsafe_allow_html=True)

# --- LISTADO DE GASOLINERAS ---
st.write("---") # Separador

maps_icon_url = "https://upload.wikimedia.org/wikipedia/commons/a/aa/Google_Maps_icon_%282020%29.svg"

# Generar tarjetas dinámicamente
for index, row in df.iterrows():
    with st.container(border=True):
        # Diseño de la tarjeta: Título grande, precios debajo
        st.write(f"### {row['Empresa']}")
        
        # Fila de precios con iconos emoji
        st.markdown(f"⛽ **D:** {row['Precio_Diesel']:.3f}€ | **G95:** {row['Precio_G95']:.3f}€", unsafe_allow_html=True)
        
        # Fila de distancia
        st.write(f"📍 A {row['Distancia']:.2f} km")
        
        # Separador interno antes del botón
        st.write("")
        
        # Botón de Navegar personalizado usando Markdown
        # Construir la URL de Google Maps api v1 dir (navegación)
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['Lat']},{row['Lon']}"
        
        # TRUCO: Un div con text-align center para forzar el centrado horizontal del link en la tarjeta
        st.markdown(f"""
        <div style="text-align: center;">
            <a href="{maps_url}" target="_blank" class="link-button-custom">
                <img src="{maps_icon_url}" alt="Google Maps">
                Navegar
            </a>
        </div>
        """, unsafe_allow_html=True)

# --- PIE DE PÁGINA (Para ocultar Streamlit elements) ---
# Hecho en el bloque CSS inicial
