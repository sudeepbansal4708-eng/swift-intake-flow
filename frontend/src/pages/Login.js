import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API, setAuthToken } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card } from '../components/ui/card';
import { Car } from 'lucide-react';
import { toast } from 'sonner';

export default function Login({ setIsAuthenticated }) {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'valet'
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      setAuthToken(response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setIsAuthenticated(true);
      toast.success(isLogin ? 'Logged in successfully!' : 'Account created!');
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
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

        <Card className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <Label htmlFor="name" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  Full Name
                </Label>
                <Input
                  data-testid="name-input"
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  placeholder="Enter your name"
                  required={!isLogin}
                />
              </div>
            )}

            <div>
              <Label htmlFor="email" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                Email
              </Label>
              <Input
                data-testid="email-input"
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                Password
              </Label>
              <Input
                data-testid="password-input"
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="h-12 bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white placeholder:text-zinc-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="••••••••"
                required
              />
            </div>

            {!isLogin && (
              <div>
                <Label htmlFor="role" className="text-sm font-medium text-zinc-400 mb-2 block uppercase tracking-wide">
                  Role
                </Label>
                <select
                  data-testid="role-select"
                  id="role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="h-12 w-full bg-zinc-950/50 border border-zinc-800 rounded-lg px-4 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="valet">Valet Driver</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            )}

            <Button
              data-testid="submit-button"
              type="submit"
              disabled={loading}
              className="w-full h-12 px-6 rounded-lg font-medium transition-all active:scale-95 bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] border border-blue-500/50"
            >
              {loading ? 'Loading...' : isLogin ? 'LOGIN' : 'CREATE ACCOUNT'}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <button
              data-testid="toggle-mode-button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm text-zinc-400 hover:text-white transition-colors"
            >
              {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Login'}
            </button>
          </div>
        </Card>

        <div className="mt-6 text-center text-xs text-zinc-500">
          <p>Demo Credentials:</p>
          <p>Admin: admin@swift.com / admin123</p>
          <p>Valet: valet@swift.com / valet123</p>
        </div>
      </div>
    </div>
  );
}
