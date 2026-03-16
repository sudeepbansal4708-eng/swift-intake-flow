import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { ArrowLeft, Camera, MapPin, Navigation, Car } from 'lucide-react';
import { toast } from 'sonner';

export default function IntakeForm() {
  const [step, setStep] = useState(1); // 1: Car handoff, 2: GPS & Landmark, 3: Final park
  const [formData, setFormData] = useState({
    phone_number: '',
    license_plate: '',
    tag_number: '',
    zone_label: '',
    gps_latitude: null,
    gps_longitude: null
  });
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [gettingLocation, setGettingLocation] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const captureLocation = () => {
    setGettingLocation(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setFormData({
            ...formData,
            gps_latitude: position.coords.latitude,
            gps_longitude: position.coords.longitude
          });
          toast.success('Location captured!');
          setGettingLocation(false);
        },
        (error) => {
          toast.error('Failed to get location. Please enable GPS.');
          setGettingLocation(false);
        },
        { enableHighAccuracy: true }
      );
    } else {
      toast.error('Geolocation not supported');
      setGettingLocation(false);
    }
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setPhoto(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleStartPark = (e) => {
    e.preventDefault();
    if (!formData.phone_number || !formData.license_plate) {
      toast.error('Please enter phone number and license plate');
      return;
    }
    setStep(2);
    toast.success('Car handoff recorded! Now capture location.');
  };

  const handleFinalPark = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/vehicles`, formData);
      const vehicleId = response.data.vehicle.id;

      if (photo) {
        const photoFormData = new FormData();
        photoFormData.append('vehicle_id', vehicleId);
        photoFormData.append('photo', photo);
        await axios.post(`${API}/vehicles/upload-photo`, photoFormData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }

      toast.success('✅ Vehicle parked! Customer notified via WhatsApp.');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to park vehicle');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mobile-container">
      <div className="gradient-glow-overlay" />
      <div className="content-wrapper p-4 space-y-6">
        <div className="flex items-center gap-3">
          <Button
            data-testid="back-button"
            onClick={() => step === 1 ? navigate('/') : setStep(1)}
            variant="ghost"
            size="icon"
            className="h-10 w-10 text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
              {step === 1 ? 'Car Handoff' : 'Parking Location'}
            </h1>
            <p className="text-sm text-zinc-400">Step {step} of 2</p>
          </div>
        </div>

        {step === 1 && (
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
            <form onSubmit={handleStartPark} className="space-y-4">
              <div className="flex items-center gap-3 mb-4 p-4 bg-blue-950/20 border border-blue-900/50 rounded-lg">
                <Car className="w-8 h-8 text-blue-400" />
                <div>
                  <div className="font-medium text-white">Car Handoff</div>
                  <div className="text-xs text-zinc-400">Enter customer details</div>
                </div>
              </div>

              <div>
                <Label htmlFor="phone" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  Customer Phone Number
                </Label>
                <Input
                  data-testid="phone-input"
                  id="phone"
                  type="tel"
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  placeholder="+1234567890"
                  required
                  autoFocus
                />
              </div>

              <div>
                <Label htmlFor="plate" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  License Plate / Car Number
                </Label>
                <Input
                  data-testid="plate-input"
                  id="plate"
                  type="text"
                  value={formData.license_plate}
                  onChange={(e) => setFormData({ ...formData, license_plate: e.target.value.toUpperCase() })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  placeholder="ABC-1234"
                  required
                />
              </div>

              <Button
                data-testid="start-park-button"
                type="submit"
                className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
              >
                START PARK →
              </Button>
            </form>
          </Card>
        )}

        {step === 2 && (
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
            <form onSubmit={handleFinalPark} className="space-y-4">
              <div className="flex items-center gap-3 mb-4 p-4 bg-emerald-950/20 border border-emerald-900/50 rounded-lg">
                <MapPin className="w-8 h-8 text-emerald-400" />
                <div>
                  <div className="font-medium text-white">Parking Location</div>
                  <div className="text-xs text-zinc-400">{formData.license_plate}</div>
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  GPS Location
                </Label>
                <Button
                  data-testid="gps-button"
                  type="button"
                  onClick={captureLocation}
                  disabled={gettingLocation}
                  className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-zinc-800 hover:bg-zinc-700 text-white border border-zinc-700"
                >
                  <Navigation className="w-4 h-4 mr-2" />
                  {gettingLocation ? 'Getting Location...' : formData.gps_latitude ? '✅ Location Captured' : 'Capture GPS Location'}
                </Button>
                {formData.gps_latitude && (
                  <p className="text-xs text-emerald-400 mt-2">
                    📍 {formData.gps_latitude.toFixed(6)}, {formData.gps_longitude.toFixed(6)}
                  </p>
                )}
              </div>

              <div>
                <Label htmlFor="zone" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  Landmark / Zone / Level
                </Label>
                <Input
                  data-testid="zone-input"
                  id="zone"
                  type="text"
                  value={formData.zone_label}
                  onChange={(e) => setFormData({ ...formData, zone_label: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  placeholder="Level 3, Section B"
                />
              </div>

              <div>
                <Label htmlFor="tag" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  🏷️ Key Tag Number
                </Label>
                <Input
                  data-testid="tag-input"
                  id="tag"
                  type="text"
                  value={formData.tag_number}
                  onChange={(e) => setFormData({ ...formData, tag_number: e.target.value.toUpperCase() })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  placeholder="TAG-001"
                  required
                />
                <p className="text-xs text-zinc-500 mt-1">Attach this tag to the car keys</p>
              </div>

              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  Vehicle Photo (Optional)
                </Label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handlePhotoChange}
                  className="hidden"
                />
                <Button
                  data-testid="photo-button"
                  type="button"
                  onClick={() => fileInputRef.current.click()}
                  className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-zinc-800 hover:bg-zinc-700 text-white border border-zinc-700"
                >
                  <Camera className="w-4 h-4 mr-2" />
                  {photo ? '✅ Photo Captured' : 'Take Photo'}
                </Button>
                {photoPreview && (
                  <div className="mt-3 rounded-lg overflow-hidden border border-zinc-800">
                    <img src={photoPreview} alt="Vehicle" className="w-full h-48 object-cover" />
                  </div>
                )}
              </div>

              <Button
                data-testid="submit-button"
                type="submit"
                disabled={loading || !formData.gps_latitude}
                className="w-full h-12 rounded-lg font-medium transition-all active:scale-95 bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] border border-emerald-500/50"
              >
                {loading ? 'Parking...' : 'PARK VEHICLE ✓'}
              </Button>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}
