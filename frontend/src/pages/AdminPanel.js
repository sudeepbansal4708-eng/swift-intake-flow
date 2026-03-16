import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { ArrowLeft, Users, DollarSign, Car, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

export default function AdminPanel() {
  const [valets, setValets] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [tips, setTips] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [valetsRes, vehiclesRes, tipsRes] = await Promise.all([
        axios.get(`${API}/admin/valets`),
        axios.get(`${API}/vehicles`),
        axios.get(`${API}/admin/tips`).catch(() => ({ data: [] }))
      ]);
      
      setValets(valetsRes.data);
      setVehicles(vehiclesRes.data);
      setTips(tipsRes.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const deleteValet = async (valetId) => {
    if (!window.confirm('Are you sure you want to deactivate this valet?')) return;
    
    try {
      await axios.delete(`${API}/admin/valets/${valetId}`);
      toast.success('Valet deactivated');
      fetchData();
    } catch (error) {
      toast.error('Failed to deactivate valet');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-zinc-400">Loading...</div>
      </div>
    );
  }

  const totalTips = tips.reduce((sum, tip) => sum + (tip.amount || 0), 0);
  const activeValets = valets.filter(v => v.is_active !== false);

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
            Admin Panel
          </h1>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4">
            <Users className="w-6 h-6 text-blue-500 mb-2" />
            <div className="text-2xl font-bold text-white">{activeValets.length}</div>
            <div className="text-xs text-zinc-400 uppercase tracking-wider">Active Valets</div>
          </Card>
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4">
            <Car className="w-6 h-6 text-emerald-500 mb-2" />
            <div className="text-2xl font-bold text-white">{vehicles.length}</div>
            <div className="text-xs text-zinc-400 uppercase tracking-wider">Vehicles</div>
          </Card>
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4">
            <DollarSign className="w-6 h-6 text-amber-500 mb-2" />
            <div className="text-2xl font-bold text-white">₹{totalTips}</div>
            <div className="text-xs text-zinc-400 uppercase tracking-wider">Total Tips</div>
          </Card>
        </div>

        <div>
          <h2 className="text-lg font-semibold uppercase tracking-tight mb-3" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            Valet Drivers
          </h2>
          <div className="space-y-2">
            {valets.map((valet) => (
              <Card
                key={valet.id}
                data-testid={`valet-${valet.id}`}
                className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 flex justify-between items-center"
              >
                <div>
                  <div className="font-medium text-white">{valet.name}</div>
                  <div className="text-sm text-zinc-400">{valet.email}</div>
                  <div className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border mt-1">
                    <span className={valet.role === 'admin' ? 'text-amber-400' : 'text-blue-400'}>
                      {valet.role.toUpperCase()}
                    </span>
                  </div>
                  {valet.is_active === false && (
                    <span className="ml-2 text-xs text-red-400">(Inactive)</span>
                  )}
                </div>
                {valet.is_active !== false && valet.role !== 'admin' && (
                  <Button
                    data-testid={`delete-valet-${valet.id}`}
                    onClick={() => deleteValet(valet.id)}
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-red-400 hover:text-red-300 hover:bg-red-950/20"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-lg font-semibold uppercase tracking-tight mb-3" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            Recent Vehicles
          </h2>
          <div className="space-y-2">
            {vehicles.slice(0, 10).map((vehicle) => (
              <Card
                key={vehicle.id}
                data-testid={`vehicle-${vehicle.id}`}
                className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-white">{vehicle.license_plate}</div>
                    <div className="text-sm text-zinc-400">{vehicle.phone_number}</div>
                    {vehicle.zone_label && (
                      <div className="text-xs text-zinc-500 mt-1">{vehicle.zone_label}</div>
                    )}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {new Date(vehicle.parked_at).toLocaleDateString()}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
