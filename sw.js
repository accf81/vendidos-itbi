const CACHE = 'itbi-v12';
const ASSETS = ['./', './index.html', './ITBI_SP_residencial.db.gz'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);

  if (req.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  if (url.pathname.endsWith('/index.html') || url.pathname === '/') {
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put('./index.html', copy));
      return res;
    }).catch(() => caches.match('./index.html')));
    return;
  }

  e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
    if (url.pathname.includes('.db.gz') || url.pathname.includes('index.html')) {
      return caches.open(CACHE).then(c => { c.put(req, res.clone()); return res; });
    }
    return res;
  })));
});
