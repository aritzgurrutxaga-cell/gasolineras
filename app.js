const TRAD = {
  eu: {
    subtitulo: "Konparatu prezioak eta aurreztu depositua betetzean.",
    btn_inicio: "📍 Erakutsi gasolindegiak",
    btn_inicio_sub: "Gomendagarria da kokapena onartzea bilatzeko",
    localizando: "⏳ Kokapena bilatzen...",
    localizando_countdown: "⏳ Kokapena bilatzen... {s} segundo",
    localizando_countdown_plural: "⏳ Kokapena bilatzen... {s} segundo",
    escribe_muni: "📍 Idatzi zure udalerria:",
    placeholder: "Bilatu...",
    btn_confirmar: "🔍 Bilatu",
    titulo_buscar: "Bilatu",
    titulo_resultados: "{m} inguruko emaitzak",
    seleccione_municipio: "Hautatu udalerri bat.",
    error_con: "Konexio errorea.",
    navegar: "Nabigatu",
    distancia_fmt: "📍 {d} km-ra",
    sin_resultados: "Ez da gasolindegirik aurkitu hautatutako erradioan.",
    municipio_no_valido: "Aukeratu zerrendako udalerri bat.",
    ubicacion_no_disponible: "Ezin izan da kokapena lortu. Bilatu udalerria eskuz."
  },
  es: {
    subtitulo: "Compara precios en tiempo real y ahorra en cada repostaje.",
    btn_inicio: "📍 Mostrar gasolineras",
    btn_inicio_sub: "Es recomendable permitir la ubicación para buscar",
    localizando: "⏳ Localizando...",
    localizando_countdown: "⏳ Localizando... {s} segundo",
    localizando_countdown_plural: "⏳ Localizando... {s} segundos",
    escribe_muni: "📍 Escribe tu municipio:",
    placeholder: "Buscar...",
    btn_confirmar: "✅ Confirmar selección",
    titulo_buscar: "Buscar",
    titulo_resultados: "Resultados cerca de {m}",
    seleccione_municipio: "Seleccione un municipio.",
    error_con: "Error de conexión.",
    navegar: "Navegar",
    distancia_fmt: "📍 A {d} km",
    sin_resultados: "No se han encontrado gasolineras en el radio seleccionado.",
    municipio_no_valido: "Selecciona un municipio de la lista.",
    ubicacion_no_disponible: "No se ha podido obtener la ubicación. Busca el municipio manualmente."
  }
};

let datos = [];
let municipios = [];
let lang = localStorage.getItem("lang_gasolineras") || "eu";

let tipoCombustible = localStorage.getItem("comb_gasolineras") || "Diésel";
let radioKm = Number(localStorage.getItem("radio_gasolineras") || 5);

let latRef = null;
let lonRef = null;
let muniRef = null;
let intervaloCuentaAtras = null;

const pantallaInicio = document.getElementById("pantalla-inicio");
const pantallaLocalizando = document.getElementById("pantalla-localizando");
const pantallaManual = document.getElementById("pantalla-manual");
const pantallaResultados = document.getElementById("pantalla-resultados");

const btnEu = document.getElementById("btn-eu");
const btnEs = document.getElementById("btn-es");
const subtitulo = document.getElementById("subtitulo");
const btnUbicacion = document.getElementById("btn-ubicacion");
const btnUbicacionText = document.getElementById("btn-ubicacion-text");
const btnUbicacionSub = document.getElementById("btn-ubicacion-sub");
const textoLocalizando = document.getElementById("texto-localizando");
const textoMunicipio = document.getElementById("texto-municipio");

const inputMunicipio = document.getElementById("input-municipio");
const sugerenciasMunicipio = document.getElementById("sugerencias-municipio");
const btnConfirmar = document.getElementById("btn-confirmar");

const tituloBuscar = document.getElementById("titulo-buscar");
const tituloResultados = document.getElementById("titulo-resultados");
const inputMunicipioAjustes = document.getElementById("input-municipio-ajustes");
const btnClearMuni = document.getElementById("btn-clear-muni");
const sugerenciasMunicipioAjustes = document.getElementById("sugerencias-municipio-ajustes");
const resultados = document.getElementById("resultados");

