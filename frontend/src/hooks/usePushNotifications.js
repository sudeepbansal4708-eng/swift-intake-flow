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
    // Audio API not available
  }
}

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
    // Fallback: some browsers don't support Notification constructor
  }
}

export function usePushNotifications() {
  const subscribedRef = useRef(false);
  const knownTicketIdsRef = useRef(new Set());
  const initialLoadDoneRef = useRef(false);

  const requestPermission = useCallback(async () => {
    if (!('Notification' in window)) return false;
    if (Notification.permission === 'granted') return true;
    if (Notification.permission === 'default') {
      const result = await Notification.requestPermission();
      return result === 'granted';
    }
    return false;
  }, []);

  const subscribePush = useCallback(async () => {
    if (subscribedRef.current) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      await navigator.serviceWorker.ready;

      // Get VAPID key from env or fetch from API
      let vapidKey = process.env.REACT_APP_VAPID_PUBLIC_KEY;
      if (!vapidKey) {
        try {
          const res = await axios.get(`${API}/push/vapid-key`);
          vapidKey = res.data.public_key;
        } catch (e) {
          // Could not get VAPID key
        }
      }
      if (!vapidKey) return;

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
    }
  }, []);

  const checkForNewTickets = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/tickets`);
      const activeTickets = res.data.filter(t => ['open', 'claimed', 'en_route'].includes(t.status));

      if (!initialLoadDoneRef.current) {
        res.data.forEach(t => knownTicketIdsRef.current.add(t.id));
        initialLoadDoneRef.current = true;
        return;
      }

      for (const ticket of activeTickets) {
        if (!knownTicketIdsRef.current.has(ticket.id)) {
          knownTicketIdsRef.current.add(ticket.id);
          const plate = ticket.vehicle?.license_plate || 'Unknown';
          const tag = ticket.vehicle?.tag_number;
          const tagStr = tag ? ` (Tag #${tag})` : '';

          if (ticket.status === 'open') {
            // Open ticket — offer Claim action
            toast.info(`New Retrieval: ${plate}${tagStr}`, {
              description: 'Tap Claim to pick up this car',
              duration: 30000,
              action: {
                label: 'Claim',
                onClick: async () => {
                  try {
                    await axios.put(`${API}/tickets/${ticket.id}/claim`);
                    window.location.href = `/ticket/${ticket.id}`;
                  } catch (err) {
                    toast.error(err.response?.data?.detail || 'Failed to claim');
                  }
                }
              }
            });
          } else {
            toast.info(`Retrieval Update: ${plate}${tagStr}`, {
              description: `Status: ${ticket.status.replace('_', ' ')}`,
              duration: 10000,
              action: {
                label: 'View',
                onClick: () => { window.location.href = `/ticket/${ticket.id}`; }
              }
            });
          }

          playAlertSound();

          showBrowserNotification(
            ticket.status === 'open' ? 'New Retrieval — Tap to Claim' : 'Retrieval Update',
            `Car ${plate}${tagStr}${ticket.status === 'open' ? ' — claim this ticket!' : ''}`,
            ticket.id
          );
        }
      }
    } catch (err) {
      // Non-critical: poll will retry
    }
  }, []);

  const subscribe = useCallback(async () => {
    const granted = await requestPermission();
    if (granted) {
      subscribePush();
    }
  }, [requestPermission, subscribePush]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    checkForNewTickets();
    const interval = setInterval(checkForNewTickets, 5000);
    return () => clearInterval(interval);
  }, [checkForNewTickets]);

  return { subscribe, requestPermission };
}
