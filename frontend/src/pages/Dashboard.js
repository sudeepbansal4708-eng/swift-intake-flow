import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Plus, Car, LogOut, Settings, Clock, MapPin, Phone, Award } from 'lucide-react';
import { toast } from 'sonner';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user'));
    setUser(userData);
    fetchTickets();

    const interval = setInterval(fetchTickets, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API}/tickets`);
      setTickets(response.data);
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
    } finally {
      setLoading(false);
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
      // Navigate directly to ticket detail page
      navigate(`/ticket/${ticketId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to claim ticket');
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

  return (
    <div className="mobile-container">
      <div className="gradient-glow-overlay" />
      <div className="content-wrapper p-4 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
              Dashboard
            </h1>
            <p className="text-sm text-zinc-400">Welcome, {user?.name}</p>
          </div>
          <div className="flex gap-2">
            {user?.role === 'admin' && (
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
                        <span>🏷️</span>
                        <span className="text-amber-400 font-medium">{ticket.vehicle.tag_number}</span>
                      </div>
                    )}
                  </div>
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

      <Button
        data-testid="new-intake-button"
        onClick={() => navigate('/intake')}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full bg-blue-600 text-white shadow-xl flex items-center justify-center z-[9999] hover:scale-105 active:scale-95 shadow-[0_0_30px_rgba(59,130,246,0.5)]"
      >
        <Plus className="w-6 h-6" />
      </Button>
    </div>
  );
}
