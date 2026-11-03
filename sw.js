// Service worker: permite instalar la app y que abra rápido.
// Al publicar cambios, subí el número de versión.
const VERSION = 'asistente-v13';
const SHELL = ['./', 'index.html', 'manifest.json', 'icon-192.png', 'icon-512.png'];
const ESPERA_MAX = 1200;   // ms: si internet tarda más, abre con la copia guardada

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Archivos propios: intenta traer la versión nueva, pero si internet tarda más de 1,2 segundos
// abre con la copia guardada y termina de actualizar por detrás (se ve en la próxima apertura).
// Las consultas a Gemini, Claude, el clima o la agenda no pasan por acá.
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  const red = fetch(e.request, { cache: 'no-cache' }).then(res => {
    if (res.ok) { const copia = res.clone(); caches.open(VERSION).then(c => c.put(e.request, copia)); }
    return res;
  });
  e.waitUntil(red.catch(() => {}));
  e.respondWith((async () => {
    const guardada = await caches.match(e.request, { ignoreSearch: true });
    if (!guardada) return red.catch(() => caches.match('index.html'));
    const espera = new Promise(r => setTimeout(() => r(guardada), ESPERA_MAX));
    return Promise.race([red.catch(() => guardada), espera]);
  })());
});
