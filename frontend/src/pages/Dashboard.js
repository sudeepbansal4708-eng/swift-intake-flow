import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Car, LogOut, Clock, MapPin, Phone, Award, Crown, Users, DollarSign, X, IdCard, ArrowDownToLine, Search, ParkingCircle, CheckCircle, WifiOff, Wifi, Bell, Download } from 'lucide-react';
import { toast } from 'sonner';
import { usePushNotifications } from '../hooks/usePushNotifications';
import { useInstallPrompt } from '../hooks/useInstallPrompt';
import SuperAdminPanel from './SuperAdminPanel';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dashStats, setDashStats] = useState(null);
  const [valetStats, setValetStats] = useState(null);
  const [activeModal, setActiveModal] = useState(null);
  const [showRetrieveModal, setShowRetrieveModal] = useState(false);
  const [retrievePhone, setRetrievePhone] = useState('+91');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [retrieveLoading, setRetrieveLoading] = useState(false);
  const [checkoutConfirm, setCheckoutConfirm] = useState(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [requestOnlineLoading, setRequestOnlineLoading] = useState(false);
  const [showNotifBanner, setShowNotifBanner] = useState(false);
  const navigate = useNavigate();
  const { subscribe } = usePushNotifications();
  const { isInstallable, promptInstall, dismiss: dismissInstall } = useInstallPrompt();

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    setUser(userData);
    fetchTickets(true);
    if (userData?.role === 'admin') fetchDashStats();
    if (userData?.role === 'valet') fetchValetStats();
    refreshUserStatus();

    // Subscribe to push notifications
    subscribe();

    // Check if notification permission needs prompting
    if ('Notification' in window && Notification.permission === 'default') {
      setShowNotifBanner(true);
    }

    const interval = setInterval(() => {
      fetchTickets();
      if (userData?.role === 'admin') fetchDashStats();
      if (userData?.role === 'valet') fetchValetStats();
      refreshUserStatus();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchTickets = async (showError = false) => {
    try {
      const response = await axios.get(`${API}/tickets`);
      setTickets(response.data);
    } catch (error) {
      if (showError) toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const fetchDashStats = async () => {
    try {
      const res = await axios.get(`${API}/admin/dashboard-stats`);
      setDashStats(res.data);
    } catch (err) {
      console.warn('Dashboard stats fetch failed:', err.message);
    }
  };

  const fetchValetStats = async () => {
    try {
      const res = await axios.get(`${API}/valet/dashboard-stats`);
      setValetStats(res.data);
    } catch (err) {
      console.warn('Valet stats fetch failed:', err.message);
    }
  };

  const refreshUserStatus = async () => {
    try {
      const res = await axios.get(`${API}/auth/me`);
      setUser(prev => prev ? { ...prev, is_online: res.data.is_online } : prev);
      // Update localStorage
      const stored = JSON.parse(localStorage.getItem('user'));
      if (stored) {
        stored.is_online = res.data.is_online;
        localStorage.setItem('user', JSON.stringify(stored));
      }
    } catch (err) {
      console.warn('User status refresh failed:', err.message);
    }
  };

  const requestOnline = async () => {
    setRequestOnlineLoading(true);
    try {
      const res = await axios.post(`${API}/valet/request-online`);
      toast.success(res.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send request');
    } finally {
      setRequestOnlineLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    delete axios.defaults.headers.common['Authorization'];
    navigate('/login');
  };

  const claimTicket = async (ticketId) => {
    try {
      await axios.put(`${API}/tickets/${ticketId}/claim`);
      toast.success('Ticket claimed!');
      navigate(`/ticket/${ticketId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim ticket');
    }
  };

  const handleLookup = async () => {
    if (!retrievePhone.trim()) return;
    setLookupLoading(true);
    setLookupResult(null);
    try {
      const res = await axios.get(`${API}/vehicles/lookup`, { params: { phone: retrievePhone.trim() } });
      setLookupResult(res.data);
    } catch (error) {
      const msg = error.response?.data?.detail || 'Vehicle not found';
      toast.error(msg);
      setLookupResult(null);
    } finally {
      setLookupLoading(false);
    }
  };

  const handleRetrieve = async () => {
    setRetrieveLoading(true);
    try {
      const res = await axios.post(`${API}/tickets/retrieve`, { phone_number: retrievePhone.trim() });
      if (res.data.pending_payment) {
        toast.info(`Payment of Rs.${res.data.ticket.valet_fee} requested from customer`);
        setShowRetrieveModal(false);
        setRetrievePhone('+91');
        setLookupResult(null);
        fetchTickets();
      } else {
        toast.success('Retrieval ticket created!');
        setShowRetrieveModal(false);
        setRetrievePhone('+91');
        setLookupResult(null);
        fetchTickets();
        navigate(`/ticket/${res.data.ticket.id}`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create retrieval ticket');
    } finally {
      setRetrieveLoading(false);
    }
  };

  const openRetrieveModal = () => {
    setShowRetrieveModal(true);
    setRetrievePhone('');
    setLookupResult(null);
  };

  const handleCheckout = async (vehicleId) => {
    setCheckoutLoading(true);
    try {
      await axios.post(`${API}/admin/vehicles/${vehicleId}/checkout`);
      toast.success('Vehicle checked out successfully');
      setCheckoutConfirm(null);
      if (isAdmin) fetchDashStats();
      fetchTickets();
      if (user?.role === 'valet') fetchValetStats();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to checkout vehicle');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const openTickets = tickets.filter(t => t.status === 'open');
  const myTickets = tickets.filter(t => t.claimed_by === user?.id && !['completed', 'returned'].includes(t.status));

  const getStatusColor = (status) => {
    const colors = {
      open: 'bg-blue-950/30 text-blue-400 border-blue-900/50',
      claimed: 'bg-amber-950/30 text-amber-400 border-amber-900/50',
      en_route: 'bg-purple-950/30 text-purple-400 border-purple-900/50',
      arrived: 'bg-emerald-950/30 text-emerald-400 border-emerald-900/50',
      completed: 'bg-zinc-800 text-zinc-400 border-zinc-700'
    };
    return colors[status] || 'bg-zinc-800 text-zinc-400 border-zinc-700';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-zinc-400">Loading...</div>
      </div>
    );
  }

  // Super admin gets their own dedicated home screen
  if (user?.role === 'super_admin') {
    return <SuperAdminPanel />;
  }

  const isAdmin = user?.role === 'admin';

  return (
    <div className="mobile-container">
      <div className="gradient-glow-overlay" />
      <div className="content-wrapper p-4 space-y-6 pb-24">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
              Dashboard
            </h1>
            <p className="text-sm text-zinc-400">Welcome, {user?.name}</p>
          </div>
          <div className="flex gap-2">
            {isAdmin && (
              <Button
                data-testid="admin-panel-button"
                onClick={() => navigate('/admin')}
                variant="ghost"
                size="icon"
                className="h-10 w-10 text-zinc-400 hover:text-white hover:bg-zinc-800"
              >
                <Award className="w-5 h-5" />
              </Button>
            )}
            <Button
              data-testid="logout-button"
              onClick={handleLogout}
              variant="ghost"
              size="icon"
              className="h-10 w-10 text-zinc-400 hover:text-white hover:bg-zinc-800"
            >
              <LogOut className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Push Notification Permission Banner */}
        {showNotifBanner && (
          <Card data-testid="notification-banner" className="bg-blue-950/30 border border-blue-800/50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-blue-400" />
                <div>
                  <div className="text-sm font-semibold text-blue-300">Enable Notifications</div>
                  <div className="text-xs text-blue-400/70">Get alerted instantly when a car retrieval is requested</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  data-testid="enable-notifications-btn"
                  onClick={async () => {
                    await subscribe();
                    setShowNotifBanner(false);
                    if (Notification.permission === 'granted') {
                      toast.success('Notifications enabled!');
                    }
                  }}
                  className="h-8 px-3 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold"
                >
                  Enable
                </Button>
                <Button
                  data-testid="dismiss-notifications-btn"
                  onClick={() => setShowNotifBanner(false)}
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-blue-400/50 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Install App Banner */}
        {isInstallable && (
          <Card data-testid="install-app-banner" className="bg-emerald-950/30 border border-emerald-800/50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Download className="w-5 h-5 text-emerald-400" />
                <div>
                  <div className="text-sm font-semibold text-emerald-300">Install Valet Guys</div>
                  <div className="text-xs text-emerald-400/70">Add to your home screen for quick access</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  data-testid="install-app-btn"
                  onClick={async () => {
                    const installed = await promptInstall();
                    if (installed) {
                      toast.success('App installed!');
                    }
                  }}
                  className="h-8 px-3 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
                >
                  Install
                </Button>
                <Button
                  data-testid="dismiss-install-btn"
                  onClick={dismissInstall}
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-emerald-400/50 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Admin Stat Cards */}
        {isAdmin && dashStats && (
          <div className="grid grid-cols-3 gap-3">
            <Card
              data-testid="card-active-valets"
              onClick={() => setActiveModal('valets')}
              className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 cursor-pointer hover:border-blue-800/50 transition-colors active:scale-95"
            >
              <Users className="w-6 h-6 text-blue-500 mb-2" />
              <div className="text-2xl font-bold text-white">{dashStats.totals.valets}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Active Valets</div>
            </Card>
            <Card
              data-testid="card-vehicles"
              onClick={() => setActiveModal('vehicles')}
              className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 cursor-pointer hover:border-emerald-800/50 transition-colors active:scale-95"
            >
              <Car className="w-6 h-6 text-emerald-500 mb-2" />
              <div className="text-2xl font-bold text-white">{dashStats.totals.vehicles}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Vehicles</div>
            </Card>
            <Card
              data-testid="card-tips"
              className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 relative opacity-60"
            >
              <DollarSign className="w-6 h-6 text-amber-500 mb-2" />
              <div className="text-2xl font-bold text-white">--</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Tips Today</div>
              <span className="absolute top-2 right-2 text-[9px] px-1.5 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800/50 font-semibold">COMING SOON</span>
            </Card>
          </div>
        )}

        {/* Valet offline banner */}
        {!isAdmin && user?.role === 'valet' && !user?.is_online && (
          <Card data-testid="valet-offline-banner" className="bg-red-950/20 border border-red-800/50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <WifiOff className="w-5 h-5 text-red-400" />
                <div>
                  <div className="text-sm font-semibold text-red-300">You are offline</div>
                  <div className="text-xs text-red-400/70">Ask your manager to mark you online to start your shift</div>
                </div>
              </div>
              <Button
                data-testid="request-online-button"
                onClick={requestOnline}
                disabled={requestOnlineLoading}
                className="h-9 px-4 bg-red-600 hover:bg-red-500 text-white text-xs font-semibold"
              >
                {requestOnlineLoading ? '...' : 'Request Online'}
              </Button>
            </div>
          </Card>
        )}

        {!isAdmin && user?.role === 'valet' && user?.is_online && (
          <div data-testid="valet-online-badge" className="flex items-center gap-2 text-emerald-400 text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-medium">Online</span>
          </div>
        )}

        {/* Valet stat cards */}
        {!isAdmin && valetStats && (
          <div className="grid grid-cols-3 gap-3">
            <Card
              data-testid="valet-card-parked"
              className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4"
            >
              <Car className="w-6 h-6 text-blue-500 mb-2" />
              <div className="text-2xl font-bold text-white">{valetStats.cars_parked_today}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Cars Parked</div>
            </Card>
            <Card
              data-testid="valet-card-retrieved"
              className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4"
            >
              <ArrowDownToLine className="w-6 h-6 text-emerald-500 mb-2" />
              <div className="text-2xl font-bold text-white">{valetStats.cars_retrieved_today}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Cars Retrieved</div>
            </Card>
            <Card
              data-testid="valet-card-tips"
              className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 relative opacity-60"
            >
              <DollarSign className="w-6 h-6 text-amber-500 mb-2" />
              <div className="text-2xl font-bold text-white">--</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Tips Today</div>
              <span className="absolute top-2 right-2 text-[9px] px-1.5 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800/50 font-semibold">COMING SOON</span>
            </Card>
          </div>
        )}

        {!isAdmin && !valetStats && (
          <div className="grid grid-cols-2 gap-3">
            <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4">
              <div className="text-2xl font-bold text-white">{openTickets.length}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Open Requests</div>
            </Card>
            <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4">
              <div className="text-2xl font-bold text-white">{myTickets.length}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">My Active</div>
            </Card>
          </div>
        )}

        {myTickets.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold uppercase tracking-tight mb-3" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
              My Active Tickets
            </h2>
            <div className="space-y-3">
              {myTickets.map((ticket) => (
                <Card
                  key={ticket.id}
                  data-testid={`my-ticket-${ticket.id}`}
                  onClick={() => navigate(`/ticket/${ticket.id}`)}
                  className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 hover:border-zinc-700 transition-colors cursor-pointer active:scale-95"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <Car className="w-4 h-4 text-blue-500" />
                      <span className="font-medium text-white">{ticket.vehicle?.license_plate}</span>
                    </div>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(ticket.status)}`}>
                      {ticket.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <div className="space-y-1 text-sm text-zinc-400">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3 h-3" />
                      <span>{ticket.vehicle?.zone_label || 'Location saved'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-3 h-3" />
                      <span>{ticket.customer_phone}</span>
                    </div>
                    {ticket.vehicle?.tag_number && (
                      <div className="flex items-center gap-2 mt-2 p-2 bg-amber-950/20 border border-amber-900/50 rounded">
                        <span className="text-amber-400 font-medium">TAG: {ticket.vehicle.tag_number}</span>
                      </div>
                    )}
                  </div>
                  {ticket.status === 'arrived' && ticket.vehicle?.id && (
                    checkoutConfirm === ticket.vehicle.id ? (
                      <div className="mt-3 flex gap-2">
                        <Button
                          data-testid={`valet-checkout-confirm-${ticket.vehicle.id}`}
                          onClick={(e) => { e.stopPropagation(); handleCheckout(ticket.vehicle.id); }}
                          disabled={checkoutLoading}
                          className="flex-1 h-9 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                        >
                          {checkoutLoading ? 'Processing...' : 'Confirm Checkout'}
                        </Button>
                        <Button
                          onClick={(e) => { e.stopPropagation(); setCheckoutConfirm(null); }}
                          variant="ghost"
                          className="h-9 text-xs text-zinc-400 hover:text-white"
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        data-testid={`valet-checkout-button-${ticket.vehicle.id}`}
                        onClick={(e) => { e.stopPropagation(); setCheckoutConfirm(ticket.vehicle.id); }}
                        className="mt-3 w-full h-9 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                      >
                        <CheckCircle className="w-3 h-3 mr-1.5" />
                        Checkout &amp; Complete
                      </Button>
                    )
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}

        <div>
          <h2 className="text-lg font-semibold uppercase tracking-tight mb-3" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            Open Requests
          </h2>
          {openTickets.length === 0 ? (
            <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-8 text-center">
              <Clock className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-400">No open requests</p>
            </Card>
          ) : (
            <div className="space-y-3">
              {openTickets.map((ticket) => (
                <Card
                  key={ticket.id}
                  data-testid={`open-ticket-${ticket.id}`}
                  className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Car className="w-4 h-4 text-blue-500" />
                        <span className="font-medium text-white">{ticket.vehicle?.license_plate}</span>
                      </div>
                      <div className="space-y-1 text-sm text-zinc-400">
                        <div className="flex items-center gap-2">
                          <MapPin className="w-3 h-3" />
                          <span>{ticket.vehicle?.zone_label || 'Location saved'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <Button
                    data-testid={`claim-button-${ticket.id}`}
                    onClick={() => claimTicket(ticket.id)}
                    className="w-full h-10 rounded-lg font-medium transition-all active:scale-95 bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
                  >
                    CLAIM TICKET
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Action Ribbon */}
      {(isAdmin || (user?.role === 'valet' && user?.is_online)) && (
        <div className="fixed bottom-0 left-0 right-0 z-[9998] bg-zinc-900/95 backdrop-blur-md border-t border-zinc-800 px-4 py-3 flex gap-3" data-testid="bottom-ribbon">
          <button
            data-testid="ribbon-park-button"
            onClick={() => navigate('/intake')}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-blue-600 text-white font-semibold text-sm uppercase tracking-wider hover:bg-blue-500 active:scale-[0.97] transition-all shadow-[0_0_20px_rgba(59,130,246,0.3)]"
          >
            <ParkingCircle className="w-4 h-4" />
            Park
          </button>
          <button
            data-testid="ribbon-retrieve-button"
            onClick={openRetrieveModal}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-600 text-white font-semibold text-sm uppercase tracking-wider hover:bg-emerald-500 active:scale-[0.97] transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)]"
          >
            <Search className="w-4 h-4" />
            Retrieve
          </button>
        </div>
      )}

      {/* Retrieve Modal */}
      {showRetrieveModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[10000] p-4" onClick={() => setShowRetrieveModal(false)}>
          <Card
            data-testid="retrieve-modal"
            className="bg-zinc-900 border border-zinc-700 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <h3 className="font-bold text-white text-lg uppercase" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Retrieve Vehicle
              </h3>
              <Button
                data-testid="close-retrieve-modal"
                onClick={() => setShowRetrieveModal(false)}
                variant="ghost" size="icon"
                className="h-8 w-8 text-zinc-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="p-4 space-y-4">
              <div>
                <label className="text-sm text-zinc-400 uppercase tracking-wide block mb-2">Customer Phone Number</label>
                <div className="flex gap-2">
                  <Input
                    data-testid="retrieve-phone-input"
                    type="tel"
                    value={retrievePhone}
                    onChange={(e) => { setRetrievePhone(e.target.value); setLookupResult(null); }}
                    placeholder="+91XXXXXXXXXX"
                    className="flex-1 h-11 bg-zinc-950/50 border-zinc-800 text-white placeholder:text-zinc-600 focus:border-blue-500"
                    onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
                  />
                  <Button
                    data-testid="retrieve-lookup-button"
                    onClick={handleLookup}
                    disabled={lookupLoading || !retrievePhone.trim()}
                    className="h-11 px-4 bg-blue-600 hover:bg-blue-500 text-white"
                  >
                    {lookupLoading ? '...' : <Search className="w-4 h-4" />}
                  </Button>
                </div>
              </div>

              {lookupResult && (
                <Card data-testid="retrieve-vehicle-info" className="bg-zinc-800/50 border border-zinc-700 p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/50 flex items-center justify-center">
                      <Car className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <div className="text-lg font-bold text-white">{lookupResult.vehicle.license_plate}</div>
                      {lookupResult.vehicle.tag_number && (
                        <span className="text-xs text-amber-400 bg-amber-950/30 border border-amber-900/50 px-1.5 py-0.5 rounded">
                          Tag #{lookupResult.vehicle.tag_number}
                        </span>
                      )}
                    </div>
                  </div>
                  {lookupResult.vehicle.zone_label && (
                    <div className="flex items-center gap-2 text-sm text-zinc-400">
                      <MapPin className="w-3.5 h-3.5" />
                      <span>{lookupResult.vehicle.zone_label}</span>
                    </div>
                  )}
                  {lookupResult.vehicle.parked_at && (
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                      <Clock className="w-3 h-3" />
                      <span>Parked at {new Date(lookupResult.vehicle.parked_at).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'})}</span>
                    </div>
                  )}

                  {lookupResult.has_active_ticket ? (
                    <div className="p-2 bg-amber-950/20 border border-amber-900/50 rounded text-amber-400 text-sm text-center">
                      A retrieval ticket already exists for this vehicle
                    </div>
                  ) : (
                    <Button
                      data-testid="retrieve-confirm-button"
                      onClick={handleRetrieve}
                      disabled={retrieveLoading}
                      className="w-full h-11 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold active:scale-95 transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] border border-emerald-500/50"
                    >
                      {retrieveLoading ? 'Creating...' : 'START RETRIEVAL'}
                    </Button>
                  )}
                </Card>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Admin Detail Modals */}
      {activeModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setActiveModal(null)}>
          <Card
            data-testid={`modal-${activeModal}`}
            className="bg-zinc-900 border border-zinc-700 w-full max-w-md max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-zinc-800 shrink-0">
              <h3 className="font-bold text-white text-lg uppercase" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                {activeModal === 'valets' && 'Active Valets'}
                {activeModal === 'vehicles' && 'Parked Vehicles'}
                {activeModal === 'tips' && 'Tips Breakdown'}
              </h3>
              <Button data-testid="close-detail-modal" onClick={() => setActiveModal(null)} variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="overflow-y-auto p-4 space-y-2">
              {activeModal === 'valets' && (
                dashStats?.active_valets?.length > 0 ? (
                  dashStats.active_valets.map((v) => (
                    <Card key={v.id} data-testid={`modal-valet-${v.id}`} className="bg-zinc-800/50 border border-zinc-700 p-3">
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-full bg-blue-900/30 border border-blue-800/50 flex items-center justify-center shrink-0">
                          <Users className="w-4 h-4 text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-white text-sm">{v.name}</div>
                          {v.phone_number && <div className="flex items-center gap-1 text-xs text-zinc-400"><Phone className="w-3 h-3" />{v.phone_number}</div>}
                          {v.email && <div className="text-xs text-zinc-500 truncate">{v.email}</div>}
                          {v.driver_license_number && <div className="flex items-center gap-1 text-xs text-emerald-500 mt-1"><IdCard className="w-3 h-3" />{v.driver_license_number}</div>}
                        </div>
                      </div>
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-8 text-zinc-500 text-sm">No active valets</div>
                )
              )}

              {activeModal === 'vehicles' && (
                dashStats?.parked_vehicles?.length > 0 ? (
                  dashStats.parked_vehicles.map((v) => (
                    <Card key={v.id} data-testid={`modal-vehicle-${v.id}`} className="bg-zinc-800/50 border border-zinc-700 p-3">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Car className="w-4 h-4 text-emerald-400" />
                            <span className="font-bold text-white text-sm">{v.license_plate}</span>
                            {v.tag_number && <span className="text-[10px] text-amber-400 bg-amber-950/20 border border-amber-900/50 px-1.5 py-0.5 rounded">#{v.tag_number}</span>}
                          </div>
                          {v.zone_label && <div className="flex items-center gap-1 text-xs text-zinc-400"><MapPin className="w-3 h-3" />{v.zone_label}</div>}
                          <div className="flex items-center gap-1 text-xs text-zinc-500 mt-0.5"><Phone className="w-3 h-3" />{v.phone_number}</div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-[10px] text-zinc-500">{v.parked_by_name}</div>
                          {v.parked_at && <div className="text-[10px] text-zinc-600">{new Date(v.parked_at).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'})}</div>}
                        </div>
                      </div>
                      {checkoutConfirm === v.id ? (
                        <div className="mt-2 flex gap-2">
                          <Button
                            data-testid={`checkout-confirm-${v.id}`}
                            onClick={() => handleCheckout(v.id)}
                            disabled={checkoutLoading}
                            className="flex-1 h-8 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                          >
                            {checkoutLoading ? 'Processing...' : 'Confirm Checkout'}
                          </Button>
                          <Button
                            data-testid={`checkout-cancel-${v.id}`}
                            onClick={() => setCheckoutConfirm(null)}
                            variant="ghost"
                            className="h-8 text-xs text-zinc-400 hover:text-white"
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Button
                          data-testid={`checkout-button-${v.id}`}
                          onClick={() => setCheckoutConfirm(v.id)}
                          variant="outline"
                          className="mt-2 w-full h-8 text-xs border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
                        >
                          <CheckCircle className="w-3 h-3 mr-1.5" />
                          Checkout
                        </Button>
                      )}
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-8 text-zinc-500 text-sm">No vehicles parked today</div>
                )
              )}

              {activeModal === 'tips' && (
                <div className="text-center py-8">
                  <DollarSign className="w-8 h-8 text-amber-600/40 mx-auto mb-2" />
                  <div className="text-sm text-zinc-400 font-medium">Tips & Payments</div>
                  <span className="inline-block mt-2 text-[10px] px-2.5 py-1 rounded-full bg-amber-900/30 text-amber-400 border border-amber-800/50 font-semibold">COMING SOON</span>
                  <div className="text-[10px] text-zinc-600 mt-2">Payment integration will be available after the pilot phase</div>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
