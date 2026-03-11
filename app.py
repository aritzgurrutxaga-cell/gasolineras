# 3. Carga de Datos OPTIMIZADA
@st.cache_data(ttl=3600, show_spinner="Sincronizando con el Ministerio...")
def cargar_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    
    # Headers completos para parecer un navegador real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    }
    
    try:
        # Aumentamos el timeout a 30 segundos (los servidores del gobierno a veces saturan)
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status() # Lanza error si la respuesta no es 200 OK
        return r.json()["ListaEESSPrecio"]
    except requests.exceptions.Timeout:
        st.error("⌛ El servidor del Ministerio tarda demasiado en responder. Reintenta en unos instantes.")
        return None
    except Exception as e:
        # Esto te ayudará a ver el error real en la consola de Streamlit
        print(f"Error de conexión: {e}")
        return None
