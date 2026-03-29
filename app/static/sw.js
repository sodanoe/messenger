// ─────────────────────────────────────────────────────────
//  Service Worker — нужен для push-уведомлений в Chrome
//  Размещать: /sw.js (корень домена, рядом с index.html)
//  FastAPI:   app.mount("/", StaticFiles(directory="static", html=True))
//             или отдельный роут: @app.get("/sw.js")
// ─────────────────────────────────────────────────────────

self.addEventListener('install', e => {
  self.skipWaiting();  // активируемся сразу, не ждём закрытия старых вкладок
});

self.addEventListener('activate', e => {
  e.waitUntil(clients.claim());  // берём контроль над уже открытыми вкладками
});

// Клик по уведомлению — фокусируем открытую вкладку или открываем новую
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      const existing = list.find(c => c.url && c.url.includes(self.location.origin));
      if (existing) return existing.focus();
      return clients.openWindow('/');
    })
  );
});
