import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from '../components/ui/table';
import { ArrowLeft, Car, CarFront, Warehouse, Timer, IndianRupee, TrendingUp, Users, AlertTriangle, Download, BarChart3, Trophy, Clock, FileText } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Cell } from 'recharts';
import { toast } from 'sonner';

const STATUS_COLORS = { green: '#22c55e', amber: '#f59e0b', red: '#ef4444' };

function StatCard({ icon: Icon, label, value, sub, iconColor = 'text-blue-500', testId }) {
  return (
    <Card data-testid={testId} className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 flex flex-col gap-1">
      <Icon className={`w-5 h-5 ${iconColor}`} />
      <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
      <div className="text-[10px] text-zinc-400 uppercase tracking-widest leading-tight">{label}</div>
      {sub && <div className="text-xs text-zinc-500 mt-0.5">{sub}</div>}
    </Card>
  );
}

function RetrievalIndicator({ mins, status }) {
  const color = STATUS_COLORS[status] || STATUS_COLORS.green;
  const labels = { green: '< 8 min', amber: '8-12 min', red: '> 12 min' };
  return (
    <Card data-testid="retrieval-speed-card" className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 p-4 col-span-2">
      <div className="flex items-center gap-3">
        <Timer className="w-5 h-5" style={{ color }} />
        <div className="flex-1">
          <div className="text-xs text-zinc-400 uppercase tracking-widest">Avg Retrieval Time</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-2xl font-bold text-white">{mins} min</span>
            <span
              className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border"
              style={{ color, borderColor: color, background: `${color}15` }}
            >
              {labels[status] || status}
            </span>
          </div>
        </div>
        <div className="flex gap-1">
          {['green', 'amber', 'red'].map(s => (
            <div key={s} className="w-2.5 h-8 rounded-full" style={{ background: s === status ? STATUS_COLORS[s] : '#27272a' }} />
          ))}
        </div>
      </div>
    </Card>
  );
}

