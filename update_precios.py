import json
import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)


url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"

session = requests.Session()
session.mount("https://", SSLAdapter())

r = session.get(url, timeout=25)
r.raise_for_status()

payload = {
    "fecha_descarga": datetime.datetime.now().isoformat(),
    "datos": r.json()["ListaEESSPrecio"]
}

with open("precios_gasolineras.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