function t() {
  return TRAD[lang];
}

function escapeHtml(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">")
    .replaceAll('"', "\"")
    .replaceAll("'", "'");
}

function mostrarPantalla(nombre) {
  pantallaInicio.classList.add("hidden");
  pantallaLocalizando.classList.add("hidden");
  pantallaManual.classList.add("hidden");
  pantallaResultados.classList.add("hidden");

  if (nombre === "inicio") pantallaInicio.classList.remove("hidden");
  if (nombre === "localizando") pantallaLocalizando.classList.remove("hidden");
  if (nombre === "manual") pantallaManual.classList.remove("hidden");
  if (nombre === "resultados") pantallaResultados.classList.remove("hidden");
}

function aplicarIdioma() {
  document.documentElement.lang = lang;

  btnEu.classList.toggle("active", lang === "eu");
  btnEs.classList.toggle("active", lang === "es");

  subtitulo.textContent = t().subtitulo;
  btnUbicacionText.textContent = t().btn_inicio;
  btnUbicacionSub.textContent = t().btn_inicio_sub;
  textoMunicipio.textContent = t().escribe_muni;
  inputMunicipio.placeholder = t().placeholder;
  btnConfirmar.textContent = t().btn_confirmar;

  if (tituloBuscar) tituloBuscar.textContent = t().titulo_buscar;

  if (!pantallaResultados.classList.contains("hidden")) {
    pintarResultados();
  }
}

function normalizarTexto(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toUpperCase();
}

function normalizarNumero(valor) {
  if (valor === null || valor === undefined) return NaN;

  const texto = String(valor).trim();

  if (
    texto === "" ||
    texto.toUpperCase() === "N/A" ||
    texto.toUpperCase() === "NA" ||
    texto.toUpperCase() === "NULL" ||
    texto === "-"
  ) {
    return NaN;
  }

  const numero = Number(texto.replace(",", "."));

  return Number.isFinite(numero) ? numero : NaN;
}

function calcularDistancia(lat1, lon1, lat2, lon2) {
  const R = 6371.0;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const rLat1 = lat1 * Math.PI / 180;
  const rLat2 = lat2 * Math.PI / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rLat1) * Math.cos(rLat2) * Math.sin(dLon / 2) ** 2;

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function prepararDatos(raw) {
  return raw.map(g => ({
    ...g,
    lat_num: normalizarNumero(g["Latitud"]),
    lon_num: normalizarNumero(g["Longitud (WGS84)"]),
    precio_diesel_num: normalizarNumero(g["Precio Gasoleo A"]),
    precio_g95_num: normalizarNumero(g["Precio Gasolina 95 E5"])
  }));
}

function prepararMunicipios() {
  municipios = [...new Set(datos.map(g => String(g["Municipio"] || "")).filter(Boolean))].sort();
}

function obtenerSugerencias(valor) {
  const q = normalizarTexto(valor);
  if (!q) return [];

  return municipios.filter(m => normalizarTexto(m).startsWith(q)).slice(0, 8);
}

function pintarSugerencias(input, contenedor) {
  const sugerencias = obtenerSugerencias(input.value);

  if (!sugerencias.length) {
    contenedor.classList.add("hidden");
    contenedor.innerHTML = "";
    return;
  }

  contenedor.innerHTML = sugerencias.map(m => `
    <div class="sugerencia-item" data-value="${escapeHtml(m)}">${escapeHtml(m)}</div>
  `).join("");

  contenedor.classList.remove("hidden");
}

function ocultarSugerencias() {
  sugerenciasMunicipio.classList.add("hidden");
  sugerenciasMunicipio.innerHTML = "";
  sugerenciasMunicipioAjustes.classList.add("hidden");
  sugerenciasMunicipioAjustes.innerHTML = "";
}