function HourlyChart({ data }) {
  const hasData = data.some(d => d.intake > 0 || d.retrieval > 0);
  const formatted = data.map(d => ({
    ...d,
    label: `${d.hour.toString().padStart(2, '0')}:00`
  }));

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-zinc-500">
        <BarChart3 className="w-10 h-10 mb-2 opacity-30" />
        <span className="text-sm">No activity data yet today</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={formatted} barGap={1}>
        <XAxis dataKey="label" tick={{ fill: '#71717a', fontSize: 10 }} interval={2} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#71717a', fontSize: 10 }} allowDecimals={false} axisLine={false} tickLine={false} width={25} />
        <Tooltip
          contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12, color: '#fff' }}
          labelStyle={{ color: '#a1a1aa' }}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#a1a1aa' }} />
        <Bar dataKey="intake" name="Intake" fill="#3b82f6" radius={[3, 3, 0, 0]} />
        <Bar dataKey="retrieval" name="Retrieval" fill="#a855f7" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function AdminReporting() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchReporting();
    const interval = setInterval(fetchReporting, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchReporting = async () => {
    try {
      const res = await axios.get(`${API}/admin/reporting`);
      setData(res.data);
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error('Admin access required');
        navigate('/');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const res = await axios.get(`${API}/admin/reporting/export`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `parkaro_payout_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('CSV downloaded');
    } catch {
      toast.error('Export failed');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-zinc-400">Loading report...</div>
      </div>
    );
  }

  const s = data?.summary || {};
  const leaderboard = data?.leaderboard || [];
  const hourly = data?.hourly_volume || [];
  const waitlist = data?.waitlist || [];
  const fin = data?.financial || {};

  return (
    <div className="mobile-container">
      <div className="gradient-glow-overlay" />
      <div className="content-wrapper p-4 space-y-6 pb-24">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Button
            data-testid="back-to-admin-btn"
            onClick={() => navigate('/admin')}
            variant="ghost"
            size="icon"
            className="h-10 w-10 text-zinc-400 hover:text-white hover:bg-zinc-800"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold uppercase tracking-tight" style={{ fontFamily: 'Barlow Condensed, sans-serif' }}>
              The Nightly Pulse
            </h1>
            <p className="text-xs text-zinc-500 uppercase tracking-widest">
              {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'short', year: 'numeric' })}
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex gap-2">
          <Button
            data-testid="tab-management-btn"
            onClick={() => navigate('/admin')}
            variant="ghost"
            className="h-9 px-4 rounded-full text-xs uppercase tracking-wider text-zinc-400 hover:text-white hover:bg-zinc-800 border border-zinc-800"
          >
            Management
          </Button>
          <Button
            data-testid="tab-reporting-btn"
            variant="ghost"
            className="h-9 px-4 rounded-full text-xs uppercase tracking-wider bg-blue-600/20 text-blue-400 border border-blue-500/30"
          >
            Reporting
          </Button>
        </div>

        {/* Section 1: Tonight's Performance */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400 mb-3" style={{ fontFamily: 'Barlow Condensed, sans-serif' }}>
            Tonight's Performance
          </h2>
          <div className="grid grid-cols-3 gap-2 mb-2">
            <StatCard icon={Car} label="Parked" value={s.cars_parked} iconColor="text-blue-500" testId="stat-cars-parked" />
            <StatCard icon={CarFront} label="Retrieved" value={s.cars_retrieved} iconColor="text-emerald-500" testId="stat-cars-retrieved" />
            <StatCard icon={Warehouse} label="Active Inv." value={s.active_inventory} iconColor="text-violet-500" testId="stat-active-inventory" />
          </div>
          <RetrievalIndicator mins={s.avg_retrieval_mins} status={s.retrieval_status} />
          <div className="grid grid-cols-2 gap-2 mt-2">
            <StatCard icon={IndianRupee} label="Total Tips" value={`₹${s.total_tips || 0}`} iconColor="text-amber-500" sub="Placeholder" testId="stat-total-tips" />
            <StatCard icon={TrendingUp} label="Collection Rate" value={`${s.collection_rate || 0}%`} iconColor="text-cyan-500" sub="Placeholder" testId="stat-collection-rate" />
          </div>
        </div>

        {/* Section 2: Valet Leaderboard */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Trophy className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400" style={{ fontFamily: 'Barlow Condensed, sans-serif' }}>
              Valet Leaderboard
            </h2>
          </div>
          {leaderboard.length === 0 ? (
            <Card className="bg-zinc-900/50 border border-zinc-800 p-6 text-center">
              <Users className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
              <p className="text-sm text-zinc-500">No valet activity today</p>
            </Card>
          ) : (
            <Card className="bg-zinc-900/50 border border-zinc-800 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-zinc-800 hover:bg-transparent">
                    <TableHead className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">Valet</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold text-center">Parked</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold text-center">Retrieved</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold text-center">Avg Speed</TableHead>
                    <TableHead className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold text-right">Tips</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaderboard.map((v, idx) => (
                    <TableRow key={v.id} data-testid={`leaderboard-row-${idx}`} className="border-zinc-800/50">
                      <TableCell className="text-sm text-white font-medium py-3">
                        <div className="flex items-center gap-2">
                          {idx === 0 && <span className="text-amber-400 text-xs">1st</span>}
                          {idx === 1 && <span className="text-zinc-400 text-xs">2nd</span>}
                          {idx === 2 && <span className="text-orange-700 text-xs">3rd</span>}
                          {v.name}
                        </div>
                      </TableCell>
                      <TableCell className="text-center text-sm text-zinc-300">{v.cars_parked}</TableCell>
                      <TableCell className="text-center text-sm text-zinc-300">{v.cars_retrieved}</TableCell>
                      <TableCell className="text-center text-sm">
                        <span className={v.avg_retrieval_speed > 12 ? 'text-red-400' : v.avg_retrieval_speed > 8 ? 'text-amber-400' : 'text-emerald-400'}>
                          {v.avg_retrieval_speed > 0 ? `${v.avg_retrieval_speed}m` : '-'}
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-sm text-amber-400">₹{v.tips_earned}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </div>

        {/* Section 3: Efficiency Gaps & Bottlenecks */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400" style={{ fontFamily: 'Barlow Condensed, sans-serif' }}>
              Peak Hour Heatmap
            </h2>
          </div>
          <Card data-testid="hourly-chart-card" className="bg-zinc-900/50 border border-zinc-800 p-4">
            <HourlyChart data={hourly} />
          </Card>
        </div>

        {/* Wait-List Alert */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400" style={{ fontFamily: 'Barlow Condensed, sans-serif' }}>
              Wait-List Alert
            </h2>
            {waitlist.length > 0 && (
              <span className="ml-auto text-xs font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full">
                {waitlist.length} overdue
              </span>
            )}
          </div>
          {waitlist.length === 0 ? (
            <Card className="bg-zinc-900/50 border border-zinc-800 p-6 text-center">
              <Clock className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
              <p className="text-sm text-zinc-500">No overdue requests</p>
            </Card>
          ) : (
            <div className="space-y-2">
              {waitlist.map((w) => (
                <Card
                  key={w.ticket_id}
                  data-testid={`waitlist-item-${w.ticket_id}`}
                  className="bg-red-950/20 border border-red-900/40 p-3"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-sm font-medium text-white">{w.license_plate}</div>
                      <div className="text-xs text-zinc-400">{w.customer_phone}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-red-400">{w.wait_minutes}m</div>
                      <div className="text-[10px] uppercase text-zinc-500">{w.status.replace('_', ' ')}</div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Section 4: Financial & Tip Reconciliation */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold uppercase tracking-widest text-zinc-400" style={{ fontFamily: 'Barlow Condensed, sans-serif' }}>
              Financial Reconciliation
            </h2>
          </div>
          <Card data-testid="financial-card" className="bg-zinc-900/50 border border-zinc-800 p-4 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Pending Tips</div>
                <div className="text-lg font-bold text-amber-400">{fin.pending_tips_count || 0}</div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Paid Tips</div>
                <div className="text-lg font-bold text-emerald-400">₹{fin.paid_tips_total || 0}</div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Platform Fee</div>
                <div className="text-lg font-bold text-violet-400">₹{fin.platform_fees || 0}</div>
              </div>
            </div>

            {fin.payout && fin.payout.length > 0 && (
              <div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Valet Payout Summary</div>
                {fin.payout.map((p, i) => (
                  <div key={i} className="flex justify-between items-center py-1.5 border-t border-zinc-800/50">
                    <span className="text-sm text-zinc-300">{p.valet_name}</span>
                    <span className="text-sm text-emerald-400 font-medium">₹{p.payout_amount}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="text-[10px] text-zinc-600 italic">
              Tip data is a placeholder — will populate once payment integration is live.
            </div>

            <Button
              data-testid="export-csv-btn"
              onClick={handleExportCSV}
              variant="outline"
              className="w-full h-10 border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Download Payout CSV
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
}
