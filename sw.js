const CACHE_NAME = 'gasolina-beta-1-v1';
const ASSETS = [
  './',
  './index.html',
  './styles.css?v=21',
  './app.js?v=22',
  './manifest.json'
];

// Instalación: Guardamos el "caparazón" de la web en la caché
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activación: Limpiamos cachés antiguas si actualizamos la versión
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

  // Regla estricta: Los precios NUNCA se cachean en el Service Worker, siempre vienen de la red
  if (url.pathname.includes('precios_gasolineras.json')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Para el resto (HTML, CSS, JS), buscamos en caché primero. Si no está, vamos a la red.
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