function buscarMunicipioValido(valor) {
  const q = normalizarTexto(valor);
  if (!q) return null;

  const exacto = municipios.find(m => normalizarTexto(m) === q);
  if (exacto) return exacto;

  const empieza = municipios.find(m => normalizarTexto(m).startsWith(q));
  if (empieza) return empieza;

  return null;
}

function municipioMasCercano(lat, lon) {
  let mejor = null;
  let mejorDistancia = Infinity;

  datos.forEach(g => {
    if (Number.isNaN(g.lat_num) || Number.isNaN(g.lon_num)) return;

    const d = calcularDistancia(lat, lon, g.lat_num, g.lon_num);
    if (d < mejorDistancia) {
      mejorDistancia = d;
      mejor = g["Municipio"];
    }
  });

  return mejor;
}

function obtenerCoordenadasMunicipio(municipio) {
  const filas = datos.filter(g => String(g["Municipio"]) === String(municipio));

  if (!filas.length) return null;

  const latitudes = filas.map(g => g.lat_num).filter(v => !Number.isNaN(v));
  const longitudes = filas.map(g => g.lon_num).filter(v => !Number.isNaN(v));

  if (!latitudes.length || !longitudes.length) return null;

  return {
    lat: latitudes.reduce((a, b) => a + b, 0) / latitudes.length,
    lon: longitudes.reduce((a, b) => a + b, 0) / longitudes.length
  };
}

function guardarEstado() {
  localStorage.setItem("comb_gasolineras", tipoCombustible);
  localStorage.setItem("radio_gasolineras", String(radioKm));
  localStorage.setItem("lang_gasolineras", lang);
}

function sincronizarFiltrosUI() {
  if (muniRef && muniRef !== "GPS") {
    inputMunicipioAjustes.value = muniRef;
  } else {
    inputMunicipioAjustes.value = "";
  }

  document.querySelectorAll(".radio-btn").forEach(btn => {
    btn.classList.toggle("active", Number(btn.dataset.radio) === radioKm);
  });

  document.querySelectorAll(".fuel-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.fuel === tipoCombustible);
  });
}

