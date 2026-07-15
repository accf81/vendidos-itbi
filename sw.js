// Este service worker existia pra guardar o banco de dados grande em cache
// (arquitetura antiga). Não é mais necessário — a busca agora consulta o
// Supabase direto, sem download nenhum. Este arquivo só limpa o cache velho
// de quem já tinha instalado, e se desativa sozinho.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll())
      .then((clients) => clients.forEach((c) => c.navigate(c.url)))
  );
});
