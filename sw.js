const CACHE = 'itbi-v6';
const ASSETS = ['./','./index.html','./ITBI_SP_residencial.db.gz'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => {
    if (e.request.url.includes('.db.gz') || e.request.url.includes('index.html')) {
      return caches.open(CACHE).then(c => { c.put(e.request, res.clone()); return res; });
    }
    return res;
  })));
});