function pintarResultados() {
  guardarEstado();

  if (!muniRef) {
    if (tituloResultados) tituloResultados.textContent = lang === "eu" ? "Emaitzak" : "Resultados";
    resultados.innerHTML = `<div class="mensaje">${escapeHtml(t().seleccione_municipio)}</div>`;
    return;
  }

  if (tituloResultados) {
    if (muniRef === "GPS") {
      tituloResultados.textContent = lang === "eu" ? "Zure kokapenetik gertuko emaitzak" : "Resultados cerca de tu ubicación";
    } else {
      tituloResultados.textContent = t().titulo_resultados.replace("{m}", muniRef);
    }
  }

  const colPrecio = tipoCombustible === "Diésel" ? "precio_diesel_num" : "precio_g95_num";

  const filtradas = datos
    .filter(g => !Number.isNaN(g.lat_num) && !Number.isNaN(g.lon_num))
    .map(g => ({
      ...g,
      distancia: calcularDistancia(latRef, lonRef, g.lat_num, g.lon_num)
    }))
    .filter(g => !Number.isNaN(g.distancia) && g.distancia <= radioKm)
    .sort((a, b) => {
      const pa = Number.isFinite(a[colPrecio]) ? a[colPrecio] : Number.POSITIVE_INFINITY;
      const pb = Number.isFinite(b[colPrecio]) ? b[colPrecio] : Number.POSITIVE_INFINITY;

      if (pa !== pb) {
        return pa - pb;
      }

      return a.distancia - b.distancia;
    });

  if (filtradas.length === 0) {
    resultados.innerHTML = `<div class="mensaje">${escapeHtml(t().sin_resultados)}</div>`;
    return;
  }

  resultados.innerHTML = filtradas.map(g => {
    const diesel = Number.isFinite(g.precio_diesel_num) && g["Precio Gasoleo A"]
      ? `${escapeHtml(g["Precio Gasoleo A"])}€`
      : "N/A";

    const g95 = Number.isFinite(g.precio_g95_num) && g["Precio Gasolina 95 E5"]
      ? `${escapeHtml(g["Precio Gasolina 95 E5"])}€`
      : "N/A";

    const distancia = t().distancia_fmt.replace("{d}", g.distancia.toFixed(2));
    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(g.lat_num + "," + g.lon_num)}`;

    return `
      <article class="gasolinera-card">
        <div>
          <h3>${escapeHtml(g["Rótulo"] || "")} - ${escapeHtml(g["Municipio"] || "")}</h3>
          <p>⛽ <b>Diesel:</b> ${diesel} | <b>G95:</b> ${g95}</p>
          <p class="distancia">${escapeHtml(distancia)}</p>
        </div>
        <div>
          <a class="btn-navegar" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(t().navegar)}</a>
        </div>
      </article>
    `;
  }).join("");
}

function buscarPorMunicipio(valor) {
  const municipio = buscarMunicipioValido(valor);

  if (!municipio) {
    mostrarPantalla("manual");
    textoMunicipio.textContent = t().municipio_no_valido;
    return;
  }

  const coords = obtenerCoordenadasMunicipio(municipio);

  if (!coords) {
    mostrarPantalla("manual");
    textoMunicipio.textContent = t().municipio_no_valido;
    return;
  }

  muniRef = municipio;
  latRef = coords.lat;
  lonRef = coords.lon;

  ocultarSugerencias();
  mostrarPantalla("resultados");
  sincronizarFiltrosUI();
  pintarResultados();
}

function iniciarCuentaAtras() {
  if (intervaloCuentaAtras) {
    clearInterval(intervaloCuentaAtras);
  }

  let segundos = 5;
  textoLocalizando.textContent = t().localizando_countdown_plural.replace("{s}", segundos);

  intervaloCuentaAtras = setInterval(() => {
    segundos -= 1;

    if (segundos <= 0) {
      clearInterval(intervaloCuentaAtras);
      intervaloCuentaAtras = null;
      textoLocalizando.textContent = t().localizando;
      return;
    }

    const clave = segundos === 1 ? "localizando_countdown" : "localizando_countdown_plural";
    textoLocalizando.textContent = t()[clave].replace("{s}", segundos);
  }, 1000);
}

function pararCuentaAtras() {
  if (intervaloCuentaAtras) {
    clearInterval(intervaloCuentaAtras);
    intervaloCuentaAtras = null;
  }
}

function iniciarGeolocalizacion() {
  mostrarPantalla("localizando");
  iniciarCuentaAtras();

  if (!navigator.geolocation) {
    pararCuentaAtras();
    textoMunicipio.textContent = t().ubicacion_no_disponible;
    mostrarPantalla("manual");
    return;
  }

  setTimeout(() => {
    navigator.geolocation.getCurrentPosition(
      pos => {
        pararCuentaAtras();

        latRef = pos.coords.latitude;
        lonRef = pos.coords.longitude;
        muniRef = municipioMasCercano(latRef, lonRef) || "GPS";

        mostrarPantalla("resultados");
        sincronizarFiltrosUI();
        pintarResultados();
      },
      () => {
        pararCuentaAtras();

        textoMunicipio.textContent = t().ubicacion_no_disponible;
        mostrarPantalla("manual");
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0
      }
    );
  }, 600);
}

async function iniciarSegunPermisoUbicacion() {
  if (!navigator.geolocation) {
    mostrarPantalla("inicio");
    return;
  }

  if (!navigator.permissions || !navigator.permissions.query) {
    mostrarPantalla("inicio");
    return;
  }

  try {
    const permiso = await navigator.permissions.query({ name: "geolocation" });

    if (permiso.state === "granted") {
      iniciarGeolocalizacion();
    } else {
      mostrarPantalla("inicio");
    }
  } catch (e) {
    mostrarPantalla("inicio");
  }
}

async function cargarDatos() {
  try {
    const res = await fetch("./precios_gasolineras.json?v=" + Date.now(), { cache: "no-store" });

    if (!res.ok) {
      throw new Error("No se encuentra precios_gasolineras.json");
    }

    const payload = await res.json();

    let lista = [];

    if (Array.isArray(payload)) {
      lista = payload;
    } else if (payload && Array.isArray(payload.datos)) {
      lista = payload.datos;
    } else if (payload && Array.isArray(payload.ListaEESSPrecio)) {
      lista = payload.ListaEESSPrecio;
    } else {
      throw new Error("Formato JSON no reconocido");
    }

    datos = prepararDatos(lista);
    prepararMunicipios();

    if (!datos.length || !municipios.length) {
      throw new Error("JSON sin datos válidos");
    }

    iniciarSegunPermisoUbicacion();
  } catch (e) {
    pantallaInicio.innerHTML = `
      <h1 class="titulo">gasolina<span>.eus</span></h1>
      <div class="mensaje">${escapeHtml(t().error_con)}</div>
      <div class="mensaje">${escapeHtml(e.message)}</div>
    `;
    mostrarPantalla("inicio");
  }
}

btnEu.addEventListener("click", () => {
  lang = "eu";
  aplicarIdioma();
  guardarEstado();
});

btnEs.addEventListener("click", () => {
  lang = "es";
  aplicarIdioma();
  guardarEstado();
});

btnUbicacion.addEventListener("click", iniciarGeolocalizacion);

inputMunicipio.addEventListener("input", () => {
  textoMunicipio.textContent = t().escribe_muni;
  pintarSugerencias(inputMunicipio, sugerenciasMunicipio);
});

inputMunicipioAjustes.addEventListener("input", () => {
  pintarSugerencias(inputMunicipioAjustes, sugerenciasMunicipioAjustes);
});

btnClearMuni.addEventListener("click", () => {
  inputMunicipioAjustes.value = "";
  muniRef = null;
  latRef = null;
  lonRef = null;
  ocultarSugerencias();
  sincronizarFiltrosUI();
  pintarResultados();
  inputMunicipioAjustes.focus();
});

sugerenciasMunicipio.addEventListener("click", e => {
  const item = e.target.closest(".sugerencia-item");
  if (!item) return;

  inputMunicipio.value = item.dataset.value;
  buscarPorMunicipio(item.dataset.value);
});

sugerenciasMunicipioAjustes.addEventListener("click", e => {
  const item = e.target.closest(".sugerencia-item");
  if (!item) return;

  const municipioElegido = item.dataset.value;
  const coords = obtenerCoordenadasMunicipio(municipioElegido);

  if (coords) {
    muniRef = municipioElegido;
    latRef = coords.lat;
    lonRef = coords.lon;
  }

  ocultarSugerencias();
  sincronizarFiltrosUI();
  pintarResultados();
});

btnConfirmar.addEventListener("click", () => {
  buscarPorMunicipio(inputMunicipio.value);
});

inputMunicipio.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    e.preventDefault();
    buscarPorMunicipio(inputMunicipio.value);
  }
});

inputMunicipioAjustes.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    e.preventDefault();
    const municipioElegido = buscarMunicipioValido(inputMunicipioAjustes.value);

    if (municipioElegido) {
      const coords = obtenerCoordenadasMunicipio(municipioElegido);
      if (coords) {
        muniRef = municipioElegido;
        latRef = coords.lat;
        lonRef = coords.lon;
      }
    }
    ocultarSugerencias();
    sincronizarFiltrosUI();
    pintarResultados();
  }
});

document.querySelectorAll(".radio-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    radioKm = Number(btn.dataset.radio);
    sincronizarFiltrosUI();
    pintarResultados();
  });
});

document.querySelectorAll(".fuel-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    tipoCombustible = btn.dataset.fuel;
    sincronizarFiltrosUI();
    pintarResultados();
  });
});

document.addEventListener("click", e => {
  if (!e.target.closest(".autocomplete")) {
    ocultarSugerencias();
  }
});

aplicarIdioma();
cargarDatos();
