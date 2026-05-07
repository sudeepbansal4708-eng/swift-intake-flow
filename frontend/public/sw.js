/* Service Worker for Valet Guys Push Notifications */

self.addEventListener('push', function(event) {
  let data = { title: 'Valet Guys', body: 'New notification', data: {} };

  try {
    if (event.data) {
      data = event.data.json();
    }
  } catch (e) {
    // Failed to parse push data
  }

  const isRetrieval = data.data?.type === 'retrieval';

  const options = {
    body: data.body,
    icon: data.icon || '/icon-192.png',
    badge: data.badge || '/icon-192.png',
    data: data.data || {},
    tag: isRetrieval ? ('retrieval-' + (data.data?.ticket_id || 'new')) : 'valetguys-notification',
    renotify: true,
    requireInteraction: true,
    silent: false,
    actions: isRetrieval ? [
      { action: 'claim', title: 'Claim' },
      { action: 'dismiss', title: 'Dismiss' }
    ] : []
  };

  // Persistent vibration pattern for retrieval requests
  if (isRetrieval) {
    // Long vibration pattern: ring-pause-ring-pause (repeating feel)
    options.vibrate = [
      500, 200, 500, 200, 500, 800,
      500, 200, 500, 200, 500, 800,
      500, 200, 500, 200, 500, 800,
      500, 200, 500, 200, 500, 800,
      500, 200, 500, 200, 500
    ];
  }

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const ticketId = event.notification.data?.ticket_id;
  const action = event.action;

  // Dismiss action — just close
  if (action === 'dismiss') {
    return;
  }

  // Claim or tap — open the app
  let url = '/';
  if (ticketId) {
    url = action === 'claim' ? '/ticket/' + ticketId + '?claim=1' : '/ticket/' + ticketId;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      // Try to focus an existing window
      for (let client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      // Open new window
      return clients.openWindow(url);
    })
  );
});

self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', function(event) {
  event.respondWith(fetch(event.request));
});
