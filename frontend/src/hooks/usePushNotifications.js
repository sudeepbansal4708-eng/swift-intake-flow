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

// Continuous ringer that loops until stopped
class CallRinger {
  constructor() {
    this.ctx = null;
    this.intervalId = null;
    this.isRinging = false;
  }

  start() {
    if (this.isRinging) return;
    this.isRinging = true;

    try {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
      return;
    }

    this._ring();
    // Ring pattern: ring for 1s, pause 1s, repeat
    this.intervalId = setInterval(() => {
      if (this.isRinging) this._ring();
    }, 2000);
  }

  _ring() {
    if (!this.ctx || !this.isRinging) return;
    const now = this.ctx.currentTime;

    // Two-tone ring pattern (like a phone)
    [0, 0.15, 0.3, 0.45, 0.6, 0.75].forEach((delay, i) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.frequency.value = i % 2 === 0 ? 900 : 1100;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.35, now + delay);
      gain.gain.exponentialRampToValueAtTime(0.001, now + delay + 0.12);
      osc.start(now + delay);
      osc.stop(now + delay + 0.12);
    });
  }

  stop() {
    this.isRinging = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (this.ctx) {
      this.ctx.close().catch(() => {});
      this.ctx = null;
    }
  }
}

// Singleton ringer instance
const ringer = new CallRinger();

function showBrowserNotification(title, body, ticketId) {
  if (!('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;

  try {
    const notif = new Notification(title, {
      body,
      icon: '/icon-192.png',
      tag: ticketId || 'valetguys',
      renotify: true,
      requireInteraction: true
    });
    notif.onclick = () => {
      window.focus();
      ringer.stop();
      if (ticketId) {
        window.location.href = `/ticket/${ticketId}`;
      }
      notif.close();
    };
  } catch (e) {
    console.warn('Browser notification failed:', e.message);
  }
}

export function usePushNotifications() {
  const subscribedRef = useRef(false);
  const knownTicketIdsRef = useRef(new Set());
  const initialLoadDoneRef = useRef(false);
  const ringingForTicketRef = useRef(null);

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

      let vapidKey = process.env.REACT_APP_VAPID_PUBLIC_KEY;
      if (!vapidKey) {
        try {
          const res = await axios.get(`${API}/push/vapid-key`);
          vapidKey = res.data.public_key;
        } catch (e) {
          console.warn('Could not get VAPID key');
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
      console.warn('Push subscription failed:', err.message);
    }
  }, []);

  const stopRinger = useCallback(() => {
    ringer.stop();
    ringingForTicketRef.current = null;
  }, []);

  const checkForNewTickets = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/tickets`);
      const activeTickets = res.data.filter(t => ['open', 'claimed', 'en_route', 'arrived'].includes(t.status));

      if (!initialLoadDoneRef.current) {
        res.data.forEach(t => knownTicketIdsRef.current.add(t.id));
        initialLoadDoneRef.current = true;
        return;
      }

      // Check if current user has an active claimed ticket
      const user = JSON.parse(localStorage.getItem('user'));
      const userId = user?.id;
      const userHasActiveTicket = activeTickets.some(
        t => t.claimed_by === userId && ['claimed', 'en_route', 'arrived'].includes(t.status)
      );

      // If the ticket we were ringing for is no longer open, stop ringing
      if (ringingForTicketRef.current) {
        const ringedTicket = activeTickets.find(t => t.id === ringingForTicketRef.current);
        if (!ringedTicket || ringedTicket.status !== 'open') {
          stopRinger();
        }
      }

      for (const ticket of activeTickets) {
        if (!knownTicketIdsRef.current.has(ticket.id)) {
          knownTicketIdsRef.current.add(ticket.id);
          const plate = ticket.vehicle?.license_plate || 'Unknown';
          const tag = ticket.vehicle?.tag_number;
          const tagStr = tag ? ` (Tag #${tag})` : '';

          if (ticket.status === 'open') {
            // Don't ring if user already has an active ticket
            if (userHasActiveTicket) continue;

            // Start continuous ringer
            ringer.start();
            ringingForTicketRef.current = ticket.id;

            toast.info(`New Retrieval: ${plate}${tagStr}`, {
              description: 'Tap Claim to pick up this car',
              duration: Infinity,
              action: {
                label: 'Claim',
                onClick: async () => {
                  stopRinger();
                  try {
                    await axios.put(`${API}/tickets/${ticket.id}/claim`);
                    window.location.href = `/ticket/${ticket.id}`;
                  } catch (err) {
                    toast.error(err.response?.data?.detail || 'Failed to claim');
                  }
                }
              },
              onDismiss: () => {
                stopRinger();
              }
            });

            showBrowserNotification(
              'New Retrieval — Tap to Claim',
              `Car ${plate}${tagStr} — claim this ticket!`,
              ticket.id
            );
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
        }
      }
    } catch (err) {
      console.warn('Ticket poll failed:', err.message);
    }
  }, [stopRinger]);

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
    return () => {
      clearInterval(interval);
      ringer.stop();
    };
  }, [checkForNewTickets]);

  return { subscribe, requestPermission, stopRinger };
}
