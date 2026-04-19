import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { ArrowLeft, Car, MapPin, Phone, Clock, CheckCircle, Navigation, AlertTriangle, RotateCcw, ExternalLink, TimerReset } from 'lucide-react';
import { toast } from 'sonner';

function playTimerAlert() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    // Urgent triple beep
    [0, 300, 600].forEach((delay) => {
      setTimeout(() => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 1200;
        osc.type = 'square';
        gain.gain.value = 0.4;
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
        osc.stop(ctx.currentTime + 0.3);
      }, delay);
    });
  } catch (e) {
    // Audio not available
  }
}

function showTimerNotification(plate) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    const notif = new Notification('Timer Expired!', {
      body: `Customer no-show for ${plate}. Extend or park back.`,
      icon: '/favicon.ico',
      tag: 'timer-expired',
      renotify: true,
      requireInteraction: true,
    });
    notif.onclick = () => { window.focus(); notif.close(); };
  } catch (e) {
    // Notification not supported
  }
}

export default function TicketDetail() {
  const { ticketId } = useParams();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timer, setTimer] = useState(null);
  const [showReturnForm, setShowReturnForm] = useState(false);
  const [returnLocation, setReturnLocation] = useState({
    zone_label: '',
    gps_latitude: null,
    gps_longitude: null
  });
  const [gettingLocation, setGettingLocation] = useState(false);
  const [extendLoading, setExtendLoading] = useState(false);
  const timerExpiredRef = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTicket();
    const interval = setInterval(fetchTicket, 3000);
    return () => clearInterval(interval);
  }, [ticketId]);

  useEffect(() => {
    if (ticket?.status === 'arrived' && ticket.arrived_at) {
      timerExpiredRef.current = false;
      const arrivedTime = new Date(ticket.arrived_at);
      const waitSeconds = (ticket.wait_timer || 5) * 60;
      const updateTimer = setInterval(() => {
        const now = new Date();
        const elapsed = Math.floor((now - arrivedTime) / 1000);
        const remaining = Math.max(waitSeconds - elapsed, 0);
        setTimer(remaining);

        if (remaining === 0 && !timerExpiredRef.current) {
          timerExpiredRef.current = true;
          clearInterval(updateTimer);
          // Fire notification
          const plate = ticket.vehicle?.license_plate || 'Vehicle';
          playTimerAlert();
          showTimerNotification(plate);
          toast.error(`Timer expired for ${plate}! Customer no-show.`, {
            duration: 15000,
            description: 'Extend the timer or park the car back.',
          });
        }
      }, 1000);

      return () => clearInterval(updateTimer);
    }
  }, [ticket]);

  const fetchTicket = async () => {
    try {
      const response = await axios.get(`${API}/tickets?include_completed=true`);
      const foundTicket = response.data.find(t => t.id === ticketId);
      setTicket(foundTicket);
    } catch (error) {
      console.warn('Ticket fetch failed:', error.message);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (newStatus) => {
    try {
      await axios.put(`${API}/tickets/${ticketId}/status?status=${newStatus}`);
      toast.success('Status updated!');
      fetchTicket();
      
      if (newStatus === 'completed') {
        setTimeout(() => navigate('/'), 2000);
      }
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const captureLocation = () => {
    setGettingLocation(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setReturnLocation({
            ...returnLocation,
            gps_latitude: position.coords.latitude,
            gps_longitude: position.coords.longitude
          });
          toast.success('Location captured!');
          setGettingLocation(false);
        },
        (error) => {
          toast.error('Failed to get location');
          setGettingLocation(false);
        },
        { enableHighAccuracy: true }
      );
    } else {
      toast.error('Geolocation not supported');
      setGettingLocation(false);
    }
  };

  const handleReturnToPark = async () => {
    try {
      await axios.put(`${API}/vehicles/${ticket.vehicle_id}/location`, {
        zone_label: returnLocation.zone_label,
        gps_latitude: returnLocation.gps_latitude || 0,
        gps_longitude: returnLocation.gps_longitude || 0
      });

      await axios.put(`${API}/tickets/${ticketId}/status?status=returned`);
      
      toast.success('Vehicle returned to new location!');
      setTimeout(() => navigate('/'), 1500);
    } catch (error) {
      toast.error('Failed to update location');
    }
  };

  const handleExtendTimer = async () => {
    setExtendLoading(true);
    try {
      await axios.put(`${API}/tickets/${ticketId}/extend`);
      toast.success('Timer extended by 5 minutes');
      timerExpiredRef.current = false;
      fetchTicket();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to extend timer');
    } finally {
      setExtendLoading(false);
    }
  };

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getGoogleMapsUrl = (lat, lng) => {
    return `https://www.google.com/maps?q=${lat},${lng}`;
  };

  if (loading || !ticket) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-zinc-400">Loading...</div>
      </div>
    );
  }

  const statusSteps = ticket.status === 'returned'
    ? [
        { key: 'claimed', label: 'Claimed' },
        { key: 'arrived', label: 'Arrived' },
        { key: 'returned', label: 'Returned to Park' }
      ]
    : [
        { key: 'claimed', label: 'Claimed' },
        { key: 'arrived', label: 'Arrived' },
        { key: 'completed', label: 'Completed' }
      ];

  const currentStepIndex = statusSteps.findIndex(s => s.key === ticket.status);
  const hasGps = ticket.vehicle?.gps_latitude && ticket.vehicle.gps_latitude !== 0;

  return (
    <div className="mobile-container">
      <div className="gradient-glow-overlay" />
      <div className="content-wrapper p-4 space-y-6">
        <div className="flex items-center gap-3">
          <Button
            data-testid="back-button"
            onClick={() => navigate('/')}
            variant="ghost"
            size="icon"
            className="h-10 w-10 text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <h1 className="text-3xl font-bold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            Ticket Details
          </h1>
        </div>

        {/* Vehicle Info Card */}
        <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-blue-600/20 border border-blue-500/50 flex items-center justify-center">
                <Car className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <div className="text-xl font-bold text-white">{ticket.vehicle?.license_plate}</div>
                <div className="text-sm text-zinc-400">License Plate</div>
              </div>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-zinc-400">
                <Phone className="w-4 h-4" />
                <span>{ticket.customer_phone}</span>
              </div>
            </div>

            {ticket.vehicle?.photo_url && (
              <div className="rounded-lg overflow-hidden border border-zinc-800">
                <img src={ticket.vehicle.photo_url} alt="Vehicle" className="w-full h-48 object-cover" />
              </div>
            )}
          </div>
        </Card>

        {/* Retrieval Information Card - shown when claimed */}
        {ticket.status === 'claimed' && (
          <Card className="bg-blue-950/30 backdrop-blur-md border border-blue-900/50 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-full bg-blue-600/20 border border-blue-500/50 flex items-center justify-center">
                <MapPin className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h3 className="font-bold text-white text-lg uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                  Retrieval Information
                </h3>
                <p className="text-xs text-blue-400">Vehicle location & details</p>
              </div>
            </div>
            
            <div className="space-y-3">
              {ticket.vehicle?.zone_label && (
                <div className="flex items-start gap-3 p-3 bg-zinc-900/50 rounded-lg border border-zinc-800">
                  <MapPin className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Parking Location</div>
                    <div className="text-white font-medium">{ticket.vehicle.zone_label}</div>
                  </div>
                </div>
              )}
              
              {ticket.vehicle?.tag_number && (
                <div className="flex items-start gap-3 p-3 bg-amber-950/20 rounded-lg border border-amber-900/50">
                  <span className="text-2xl">🏷️</span>
                  <div className="flex-1">
                    <div className="text-xs text-amber-400/70 uppercase tracking-wider mb-1">Key Tag</div>
                    <div className="text-amber-400 font-bold text-xl">{ticket.vehicle.tag_number}</div>
                  </div>
                </div>
              )}

              {hasGps && (
                <a
                  href={getGoogleMapsUrl(ticket.vehicle.gps_latitude, ticket.vehicle.gps_longitude)}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="google-maps-link"
                  className="flex items-start gap-3 p-3 bg-emerald-950/20 rounded-lg border border-emerald-900/50 hover:bg-emerald-950/40 transition-colors block"
                >
                  <Navigation className="w-5 h-5 text-emerald-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-xs text-emerald-400/70 uppercase tracking-wider mb-1">GPS Location</div>
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-medium">Open in Google Maps</span>
                      <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                  </div>
                </a>
              )}
            </div>

            <div className="mt-4 p-3 bg-blue-950/20 border border-blue-900/30 rounded-lg">
              <p className="text-sm text-blue-300 text-center">
                Use this info to locate the vehicle. Click below when you've arrived with the car.
              </p>
            </div>
          </Card>
        )}

        {ticket.status === 'arrived' && timer !== null && (
          <Card className={`backdrop-blur-md p-6 text-center ${
            timer === 0
              ? 'bg-red-950/30 border border-red-800/50'
              : 'bg-amber-950/20 border border-amber-900/50'
          }`}>
            <Clock className={`w-12 h-12 mx-auto mb-3 ${timer === 0 ? 'text-red-400' : 'text-amber-400'}`} />
            <div className={`text-4xl font-bold mb-2 ${timer === 0 ? 'text-red-400' : 'text-amber-400'}`} style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
              {timer === 0 ? 'TIME UP' : formatTimer(timer)}
            </div>
            <div className={`text-sm uppercase tracking-wide ${timer === 0 ? 'text-red-400/70' : 'text-amber-400/70'}`}>
              {timer === 0 ? 'Customer did not show up' : 'Waiting for customer'}
            </div>
            {timer > 0 && timer <= 60 && (
              <div className="mt-2 flex items-center justify-center gap-1.5 text-amber-400 text-xs">
                <AlertTriangle className="w-3.5 h-3.5" />
                Less than a minute remaining
              </div>
            )}
            {timer === 0 && (
              <div className="mt-4 space-y-3">
                <div className="p-2 bg-red-950/30 border border-red-800/30 rounded text-red-300 text-xs mb-3">
                  <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />
                  Customer no-show. Choose an action below.
                </div>
                <div className="flex gap-3">
                  <Button
                    data-testid="extend-timer-button"
                    onClick={handleExtendTimer}
                    disabled={extendLoading}
                    className="flex-1 h-12 rounded-lg font-medium transition-all active:scale-95 bg-amber-600 hover:bg-amber-500 text-white shadow-[0_0_20px_rgba(245,158,11,0.3)] border border-amber-500/50"
                  >
                    <TimerReset className="w-4 h-4 mr-2" />
                    {extendLoading ? 'Extending...' : 'EXTEND 5 MIN'}
                  </Button>
                  <Button
                    data-testid="park-back-button"
                    onClick={() => setShowReturnForm(true)}
                    className="flex-1 h-12 rounded-lg font-medium transition-all active:scale-95 bg-red-600 hover:bg-red-500 text-white shadow-[0_0_20px_rgba(239,68,68,0.3)] border border-red-500/50"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    PARK BACK
                  </Button>
                </div>
                <Button
                  data-testid="handover-button-late"
                  onClick={() => updateStatus('completed')}
                  variant="outline"
                  className="w-full h-10 rounded-lg font-medium transition-all active:scale-95 bg-transparent border border-zinc-700 text-zinc-400 hover:bg-zinc-900 hover:text-zinc-300 text-sm"
                >
                  Customer showed up — Complete Handover
                </Button>
              </div>
            )}
          </Card>
        )}

        <div>
          <h2 className="text-lg font-semibold uppercase tracking-tight mb-3" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            Status Progress
          </h2>
          <div className="space-y-2">
            {statusSteps.map((step, index) => {
              const isActive = index === currentStepIndex;
              const isCompleted = index < currentStepIndex;
              
              return (
                <div
                  key={step.key}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                    isActive
                      ? 'bg-blue-950/30 border-blue-900/50'
                      : isCompleted
                      ? 'bg-emerald-950/20 border-emerald-900/30'
                      : 'bg-zinc-900/30 border-zinc-800'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${
                      isActive
                        ? 'border-blue-500 bg-blue-600/20'
                        : isCompleted
                        ? 'border-emerald-500 bg-emerald-600/20'
                        : 'border-zinc-700 bg-zinc-800/20'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <span className={`text-sm font-bold ${
                        isActive ? 'text-blue-400' : 'text-zinc-600'
                      }`}>
                        {index + 1}
                      </span>
                    )}
                  </div>
                  <span
                    className={`font-medium ${
                      isActive
                        ? 'text-blue-400'
                        : isCompleted
                        ? 'text-emerald-400'
                        : 'text-zinc-500'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-3">
          {ticket.status === 'claimed' && !showReturnForm && (
            <Button
              data-testid="arrived-button"
              onClick={() => updateStatus('arrived')}
              className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
            >
              I'VE ARRIVED WITH CAR
            </Button>
          )}

          {ticket.status === 'arrived' && !showReturnForm && (
            <>
              {timer !== 0 && (
                <>
                  <Button
                    data-testid="handover-button"
                    onClick={() => updateStatus('completed')}
                    className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] border border-emerald-500/50"
                  >
                    HANDOVER COMPLETE
                  </Button>
                  <Button
                    data-testid="return-button"
                    onClick={() => setShowReturnForm(true)}
                    variant="outline"
                    className="w-full h-10 rounded-lg font-medium transition-all active:scale-95 bg-transparent border border-amber-700 text-amber-300 hover:bg-amber-950/20 hover:text-amber-200 text-sm"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                    Return to different spot
                  </Button>
                </>
              )}
            </>
          )}

          {showReturnForm && (
            <Card className="bg-zinc-900/50 backdrop-blur-md border border-amber-800 p-6 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-amber-400 uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                  Return to New Location
                </h3>
                <Button
                  onClick={() => setShowReturnForm(false)}
                  variant="ghost"
                  size="sm"
                  className="text-zinc-400 hover:text-white"
                >
                  Cancel
                </Button>
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  GPS Location (Optional)
                </Label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    onClick={captureLocation}
                    disabled={gettingLocation}
                    className="flex-1 h-12 rounded-lg font-medium transition-all active:scale-95 bg-zinc-800 hover:bg-zinc-700 text-white border border-zinc-700"
                  >
                    <Navigation className="w-4 h-4 mr-2" />
                    {gettingLocation ? 'Getting...' : returnLocation.gps_latitude ? 'Captured' : 'Capture GPS'}
                  </Button>
                  {!returnLocation.gps_latitude && (
                    <Button
                      type="button"
                      onClick={() => setReturnLocation({ ...returnLocation, gps_latitude: 0, gps_longitude: 0 })}
                      className="h-12 px-4 rounded-lg font-medium transition-all active:scale-95 bg-zinc-900 hover:bg-zinc-800 text-zinc-400 border border-zinc-700"
                    >
                      Skip
                    </Button>
                  )}
                </div>
                {returnLocation.gps_latitude && returnLocation.gps_latitude !== 0 && (
                  <a
                    href={getGoogleMapsUrl(returnLocation.gps_latitude, returnLocation.gps_longitude)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-emerald-400 mt-2 flex items-center gap-1 hover:underline"
                  >
                    <Navigation className="w-3 h-3" />
                    View on Google Maps
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>

              <div>
                <Label htmlFor="return-zone" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  New Landmark / Zone
                </Label>
                <Input
                  id="return-zone"
                  type="text"
                  value={returnLocation.zone_label}
                  onChange={(e) => setReturnLocation({ ...returnLocation, zone_label: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
                  placeholder="Level 1, Section A (Closer spot)"
                  required
                />
              </div>

              <Button
                onClick={handleReturnToPark}
                disabled={!returnLocation.zone_label}
                className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-amber-600 hover:bg-amber-500 text-white shadow-[0_0_20px_rgba(245,158,11,0.3)] border border-amber-500/50"
              >
                PARK AT NEW LOCATION
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
