// Asistente — service worker DESACTIVADO.
// Este archivo solo existe para eliminar versiones anteriores que podían trabar la app.
// Al instalarse: borra las copias guardadas del Asistente (no toca las de otras apps del sitio,
// como NOW), se da de baja y recarga la app para que funcione como una página normal.
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.filter(k => k.startsWith('asistente')).map(k => caches.delete(k)));
    } catch (err) { /* nada */ }
    try { await self.registration.unregister(); } catch (err) { /* nada */ }
    try {
      const ventanas = await self.clients.matchAll({ type: 'window' });
      ventanas.forEach(v => v.navigate(v.url).catch(() => {}));
    } catch (err) { /* nada */ }
  })());
});
// Sin "fetch": el navegador carga todo directamente de internet.
