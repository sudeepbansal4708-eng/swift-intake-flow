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

// Continuous ringer using Audio element for mobile persistence
class CallRinger {
  constructor() {
    this.audio = null;
    this.isRinging = false;
  }

  start() {
    if (this.isRinging) return;
    this.isRinging = true;

    // Generate a ringtone WAV as base64 data URL
    // This approach works reliably on mobile browsers
    if (!this.audio) {
      this.audio = this._createRingtoneAudio();
    }

    this.audio.loop = true;
    this.audio.volume = 1.0;

    const playPromise = this.audio.play();
    if (playPromise) {
      playPromise.catch(() => {
        // Autoplay blocked - try with user interaction fallback
        console.warn('Ringer autoplay blocked - will ring on next interaction');
      });
    }
  }

  _createRingtoneAudio() {
    // Generate a simple ringtone using WAV format
    const sampleRate = 8000;
    const duration = 3; // 3 seconds of ring, then loops
    const numSamples = sampleRate * duration;
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);

    // WAV header
    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + numSamples * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, numSamples * 2, true);

    // Generate ring tone: 0.8s ring, 0.4s silence, 0.8s ring, 1s silence
    for (let i = 0; i < numSamples; i++) {
      const t = i / sampleRate;
      let sample = 0;

      // Ring pattern within 3-second loop
      if ((t >= 0 && t < 0.8) || (t >= 1.2 && t < 2.0)) {
        // Two-tone ring (900Hz + 1100Hz)
        const freq1 = 900;
        const freq2 = 1100;
        sample = Math.sin(2 * Math.PI * freq1 * t) * 0.3 +
                 Math.sin(2 * Math.PI * freq2 * t) * 0.3;
      }

      view.setInt16(44 + i * 2, sample * 32767, true);
    }

    const blob = new Blob([buffer], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    return audio;
  }

  stop() {
    this.isRinging = false;
    if (this.audio) {
      this.audio.pause();
      this.audio.currentTime = 0;
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

export function usePushNotifications(onNewTicket) {
  const subscribedRef = useRef(false);
  const knownTicketIdsRef = useRef(new Set());
  const initialLoadDoneRef = useRef(false);
  const ringingForTicketRef = useRef(null);
  const onNewTicketRef = useRef(onNewTicket);
  onNewTicketRef.current = onNewTicket;

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

          // Notify Dashboard to refetch tickets immediately
          if (onNewTicketRef.current) onNewTicketRef.current();

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
                    const msg = err.response?.data?.detail || 'Failed to claim';
                    if (err.response?.status === 409) {
                      toast.warning('Another valet already claimed this ticket');
                    } else {
                      toast.error(msg);
                    }
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
