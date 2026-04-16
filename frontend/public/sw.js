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

  const options = {
    body: data.body,
    icon: data.icon || '/favicon.ico',
    badge: data.badge || '/favicon.ico',
    vibrate: [200, 100, 200, 100, 200],
    data: data.data || {},
    actions: data.data?.type === 'retrieval' ? [
      { action: 'claim', title: 'Claim Ticket' },
      { action: 'open', title: 'View' }
    ] : [],
    tag: data.data?.ticket_id || 'valetguys-notification',
    renotify: true,
    requireInteraction: true
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const ticketId = event.notification.data?.ticket_id;
  let url = '/';

  if (event.action === 'claim' && ticketId) {
    // Claim the ticket via API, then navigate to it
    url = `/ticket/${ticketId}`;
    event.waitUntil(
      fetch(`/api/tickets/${ticketId}/claim`, {
        method: 'PUT',
        headers: { 'Authorization': 'Bearer ' + event.notification.data?.token }
      }).catch(() => {}).then(() => {
        return clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
          for (let client of clientList) {
            if (client.url.includes(self.location.origin) && 'focus' in client) {
              client.navigate(url);
              return client.focus();
            }
          }
          return clients.openWindow(url);
        });
      })
    );
    return;
  }

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

self.addEventListener('fetch', function(event) {
  // Network-first strategy — let the app work normally
  event.respondWith(fetch(event.request));
});
