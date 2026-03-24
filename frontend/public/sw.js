/* Service Worker for SwiftValet Push Notifications */

self.addEventListener('push', function(event) {
  let data = { title: 'SwiftValet', body: 'New notification', data: {} };
  
  try {
    if (event.data) {
      data = event.data.json();
    }
  } catch (e) {
    console.error('Failed to parse push data:', e);
  }

  const options = {
    body: data.body,
    icon: data.icon || '/favicon.ico',
    badge: data.badge || '/favicon.ico',
    vibrate: [200, 100, 200],
    data: data.data || {},
    actions: data.data?.type === 'retrieval' ? [
      { action: 'open', title: 'View Ticket' }
    ] : [],
    tag: data.data?.ticket_id || 'swiftvalet-notification',
    renotify: true
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const ticketId = event.notification.data?.ticket_id;
  let url = '/';
  
  if (ticketId) {
    url = `/ticket/${ticketId}`;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (let client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
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
