import { useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { API } from '../App';
import { toast } from 'sonner';

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// Audio alert for new retrieval tickets
function playAlertSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    osc.type = 'sine';
    gain.gain.value = 0.3;
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
    osc.stop(ctx.currentTime + 0.5);
    // Second beep
    setTimeout(() => {
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.frequency.value = 1100;
      osc2.type = 'sine';
      gain2.gain.value = 0.3;
      osc2.start();
      gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
      osc2.stop(ctx.currentTime + 0.5);
    }, 200);
  } catch (e) {
    // Audio API not available on this device
  }
}

// Send browser notification (no service worker needed)
function showBrowserNotification(title, body, ticketId) {
  if (!('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;

  try {
    const notif = new Notification(title, {
      body,
      icon: '/favicon.ico',
      tag: ticketId || 'valetguys',
      renotify: true,
      requireInteraction: true
    });
    notif.onclick = () => {
      window.focus();
      if (ticketId) {
        window.location.href = `/ticket/${ticketId}`;
      }
      notif.close();
    };
  } catch (e) {
    // Fallback: some browsers don't support Notification constructor directly
  }
}

export function usePushNotifications() {
  const subscribedRef = useRef(false);
  const knownTicketIdsRef = useRef(new Set());
  const initialLoadDoneRef = useRef(false);

  // Request notification permission on first use
  const requestPermission = useCallback(async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission();
    }
  }, []);

  // Subscribe to Web Push (best-effort, not critical)
  const subscribePush = useCallback(async () => {
    if (subscribedRef.current) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;

      const vapidKey = process.env.REACT_APP_VAPID_PUBLIC_KEY;
      if (!vapidKey) return;

      // Check existing subscription first
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidKey)
        });
      }

      await axios.post(`${API}/push/subscribe`, {
        subscription: subscription.toJSON()
      });

      subscribedRef.current = true;
    } catch (err) {
      // Non-critical: Web Push is optional, polling handles notifications
      if (err.message) {
        // Logging skipped in production
      }
    }
  }, []);

  // Poll-based notification: detect new retrieval tickets
  const checkForNewTickets = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/tickets`);
      // Watch for any active retrieval tickets (open or just claimed)
      const activeTickets = res.data.filter(t => ['open', 'claimed', 'en_route'].includes(t.status));

      if (!initialLoadDoneRef.current) {
        // First load: just record existing ticket IDs, don't notify
        res.data.forEach(t => knownTicketIdsRef.current.add(t.id));
        initialLoadDoneRef.current = true;
        return;
      }

      // Check for new tickets we haven't seen
      for (const ticket of activeTickets) {
        if (!knownTicketIdsRef.current.has(ticket.id)) {
          knownTicketIdsRef.current.add(ticket.id);
          const plate = ticket.vehicle?.license_plate || 'Unknown';
          const tag = ticket.vehicle?.tag_number;
          const tagStr = tag ? ` (Tag #${tag})` : '';

          // In-app toast
          toast.info(`New Retrieval: ${plate}${tagStr}`, {
            description: 'A vehicle retrieval has been initiated',
            duration: 10000,
            action: {
              label: 'View',
              onClick: () => { window.location.href = `/ticket/${ticket.id}`; }
            }
          });

          // Audio beep
          playAlertSound();

          // Browser notification
          showBrowserNotification(
            'New Retrieval Request',
            `Car ${plate}${tagStr} — retrieval in progress!`,
            ticket.id
          );
        }
      }
    } catch (err) {
      // Non-critical: poll will retry on next interval
    }
  }, []);

  const subscribe = useCallback(async () => {
    await requestPermission();
    subscribePush();
  }, [requestPermission, subscribePush]);

  // Start polling for new tickets
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Initial check
    checkForNewTickets();

    // Poll every 5 seconds for new tickets
    const interval = setInterval(checkForNewTickets, 5000);
    return () => clearInterval(interval);
  }, [checkForNewTickets]);

  return { subscribe };
}
