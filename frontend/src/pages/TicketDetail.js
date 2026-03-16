import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { ArrowLeft, Car, MapPin, Phone, Clock, CheckCircle, Navigation } from 'lucide-react';
import { toast } from 'sonner';

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
  const navigate = useNavigate();

  useEffect(() => {
    fetchTicket();
    const interval = setInterval(fetchTicket, 3000);
    return () => clearInterval(interval);
  }, [ticketId]);

  useEffect(() => {
    if (ticket?.status === 'arrived' && ticket.arrived_at) {
      const arrivedTime = new Date(ticket.arrived_at);
      const updateTimer = setInterval(() => {
        const now = new Date();
        const elapsed = Math.floor((now - arrivedTime) / 1000);
        const remaining = Math.max(300 - elapsed, 0);
        setTimer(remaining);

        if (remaining === 0) {
          clearInterval(updateTimer);
        }
      }, 1000);

      return () => clearInterval(updateTimer);
    }
  }, [ticket]);

  const fetchTicket = async () => {
    try {
      const response = await axios.get(`${API}/tickets`);
      const foundTicket = response.data.find(t => t.id === ticketId);
      setTicket(foundTicket);
    } catch (error) {
      console.error('Failed to fetch ticket:', error);
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
      // Update vehicle location
      await axios.put(`${API}/vehicles/${ticket.vehicle_id}/location`, {
        zone_label: returnLocation.zone_label,
        gps_latitude: returnLocation.gps_latitude || 0,
        gps_longitude: returnLocation.gps_longitude || 0
      });

      // Update ticket status
      await axios.put(`${API}/tickets/${ticketId}/status?status=returned`);
      
      toast.success('Vehicle returned to new location!');
      setTimeout(() => navigate('/'), 1500);
    } catch (error) {
      toast.error('Failed to update location');
    }
  };

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading || !ticket) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-zinc-400">Loading...</div>
      </div>
    );
  }

  const statusSteps = [
    { key: 'claimed', label: 'Claimed' },
    { key: 'arrived', label: 'Arrived' },
    { key: 'completed', label: 'Completed' }
  ];

  const currentStepIndex = statusSteps.findIndex(s => s.key === ticket.status);

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
              {ticket.vehicle?.zone_label && (
                <div className="flex items-center gap-2 text-zinc-400">
                  <MapPin className="w-4 h-4" />
                  <span>{ticket.vehicle.zone_label}</span>
                </div>
              )}
              {ticket.vehicle?.tag_number && (
                <div className="flex items-center gap-2 p-3 bg-amber-950/20 border border-amber-900/50 rounded-lg">
                  <span className="text-2xl">🏷️</span>
                  <div>
                    <div className="text-amber-400 font-bold text-lg">{ticket.vehicle.tag_number}</div>
                    <div className="text-xs text-amber-400/70">Key Tag Number</div>
                  </div>
                </div>
              )}
            </div>

            {ticket.vehicle?.photo_url && (
              <div className="rounded-lg overflow-hidden border border-zinc-800">
                <img src={ticket.vehicle.photo_url} alt="Vehicle" className="w-full h-48 object-cover" />
              </div>
            )}
          </div>
        </Card>

        {ticket.status === 'arrived' && timer !== null && (
          <Card className="bg-amber-950/20 backdrop-blur-md border border-amber-900/50 p-6 text-center">
            <Clock className="w-12 h-12 text-amber-400 mx-auto mb-3" />
            <div className="text-4xl font-bold text-amber-400 mb-2" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
              {formatTimer(timer)}
            </div>
            <div className="text-sm text-amber-400/70 uppercase tracking-wide">Time Remaining</div>
            {timer === 0 && (
              <p className="text-xs text-amber-400 mt-2">⚠️ Time's up! Consider extended hold or return to park.</p>
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
              🚗 I'VE ARRIVED WITH CAR
            </Button>
          )}

          {ticket.status === 'arrived' && !showReturnForm && (
            <>
              <Button
                data-testid="handover-button"
                onClick={() => updateStatus('completed')}
                className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] border border-emerald-500/50"
              >
                ✅ HANDOVER COMPLETE
              </Button>
              <Button
                data-testid="return-button"
                onClick={() => setShowReturnForm(true)}
                variant="outline"
                className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-transparent border border-amber-700 text-amber-300 hover:bg-amber-950/20 hover:text-amber-200"
              >
                🔄 RETURN TO DIFFERENT SPOT
              </Button>
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
                    {gettingLocation ? 'Getting...' : returnLocation.gps_latitude ? '✅ Captured' : 'Capture GPS'}
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
                  <p className="text-xs text-emerald-400 mt-2">
                    📍 {returnLocation.gps_latitude.toFixed(6)}, {returnLocation.gps_longitude.toFixed(6)}
                  </p>
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
                🔄 PARK AT NEW LOCATION
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
