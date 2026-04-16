import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { Crown, Users, Building, Plus, Trash2, X, Car, DollarSign, TrendingUp, ChevronRight, Loader2, Archive, ChevronDown, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../components/ui/collapsible';

export default function SuperAdminPanel() {
  const [clients, setClients] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientReport, setClientReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [formData, setFormData] = useState({
    phone_number: '+91',
    name: '',
    client_name: ''
  });
  // Note: email field removed - backend auto-generates from phone
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    delete axios.defaults.headers.common['Authorization'];
    navigate('/login');
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [clientsRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/super-admin/clients`),
        axios.get(`${API}/super-admin/analytics`)
      ]);
      setClients(clientsRes.data);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Super admin access required');
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAdmin = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/super-admin/admins`, formData);
      toast.success('Admin created successfully!');
      setShowAddForm(false);
      setFormData({ phone_number: '+91', name: '', client_name: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create admin');
    }
  };

  const deleteAdmin = async (adminId, e) => {
    e.stopPropagation();
    if (confirmDelete !== adminId) {
      setConfirmDelete(adminId);
      return;
    }
    setConfirmDelete(null);
    try {
      await axios.delete(`${API}/super-admin/admins/${adminId}`);
      toast.success('Admin deactivated');
      fetchData();
      if (selectedClient?.id === adminId) {
        setSelectedClient(null);
        setClientReport(null);
      }
    } catch (error) {
      toast.error('Failed to deactivate admin');
    }
  };

  const openClientReport = async (admin) => {
    if (!admin.client_id) return;
    setSelectedClient(admin);
    setReportLoading(true);
    setClientReport(null);
    try {
      const res = await axios.get(`${API}/super-admin/clients/${admin.client_id}/report`);
      setClientReport(res.data);
    } catch {
      toast.error('Failed to load client report');
    } finally {
      setReportLoading(false);
    }
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
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Crown className="w-6 h-6 text-amber-400" />
            <div>
              <h1 className="text-3xl font-bold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Dashboard
              </h1>
              <p className="text-sm text-zinc-400">Super Admin</p>
            </div>
          </div>
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

        {analytics && (
          <div className="grid grid-cols-2 gap-3">
            <Card className="bg-gradient-to-br from-amber-950/30 to-zinc-900/50 backdrop-blur-md border border-amber-800/50 p-4">
              <Building className="w-6 h-6 text-amber-400 mb-2" />
              <div className="text-3xl font-bold text-white">{analytics.total_clients}</div>
              <div className="text-xs text-amber-400 uppercase tracking-wider">Total Clients</div>
            </Card>
            <Card className="bg-gradient-to-br from-blue-950/30 to-zinc-900/50 backdrop-blur-md border border-blue-800/50 p-4">
              <Car className="w-6 h-6 text-blue-400 mb-2" />
              <div className="text-3xl font-bold text-white">{analytics.cars_parked_now}</div>
              <div className="text-xs text-blue-400 uppercase tracking-wider">Cars Parked Now</div>
            </Card>
            <Card className="bg-gradient-to-br from-emerald-950/30 to-zinc-900/50 backdrop-blur-md border border-emerald-800/50 p-4 relative opacity-60">
              <DollarSign className="w-6 h-6 text-emerald-400 mb-2" />
              <div className="text-3xl font-bold text-white">--</div>
              <div className="text-xs text-emerald-400 uppercase tracking-wider">Tips Today</div>
              <span className="absolute top-2 right-2 text-[9px] px-1.5 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800/50 font-semibold">COMING SOON</span>
            </Card>
            <Card className="bg-gradient-to-br from-purple-950/30 to-zinc-900/50 backdrop-blur-md border border-purple-800/50 p-4">
              <TrendingUp className="w-6 h-6 text-purple-400 mb-2" />
              <div className="text-3xl font-bold text-white">{analytics.tickets_today}</div>
              <div className="text-xs text-purple-400 uppercase tracking-wider">Tickets Today</div>
            </Card>
          </div>
        )}

        <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-2xl font-bold text-white">{clients.length}</div>
              <div className="text-xs text-zinc-400 uppercase tracking-wider">Total Clients</div>
            </div>
            <Button
              data-testid="add-admin-button"
              onClick={() => setShowAddForm(!showAddForm)}
              className="h-10 px-4 rounded-lg font-medium transition-all active:scale-95 bg-amber-600 hover:bg-amber-500 text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Client Admin
            </Button>
          </div>

          {showAddForm && (
            <Card className="bg-zinc-950/50 border border-amber-800 p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-amber-400 uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                  Create New Client Admin
                </h3>
                <Button onClick={() => setShowAddForm(false)} variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white">
                  <X className="w-4 h-4" />
                </Button>
              </div>
              <form onSubmit={handleCreateAdmin} className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Client/Business Name</Label>
                  <Input type="text" value={formData.client_name} onChange={(e) => setFormData({ ...formData, client_name: e.target.value })} className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500" placeholder="Acme Valet Services" required />
                </div>
                <div>
                  <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Admin Name</Label>
                  <Input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500" placeholder="John Doe" required />
                </div>
                <div>
                  <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Phone Number (for OTP Login)</Label>
                  <Input type="tel" value={formData.phone_number} onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })} className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500" placeholder="+91 9876543210" required />
                </div>
                <Button type="submit" className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-amber-600 hover:bg-amber-500 text-white">
                  Create Admin
                </Button>
              </form>
            </Card>
          )}
        </Card>

        <div>
          <h2 className="text-lg font-semibold uppercase tracking-tight mb-3" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            Client Admins
          </h2>
          <div className="space-y-3">
            {clients.filter(a => a.is_active !== false).map((admin) => (
              <Card
                key={admin.id}
                data-testid={`admin-${admin.id}`}
                onClick={() => openClientReport(admin)}
                className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 hover:border-zinc-600 cursor-pointer active:scale-[0.98] p-4 transition-all"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Building className="w-4 h-4 text-amber-400" />
                      <div className="font-bold text-white">{admin.client_name || 'Unnamed Client'}</div>
                    </div>
                    <div className="text-sm text-zinc-400">{admin.name}</div>
                    <div className="text-xs text-zinc-500">{admin.email}</div>
                    {admin.phone_number && (
                      <div className="text-xs text-zinc-500">{admin.phone_number}</div>
                    )}
                    {admin.stats && (
                      <div className="flex gap-4 mt-2">
                        <div className="text-xs">
                          <span className="text-zinc-500">Valets:</span>
                          <span className="text-white ml-1">{admin.stats.valets}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-zinc-500">Vehicles:</span>
                          <span className="text-white ml-1">{admin.stats.vehicles}</span>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {confirmDelete === admin.id ? (
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button
                          data-testid={`confirm-delete-${admin.id}`}
                          onClick={(e) => deleteAdmin(admin.id, e)}
                          className="h-7 px-2 text-[10px] rounded bg-red-600 hover:bg-red-500 text-white font-semibold"
                        >
                          Confirm
                        </Button>
                        <Button
                          data-testid={`cancel-delete-${admin.id}`}
                          onClick={(e) => { e.stopPropagation(); setConfirmDelete(null); }}
                          variant="ghost"
                          className="h-7 px-2 text-[10px] text-zinc-400 hover:text-white"
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        data-testid={`delete-admin-${admin.id}`}
                        onClick={(e) => deleteAdmin(admin.id, e)}
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-400 hover:text-red-300 hover:bg-red-950/20"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                    <ChevronRight className="w-4 h-4 text-zinc-600" />
                  </div>
                </div>
              </Card>
            ))}

            {clients.filter(a => a.is_active !== false).length === 0 && (
              <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-8 text-center">
                <Building className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                <p className="text-zinc-400">No active client admins</p>
                <p className="text-sm text-zinc-500 mt-1">Click "Add Client Admin" to get started</p>
              </Card>
            )}
          </div>
        </div>

        {/* Archived Clients */}
        {clients.filter(a => a.is_active === false).length > 0 && (
          <Collapsible open={archiveOpen} onOpenChange={setArchiveOpen}>
            <CollapsibleTrigger asChild>
              <div
                data-testid="toggle-archive-section"
                className="flex items-center justify-between py-3 px-1 cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <Archive className="w-4 h-4 text-zinc-600" />
                  <span className="text-sm text-zinc-500 uppercase tracking-widest font-semibold" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                    Archive
                  </span>
                  <span className="text-xs text-zinc-600 bg-zinc-800/50 px-1.5 py-0.5 rounded">
                    {clients.filter(a => a.is_active === false).length}
                  </span>
                </div>
                <ChevronDown className={`w-4 h-4 text-zinc-600 transition-transform duration-200 ${archiveOpen ? 'rotate-180' : ''}`} />
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="space-y-2 pt-1">
                {clients.filter(a => a.is_active === false).map((admin) => (
                  <Card
                    key={admin.id}
                    data-testid={`archived-admin-${admin.id}`}
                    className="bg-zinc-900/30 border border-zinc-800/40 p-3 opacity-50"
                  >
                    <div className="flex items-center gap-2">
                      <Building className="w-3.5 h-3.5 text-zinc-600" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-zinc-400 font-medium truncate">{admin.client_name || 'Unnamed Client'}</div>
                        <div className="text-xs text-zinc-600 truncate">{admin.name} &middot; {admin.email}</div>
                      </div>
                      <span className="text-[9px] text-red-500/60 uppercase tracking-wider shrink-0">Deactivated</span>
                    </div>
                  </Card>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>

      {/* Client Report Modal */}
      {selectedClient && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => { setSelectedClient(null); setClientReport(null); }}>
          <Card
            data-testid="client-report-modal"
            className="bg-zinc-900 border border-zinc-700 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-zinc-800">
              <div>
                <h3 className="font-bold text-white text-lg uppercase" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                  {selectedClient.client_name || 'Client Report'}
                </h3>
                <p className="text-xs text-zinc-500">Admin: {selectedClient.name}</p>
              </div>
              <Button
                data-testid="close-report-modal"
                onClick={() => { setSelectedClient(null); setClientReport(null); }}
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-zinc-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {reportLoading ? (
              <div className="p-8 flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-zinc-400 animate-spin" />
              </div>
            ) : clientReport ? (
              <div className="p-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Card data-testid="report-num-drivers" className="bg-zinc-800/50 border border-zinc-700 p-4">
                    <Users className="w-5 h-5 text-blue-400 mb-1.5" />
                    <div className="text-2xl font-bold text-white">{clientReport.num_drivers}</div>
                    <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Drivers</div>
                  </Card>
                  <Card data-testid="report-cars-parked-now" className="bg-zinc-800/50 border border-zinc-700 p-4">
                    <Car className="w-5 h-5 text-emerald-400 mb-1.5" />
                    <div className="text-2xl font-bold text-white">{clientReport.cars_parked_now}</div>
                    <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Parked Now</div>
                  </Card>
                  <Card data-testid="report-tips-today" className="bg-zinc-800/50 border border-zinc-700 p-4 relative opacity-60">
                    <DollarSign className="w-5 h-5 text-amber-400 mb-1.5" />
                    <div className="text-2xl font-bold text-white">--</div>
                    <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Tips Today</div>
                    <span className="absolute top-1.5 right-1.5 text-[8px] px-1 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800/50 font-semibold">SOON</span>
                  </Card>
                  <Card data-testid="report-cars-parked-today" className="bg-zinc-800/50 border border-zinc-700 p-4">
                    <TrendingUp className="w-5 h-5 text-violet-400 mb-1.5" />
                    <div className="text-2xl font-bold text-white">{clientReport.cars_parked_today}</div>
                    <div className="text-[10px] text-zinc-400 uppercase tracking-widest">Parked Today</div>
                  </Card>
                </div>
                <p className="text-[10px] text-zinc-600 italic text-center pt-1">Tip data will be available after the pilot phase.</p>
              </div>
            ) : null}
          </Card>
        </div>
      )}
    </div>
  );
}
