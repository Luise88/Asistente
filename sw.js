// Service worker del Asistente: abre rápido y funciona sin internet.
// Regla de oro: pase lo que pase, SIEMPRE devuelve una respuesta (nunca deja la app trabada).
const VERSION = 'asistente-v14';
const SHELL = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png'];
const ESPERA_MAX = 3000;   // ms: si internet tarda más, abre con la copia guardada

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => Promise.all(SHELL.map(u => fetch(u, { cache: 'no-store' })
        .then(r => (r.ok && !r.redirected) ? c.put(u, r) : null)
        .catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Pedido a internet con tiempo máximo
function conTiempo(promesa, ms) {
  return new Promise(resolve => {
    const t = setTimeout(() => resolve(null), ms);
    promesa.then(r => { clearTimeout(t); resolve(r); }, () => { clearTimeout(t); resolve(null); });
  });
}
async function copiaGuardada(url) {
  const c = await caches.open(VERSION);
  return (await c.match(url, { ignoreSearch: true })) || null;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;           // Gemini, clima, agenda, etc.: directo a internet

  // Apertura de la app (página principal)
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      try {
        const red = fetch(url.pathname, { cache: 'no-store', credentials: 'same-origin' });
        const r = await conTiempo(red, ESPERA_MAX);
        if (r && r.ok && !r.redirected) {
          const copia = r.clone();
          caches.open(VERSION).then(c => c.put('./index.html', copia)).catch(() => {});
          return r;
        }
        red.then(x => { if (x && x.ok && !x.redirected) caches.open(VERSION).then(c => c.put('./index.html', x)); }).catch(() => {});
        const g = (await copiaGuardada('./index.html')) || (await copiaGuardada('./'));
        if (g) return g;
        return await fetch(req);                         // sin copia: esperar a internet
      } catch (err) {
        return fetch(req);                               // último recurso: comportamiento normal del navegador
      }
    })());
    return;
  }

  // Íconos y manifiesto: copia guardada al instante; noticias/alertas: siempre lo último
  if (/\.(png|json)$/.test(url.pathname) && !/noticias|alertas/.test(url.pathname)) {
    e.respondWith((async () => {
      try { return (await copiaGuardada(url.pathname)) || (await fetch(req)); }
      catch (err) { return fetch(req); }
    })());
  }
  // Todo lo demás: el navegador lo maneja normalmente
});
