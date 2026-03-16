import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { ArrowLeft, Crown, Users, Building, Plus, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';

export default function SuperAdminPanel() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    client_name: ''
  });
  const navigate = useNavigate();

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/super-admin/clients`);
      setClients(response.data);
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
      setFormData({ email: '', password: '', name: '', client_name: '' });
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create admin');
    }
  };

  const deleteAdmin = async (adminId) => {
    if (!window.confirm('Are you sure you want to deactivate this admin?')) return;
    
    try {
      await axios.delete(`${API}/super-admin/admins/${adminId}`);
      toast.success('Admin deactivated');
      fetchClients();
    } catch (error) {
      toast.error('Failed to deactivate admin');
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
          <div>
            <div className="flex items-center gap-2">
              <Crown className="w-6 h-6 text-amber-400" />
              <h1 className="text-3xl font-bold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Super Admin
              </h1>
            </div>
            <p className="text-sm text-zinc-400">Manage client admins</p>
          </div>
        </div>

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
                <Button
                  onClick={() => setShowAddForm(false)}
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-zinc-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              <form onSubmit={handleCreateAdmin} className="space-y-4">
                <div>
                  <Label htmlFor="client_name" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                    Client/Business Name
                  </Label>
                  <Input
                    id="client_name"
                    type="text"
                    value={formData.client_name}
                    onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
                    className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500"
                    placeholder="Acme Valet Services"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="name" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                    Admin Name
                  </Label>
                  <Input
                    id="name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500"
                    placeholder="John Doe"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="email" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500"
                    placeholder="admin@acme.com"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="password" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                    Password
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500"
                    placeholder="••••••••"
                    required
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-amber-600 hover:bg-amber-500 text-white"
                >
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
            {clients.map((admin) => (
              <Card
                key={admin.id}
                data-testid={`admin-${admin.id}`}
                className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Building className="w-4 h-4 text-amber-400" />
                      <div className="font-bold text-white">{admin.client_name || 'Unnamed Client'}</div>
                    </div>
                    <div className="text-sm text-zinc-400">{admin.name}</div>
                    <div className="text-xs text-zinc-500">{admin.email}</div>
                    
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
                    
                    {admin.is_active === false && (
                      <span className="inline-block mt-2 text-xs text-red-400 px-2 py-0.5 bg-red-950/20 border border-red-900/50 rounded">
                        Inactive
                      </span>
                    )}
                  </div>
                  
                  {admin.is_active !== false && (
                    <Button
                      data-testid={`delete-admin-${admin.id}`}
                      onClick={() => deleteAdmin(admin.id)}
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-red-400 hover:text-red-300 hover:bg-red-950/20"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </Card>
            ))}

            {clients.length === 0 && (
              <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-8 text-center">
                <Building className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                <p className="text-zinc-400">No client admins yet</p>
                <p className="text-sm text-zinc-500 mt-1">Click "Add Client Admin" to get started</p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
