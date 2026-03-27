import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { ArrowLeft, Trash2, Plus, X, IdCard, Camera, Eye, UserCog, Save, BarChart3, ChevronDown, Upload, Wifi, WifiOff } from 'lucide-react';
import { toast } from 'sonner';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '../components/ui/collapsible';
import { Switch } from '../components/ui/switch';

export default function AdminPanel() {
  const [valets, setValets] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [tips, setTips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [showLicenseModal, setShowLicenseModal] = useState(false);
  const [selectedValet, setSelectedValet] = useState(null);
  const [licenseData, setLicenseData] = useState({ number: '', photo: null, preview: null });
  const [formData, setFormData] = useState({ email: '', name: '', phone_number: '', driver_license_number: '' });
  const [profileData, setProfileData] = useState({ name: '', client_name: '', profile_photo: null });
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [teamOpen, setTeamOpen] = useState(true);
  const [onlineRequests, setOnlineRequests] = useState([]);
  const fileInputRef = useRef(null);
  const profilePhotoRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
    fetchProfile();
    fetchOnlineRequests();
    const interval = setInterval(fetchOnlineRequests, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await axios.get(`${API}/auth/me`);
      setProfileData({
        name: res.data.name || '',
        client_name: res.data.client_name || '',
        profile_photo: res.data.profile_photo || null
      });
    } catch (error) {
      console.error('Failed to fetch profile');
    }
  };

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

  const handleCreateValet = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API}/admin/valets`, formData);
      const valetId = response.data.user.id;
      
      // If license photo provided, upload it
      if (licenseData.photo && formData.driver_license_number) {
        const licenseForm = new FormData();
        licenseForm.append('license_number', formData.driver_license_number);
        licenseForm.append('license_photo', licenseData.photo);
        
        await axios.post(`${API}/admin/valets/${valetId}/license`, licenseForm, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }
      
      toast.success('Valet created successfully!');
      setShowAddForm(false);
      setFormData({ email: '', name: '', phone_number: '', driver_license_number: '' });
      setLicenseData({ number: '', photo: null, preview: null });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create valet');
    }
  };

  const handleLicensePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setLicenseData({ ...licenseData, photo: file, preview: URL.createObjectURL(file) });
    }
  };

  const deleteValet = async (valetId) => {
    if (confirmDelete !== valetId) {
      setConfirmDelete(valetId);
      return;
    }
    setConfirmDelete(null);
    try {
      await axios.delete(`${API}/admin/valets/${valetId}`);
      toast.success('Valet deactivated');
      fetchData();
    } catch (error) {
      toast.error('Failed to deactivate valet');
    }
  };

  const viewLicense = (valet) => {
    setSelectedValet(valet);
    setShowLicenseModal(true);
  };

  const toggleValetOnline = async (valetId) => {
    try {
      const res = await axios.put(`${API}/admin/valets/${valetId}/toggle-online`);
      const status = res.data.is_online ? 'online' : 'offline';
      toast.success(`Valet marked ${status}`);
      fetchData();
      fetchOnlineRequests();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to toggle status');
    }
  };

  const fetchOnlineRequests = async () => {
    try {
      const res = await axios.get(`${API}/admin/online-requests`);
      setOnlineRequests(res.data);
    } catch {
      // silent
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!profileData.name.trim() && !profileData.client_name.trim()) {
      toast.error('Please fill in at least one field');
      return;
    }
    setProfileLoading(true);
    try {
      const params = new URLSearchParams();
      if (profileData.name.trim()) params.append('name', profileData.name.trim());
      if (profileData.client_name.trim()) params.append('client_name', profileData.client_name.trim());
      await axios.put(`${API}/admin/profile?${params.toString()}`);
      toast.success('Profile updated successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleProfilePhoto = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('photo', file);
    try {
      const res = await axios.post(`${API}/admin/profile/photo`, form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setProfileData(p => ({ ...p, profile_photo: res.data.profile_photo }));
      toast.success('Profile photo updated!');
    } catch {
      toast.error('Failed to upload photo');
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

        {/* Tab Switcher */}
        <div className="flex gap-2">
          <Button
            data-testid="tab-management-btn"
            variant="ghost"
            className="h-9 px-4 rounded-full text-xs uppercase tracking-wider bg-blue-600/20 text-blue-400 border border-blue-500/30"
          >
            Management
          </Button>
          <Button
            data-testid="tab-reporting-btn"
            onClick={() => navigate('/admin/reporting')}
            variant="ghost"
            className="h-9 px-4 rounded-full text-xs uppercase tracking-wider text-zinc-400 hover:text-white hover:bg-zinc-800 border border-zinc-800"
          >
            <BarChart3 className="w-3.5 h-3.5 mr-1.5" />
            Reporting
          </Button>
        </div>

        {/* Profile Editor - Collapsible */}
        <Collapsible open={profileOpen} onOpenChange={setProfileOpen}>
          <Card data-testid="admin-profile-card" className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800">
            <CollapsibleTrigger asChild>
              <button
                data-testid="toggle-profile-section"
                className="w-full flex items-center justify-between p-4 text-left hover:bg-zinc-800/30 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <UserCog className="w-5 h-5 text-violet-400" />
                  <h2 className="text-lg font-semibold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                    My Profile
                  </h2>
                </div>
                <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform duration-200 ${profileOpen ? 'rotate-180' : ''}`} />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 pb-4">
                {/* Profile Photo */}
                <div className="flex items-center gap-4 mb-4">
                  <div
                    data-testid="profile-photo-area"
                    onClick={() => profilePhotoRef.current?.click()}
                    className="relative w-16 h-16 rounded-full bg-zinc-800 border-2 border-zinc-700 hover:border-violet-500/50 cursor-pointer transition-colors overflow-hidden flex items-center justify-center group"
                  >
                    {profileData.profile_photo ? (
                      <img src={profileData.profile_photo} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                      <UserCog className="w-6 h-6 text-zinc-500" />
                    )}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                      <Upload className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <input ref={profilePhotoRef} type="file" accept="image/*" onChange={handleProfilePhoto} className="hidden" />
                  <div className="text-xs text-zinc-500">Tap to upload photo</div>
                </div>
                <form onSubmit={handleSaveProfile} className="space-y-3">
                  <div>
                    <Label className="text-xs font-medium text-zinc-400 mb-1 block uppercase tracking-wide">Your Name</Label>
                    <Input
                      data-testid="admin-profile-name"
                      type="text"
                      value={profileData.name}
                      onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                      className="h-11 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white"
                      placeholder="Your full name"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-medium text-zinc-400 mb-1 block uppercase tracking-wide">Client / Business Name</Label>
                    <Input
                      data-testid="admin-profile-client-name"
                      type="text"
                      value={profileData.client_name}
                      onChange={(e) => setProfileData({ ...profileData, client_name: e.target.value })}
                      className="h-11 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white"
                      placeholder="e.g. The Grand Restaurant"
                    />
                    <p className="text-xs text-zinc-500 mt-1">This name appears in WhatsApp messages sent to customers.</p>
                  </div>
                  <Button
                    data-testid="admin-profile-save-btn"
                    type="submit"
                    disabled={profileLoading}
                    className="w-full h-11 rounded-lg bg-violet-600 hover:bg-violet-500 font-medium"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {profileLoading ? 'Saving...' : 'Save Profile'}
                  </Button>
                </form>
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>

        {/* Team Management - Collapsible */}
        <Collapsible open={teamOpen} onOpenChange={setTeamOpen}>
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800">
            <CollapsibleTrigger asChild>
              <div
                data-testid="toggle-team-section"
                className="w-full flex items-center justify-between p-4 text-left hover:bg-zinc-800/30 transition-colors rounded-lg cursor-pointer"
              >
                <h2 className="text-lg font-semibold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                  Team Management
                </h2>
                <div className="flex items-center gap-2">
                  <Button
                    data-testid="add-valet-btn"
                    onClick={(e) => { e.stopPropagation(); setShowAddForm(!showAddForm); setTeamOpen(true); }}
                    className="h-8 px-3 rounded-lg font-medium text-xs bg-blue-600 hover:bg-blue-500"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    Add Valet
                  </Button>
                  <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform duration-200 ${teamOpen ? 'rotate-180' : ''}`} />
                </div>
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 pb-4 space-y-3">
                {showAddForm && (
          <Card className="bg-zinc-950/50 border border-blue-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-blue-400 uppercase" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Add New Valet Driver
              </h3>
              <Button onClick={() => setShowAddForm(false)} variant="ghost" size="icon" className="h-8 w-8">
                <X className="w-4 h-4" />
              </Button>
            </div>

            <form onSubmit={handleCreateValet} className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Full Name</Label>
                <Input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white"
                  placeholder="John Doe"
                  required
                />
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Email</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white"
                  placeholder="john@example.com"
                  required
                />
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Phone Number (for OTP Login)</Label>
                <Input
                  type="tel"
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white"
                  placeholder="+91 9876543210"
                  required
                />
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Driver License Number</Label>
                <Input
                  type="text"
                  value={formData.driver_license_number}
                  onChange={(e) => setFormData({ ...formData, driver_license_number: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white"
                  placeholder="DL-1420110012345"
                  required
                />
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Driver License Photo</Label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleLicensePhotoChange}
                  className="hidden"
                />
                <Button
                  type="button"
                  onClick={() => fileInputRef.current.click()}
                  className="w-full h-12 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700"
                >
                  <Camera className="w-4 h-4 mr-2" />
                  {licenseData.photo ? '✅ Photo Captured' : 'Upload License Photo'}
                </Button>
                {licenseData.preview && (
                  <div className="mt-3 rounded-lg overflow-hidden border border-zinc-800">
                    <img src={licenseData.preview} alt="License" className="w-full h-32 object-cover" />
                  </div>
                )}
              </div>

              <Button type="submit" className="w-full h-12 rounded-lg bg-blue-600 hover:bg-blue-500">
                Create Valet
              </Button>
            </form>
          </Card>
        )}

                {/* Pending Online Requests */}
                {onlineRequests.length > 0 && (
                  <Card data-testid="online-requests-card" className="bg-amber-950/20 border border-amber-800/50 p-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-amber-400 mb-2">Shift Requests</div>
                    {onlineRequests.map((req) => (
                      <div key={req.valet_id} className="flex items-center justify-between py-1.5">
                        <span className="text-sm text-white">{req.valet_name} wants to go online</span>
                        <Button
                          data-testid={`approve-online-${req.valet_id}`}
                          onClick={() => toggleValetOnline(req.valet_id)}
                          className="h-7 px-3 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                        >
                          Approve
                        </Button>
                      </div>
                    ))}
                  </Card>
                )}

                {valets.filter(v => v.role !== 'admin').map((valet) => (
                  <Card key={valet.id} data-testid={`valet-card-${valet.id}`} className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-white">{valet.name}</span>
                          {valet.is_online && (
                            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-950/30 border border-emerald-900/50 px-1.5 py-0.5 rounded-full">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              ONLINE
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-zinc-400">{valet.email}</div>
                        {valet.phone_number && (
                          <div className="text-sm text-zinc-500">{valet.phone_number}</div>
                        )}
                        <div className="flex items-center gap-2 mt-2">
                          <div className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border border-zinc-700">
                            <span className="text-blue-400">{valet.role.toUpperCase()}</span>
                          </div>
                          {valet.driver_license_number && (
                            <Button
                              onClick={() => viewLicense(valet)}
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs text-emerald-400 hover:text-emerald-300"
                            >
                              <IdCard className="w-3 h-3 mr-1" />
                              License: {valet.driver_license_number}
                            </Button>
                          )}
                        </div>
                        {valet.is_active === false && (
                          <span className="inline-block mt-1 text-xs text-red-400 px-2 py-0.5 bg-red-950/20 border border-red-900/50 rounded">(Inactive)</span>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        {valet.is_active !== false && (
                          <div className="flex items-center gap-2">
                            <Switch
                              data-testid={`toggle-online-${valet.id}`}
                              checked={!!valet.is_online}
                              onCheckedChange={() => toggleValetOnline(valet.id)}
                            />
                            {confirmDelete === valet.id ? (
                              <div className="flex items-center gap-1">
                                <Button
                                  data-testid={`confirm-delete-valet-${valet.id}`}
                                  onClick={() => deleteValet(valet.id)}
                                  className="h-7 px-2 text-[10px] rounded bg-red-600 hover:bg-red-500 text-white font-semibold"
                                >
                                  Confirm
                                </Button>
                                <Button
                                  data-testid={`cancel-delete-valet-${valet.id}`}
                                  onClick={() => setConfirmDelete(null)}
                                  variant="ghost"
                                  className="h-7 px-2 text-[10px] text-zinc-400 hover:text-white"
                                >
                                  Cancel
                                </Button>
                              </div>
                            ) : (
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
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}

                {valets.filter(v => v.role !== 'admin').length === 0 && (
                  <div className="text-center py-6 text-zinc-500 text-sm">No valet drivers yet</div>
                )}
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      </div>

      {showLicenseModal && selectedValet && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <Card className="bg-zinc-900 border border-zinc-800 p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-white text-lg uppercase" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Driver License
              </h3>
              <Button onClick={() => setShowLicenseModal(false)} variant="ghost" size="icon">
                <X className="w-5 h-5" />
              </Button>
            </div>
            <div className="space-y-4">
              <div>
                <div className="text-sm text-zinc-400 mb-1">Driver Name</div>
                <div className="text-white font-medium">{selectedValet.name}</div>
              </div>
              <div>
                <div className="text-sm text-zinc-400 mb-1">License Number</div>
                <div className="text-white font-mono">{selectedValet.driver_license_number}</div>
              </div>
              {selectedValet.driver_license_photo && (
                <div>
                  <div className="text-sm text-zinc-400 mb-2">License Photo</div>
                  <div className="rounded-lg overflow-hidden border border-zinc-700">
                    <img src={selectedValet.driver_license_photo} alt="Driver License" className="w-full" />
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
