const CACHE_NAME = 'gasolina-beta-1-v2'; // Actualizado para forzar la instalación de esta nueva versión
const ASSETS = [
  './',
  './index.html',
  './styles.css?v=21',
  './app.js?v=21', // Corregido para que coincida con el index.html
  './manifest.json',
  './icon-192.png', // Iconos añadidos para soporte offline total
  './icon-512.png'
];

// Instalación: Guardamos el "caparazón" de la web en la caché
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activación: Limpiamos cachés antiguas
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Interceptamos las peticiones de red
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Estrategia "Network First" para el JSON de precios
  if (url.pathname.includes('precios_gasolineras.json')) {
    event.respondWith(
      fetch(event.request)
        .then(networkResponse => {
          // Si la red responde bien, guardamos una copia fresca en caché y la devolvemos
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
        })
        .catch(() => {
          // Si falla la red (sin conexión), buscamos la última versión guardada en caché
          return caches.match(event.request);
        })
    );
    return;
  }

  // Estrategia "Cache First" para el resto (HTML, CSS, JS, Iconos)
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
