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

# AJUSTES DE ESPACIADO PRECISOS
st.markdown("""
    <style>
        .block-container {padding-top: 2.8rem;}
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stSlider"]) {
            margin-top: 1.2rem;
        }
        /* Reduce margen del slider */
        div[data-testid="stSlider"] {margin-bottom: -1rem;}
        
        /* AJUSTE SOLICITADO: Reduce espacio entre radio y la línea de debajo */
        div[data-testid="stRadio"] {margin-bottom: -1.5rem;}
        hr {margin-top: 0rem; margin-bottom: 1rem;}
        
        h1 {margin-top: -0.8rem; margin-bottom: 0.8rem;}
        
        /* Asegurar que las columnas de resultados no salten en móviles pequeños */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            align-items: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# Título
st.markdown(
    """
    <h1 style='text-align: center; font-size: clamp(22px, 7vw, 38px); white-space: nowrap; overflow: hidden;'>
        ⛽ Buscador Gasolineras
    </h1>
    """, 
    unsafe_allow_html=True
)

# 2. Carga de Datos con Filtro Comercial
@st.cache_data(ttl=3600, show_spinner="Actualizando Base de Datos, un momento por favor")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {'User-Agent
