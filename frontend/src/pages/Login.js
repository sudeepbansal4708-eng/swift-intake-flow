import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API, setAuthToken } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { Car, Phone, KeyRound, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

export default function Login({ setIsAuthenticated }) {
  const [mode, setMode] = useState('choose'); // choose, superadmin, otp-phone, otp-verify
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [otpPhone, setOtpPhone] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [devOtp, setDevOtp] = useState('');
  const navigate = useNavigate();

  const handleSuperAdminLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, formData);
      setAuthToken(response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setIsAuthenticated(true);
      toast.success('Logged in successfully!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestOTP = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      let phone = otpPhone.trim();
      if (!phone.startsWith('+')) phone = '+' + phone;
      const res = await axios.post(`${API}/auth/otp/request`, { phone_number: phone });
      if (res.data.dev_otp) {
        setDevOtp(res.data.dev_otp);
      }
      toast.success('OTP sent to your WhatsApp!');
      setMode('otp-verify');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      let phone = otpPhone.trim();
      if (!phone.startsWith('+')) phone = '+' + phone;
      const response = await axios.post(`${API}/auth/otp/verify`, { phone_number: phone, otp: otpCode.trim() });
      setAuthToken(response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setIsAuthenticated(true);
      toast.success('Logged in successfully!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const goBack = () => {
    if (mode === 'otp-verify') setMode('otp-phone');
    else setMode('choose');
    setOtpCode('');
    setDevOtp('');
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="gradient-glow-overlay" />
      <div className="mobile-container flex flex-col justify-center content-wrapper">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-600/20 border border-blue-500/50 mb-4">
            <Car className="w-8 h-8 text-blue-500" />
          </div>
          <h1 className="text-5xl font-bold uppercase tracking-tight text-white mb-2" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
            SwiftValet
          </h1>
          <p className="text-zinc-400 text-sm">PREMIUM PARKING SERVICE</p>
        </div>

        {/* Role chooser */}
        {mode === 'choose' && (
          <div className="space-y-3">
            <Button
              data-testid="otp-login-btn"
              onClick={() => setMode('otp-phone')}
              className="w-full h-14 rounded-lg font-medium text-base bg-blue-600 hover:bg-blue-500 text-white border border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.2)]"
            >
              <Phone className="w-5 h-5 mr-3" />
              Login with OTP
            </Button>
            <Button
              data-testid="superadmin-login-btn"
              onClick={() => setMode('superadmin')}
              variant="outline"
              className="w-full h-14 rounded-lg font-medium text-base border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
            >
              <KeyRound className="w-5 h-5 mr-3" />
              Super Admin Login
            </Button>
          </div>
        )}

        {/* Super Admin password login */}
        {mode === 'superadmin' && (
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Button onClick={goBack} variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white">
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <h2 className="text-lg font-semibold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Super Admin Login
              </h2>
            </div>
            <form onSubmit={handleSuperAdminLogin} className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Email</Label>
                <Input
                  data-testid="email-input"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500"
                  placeholder="superadmin@example.com"
                  required
                />
              </div>
              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Password</Label>
                <Input
                  data-testid="password-input"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500"
                  placeholder="••••••••"
                  required
                />
              </div>
              <Button
                data-testid="superadmin-submit-btn"
                type="submit"
                disabled={loading}
                className="w-full h-12 rounded-lg font-medium bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
              >
                {loading ? 'Logging in...' : 'LOGIN'}
              </Button>
            </form>
          </Card>
        )}

        {/* OTP - Phone entry (for both Valets and Admins) */}
        {mode === 'otp-phone' && (
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Button onClick={goBack} variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white">
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <h2 className="text-lg font-semibold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Login with OTP
              </h2>
            </div>
            <p className="text-sm text-zinc-400 mb-4">Enter your phone number. We'll send a login code to your WhatsApp.</p>
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">Phone Number</Label>
                <Input
                  data-testid="otp-phone-input"
                  type="tel"
                  value={otpPhone}
                  onChange={(e) => setOtpPhone(e.target.value)}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500"
                  placeholder="+91 9876543210"
                  required
                />
              </div>
              <Button
                data-testid="send-otp-btn"
                type="submit"
                disabled={loading}
                className="w-full h-12 rounded-lg font-medium bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
              >
                {loading ? 'Sending...' : 'SEND OTP'}
              </Button>
            </form>
          </Card>
        )}

        {/* OTP - Code verification */}
        {mode === 'otp-verify' && (
          <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Button onClick={goBack} variant="ghost" size="icon" className="h-8 w-8 text-zinc-400 hover:text-white">
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <h2 className="text-lg font-semibold uppercase tracking-tight" style={{fontFamily: 'Barlow Condensed, sans-serif'}}>
                Enter OTP
              </h2>
            </div>
            <p className="text-sm text-zinc-400 mb-4">
              A 6-digit code was sent to <span className="text-white font-medium">{otpPhone}</span> via WhatsApp.
            </p>
            {devOtp && (
              <div data-testid="dev-otp-display" className="mb-4 p-3 rounded-lg bg-amber-950/30 border border-amber-700/40">
                <div className="text-[10px] text-amber-500/80 uppercase tracking-widest mb-1">Dev Mode — Your OTP</div>
                <div className="text-2xl font-mono font-bold text-amber-400 tracking-[0.3em] text-center">{devOtp}</div>
              </div>
            )}
            <form onSubmit={handleVerifyOTP} className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">OTP Code</Label>
                <Input
                  data-testid="otp-code-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  className="h-14 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white text-center text-2xl tracking-[0.5em] font-mono placeholder:text-zinc-500 focus:border-blue-500"
                  placeholder="------"
                  required
                />
              </div>
              <Button
                data-testid="verify-otp-btn"
                type="submit"
                disabled={loading || otpCode.length !== 6}
                className="w-full h-12 rounded-lg font-medium bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
              >
                {loading ? 'Verifying...' : 'VERIFY & LOGIN'}
              </Button>
              <button
                data-testid="resend-otp-btn"
                type="button"
                onClick={handleRequestOTP}
                className="w-full text-sm text-zinc-400 hover:text-white transition-colors pt-1"
              >
                Didn't receive it? Resend OTP
              </button>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}
