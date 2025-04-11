const CACHE_NAME = 'votacao-cache-v1';
const urlsToCache = [
  '/',
  '/resultados_premio',
  '/static/css/bootstrap.min.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

// Instala e cacheia arquivos essenciais
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
});

// Intercepta requisições e responde do cache, se disponível
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
