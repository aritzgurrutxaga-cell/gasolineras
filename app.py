import streamlit as st
import requests
import pandas as pd
import numpy as np
import os
import datetime
import pytz
from streamlit_js_eval import get_geolocation
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

# --- CSS: DISEÑO CHULO Y AJUSTE MILIMÉTRICO ---
st.markdown("""
    <style>
        /* 1. Bajar el contenido para que no se pegue al marco superior del móvil */
        .block-container {padding-top: 3rem; padding-bottom: 0rem;}
        
        /* 2. Diseño del Título: Degradado profesional y forzado a una línea */
        .cool-title {
            text-align: center;
            font-family: 'Inter', system-ui, sans-serif;
            font-weight: 900;
            /* Fórmula restrictiva: mínimo 16px, ideal 5.5% del ancho, máximo 32px */
            font-size: clamp(16px, 5.5vw, 32px); 
            white-space: nowrap; 
            overflow: hidden; 
            margin-top: 0;
            margin-bottom: 0.2rem;
            letter-spacing: -0.5px;
            /* Efecto Degradado de Azul Marino a Verde Esmeralda */
            background: linear-gradient(90deg, #1E3A8A, #059669);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* 3. Ajustes de compresión para el resto de elementos */
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) { margin-top: 1rem; }
        div[data-testid="stSlider"] {margin-bottom: -1rem;}
        div[data-testid="stRadio"] {margin-bottom: -1rem;}
    </style>
""", unsafe_allow_html=True)

# --- CABECERA DE DISEÑO ---
st.markdown("<h1 class='cool-title'>Buscador Gasolineras</h1>", unsafe_allow_html=True)

# 2. Carga de Datos
@st.cache_data(ttl=3600, show_spinner="Actualizando Base de Datos, un momento por favor")
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
