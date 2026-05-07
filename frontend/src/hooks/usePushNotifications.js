import { useEffect, useRef, useCallback, useState } from 'react';
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

    if (!this.audio) {
      this.audio = this._createRingtoneAudio();
    }

    this.audio.loop = true;
    this.audio.volume = 1.0;

    const playPromise = this.audio.play();
    if (playPromise) {
      playPromise.catch(() => {
        console.warn('Ringer autoplay blocked');
      });
    }

    // Vibration pattern (if supported)
    if ('vibrate' in navigator) {
      this._vibrateLoop();
    }
  }

  _vibrateLoop() {
    if (!this.isRinging) return;
    // Vibrate: 500ms on, 300ms off, 500ms on, 1700ms off (3s cycle)
    navigator.vibrate([500, 300, 500, 1700]);
    this._vibrateTimer = setTimeout(() => this._vibrateLoop(), 3000);
  }

  _createRingtoneAudio() {
    const sampleRate = 8000;
    const duration = 3;
    const numSamples = sampleRate * duration;
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);

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

    for (let i = 0; i < numSamples; i++) {
      const t = i / sampleRate;
      let sample = 0;

      // Ring pattern: 0.8s ring, 0.4s silence, 0.8s ring, 1s silence
      if ((t >= 0 && t < 0.8) || (t >= 1.2 && t < 2.0)) {
        const freq1 = 900;
        const freq2 = 1100;
        sample = Math.sin(2 * Math.PI * freq1 * t) * 0.3 +
                 Math.sin(2 * Math.PI * freq2 * t) * 0.3;
      }

      view.setInt16(44 + i * 2, sample * 32767, true);
    }

    const blob = new Blob([buffer], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    return new Audio(url);
  }

  stop() {
    this.isRinging = false;
    if (this.audio) {
      this.audio.pause();
      this.audio.currentTime = 0;
    }
    if (this._vibrateTimer) {
      clearTimeout(this._vibrateTimer);
      this._vibrateTimer = null;
    }
    if ('vibrate' in navigator) {
      navigator.vibrate(0);
    }
  }
}

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
  const onNewTicketRef = useRef(onNewTicket);
  onNewTicketRef.current = onNewTicket;

  // State for the incoming call overlay
  const [incomingTicket, setIncomingTicket] = useState(null);

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
    setIncomingTicket(null);
  }, []);

  const handleAnswer = useCallback(async () => {
    if (!incomingTicket) return;
    const ticketId = incomingTicket.id;
    stopRinger();
    try {
      await axios.put(`${API}/tickets/${ticketId}/claim`);
      window.location.href = `/ticket/${ticketId}`;
    } catch (err) {
      if (err.response?.status === 409) {
        toast.warning('Another valet already claimed this ticket');
      } else {
        toast.error(err.response?.data?.detail || 'Failed to claim');
      }
      if (onNewTicketRef.current) onNewTicketRef.current();
    }
  }, [incomingTicket, stopRinger]);

  const handleDecline = useCallback(() => {
    stopRinger();
  }, [stopRinger]);

  const checkForNewTickets = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/tickets`);
      const activeTickets = res.data.filter(t => ['open', 'claimed', 'en_route', 'arrived'].includes(t.status));

      if (!initialLoadDoneRef.current) {
        res.data.forEach(t => knownTicketIdsRef.current.add(t.id));
        initialLoadDoneRef.current = true;
        return;
      }

      const user = JSON.parse(localStorage.getItem('user'));
      const userId = user?.id;
      const userHasActiveTicket = activeTickets.some(
        t => t.claimed_by === userId && ['claimed', 'en_route', 'arrived'].includes(t.status)
      );

      // If the ticket we're showing the call for is no longer open (claimed by someone else), dismiss
      setIncomingTicket(prev => {
        if (prev) {
          const stillOpen = activeTickets.find(t => t.id === prev.id && t.status === 'open');
          if (!stillOpen) {
            ringer.stop();
            return null;
          }
        }
        return prev;
      });

      for (const ticket of activeTickets) {
        if (!knownTicketIdsRef.current.has(ticket.id)) {
          knownTicketIdsRef.current.add(ticket.id);

          if (onNewTicketRef.current) onNewTicketRef.current();

          if (ticket.status === 'open') {
            if (userHasActiveTicket) continue;

            // Show full-screen call UI + start ringer
            ringer.start();
            setIncomingTicket(ticket);

            showBrowserNotification(
              'Retrieval Request',
              `Car ${ticket.vehicle?.license_plate || 'Unknown'} — open the app to claim!`,
              ticket.id
            );
          }
        }
      }
    } catch (err) {
      console.warn('Ticket poll failed:', err.message);
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
    return () => {
      clearInterval(interval);
      ringer.stop();
    };
  }, [checkForNewTickets]);

  return { subscribe, requestPermission, stopRinger, incomingTicket, handleAnswer, handleDecline };
}
