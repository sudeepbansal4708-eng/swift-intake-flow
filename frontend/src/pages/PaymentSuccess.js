import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card } from '../components/ui/card';
import { CheckCircle2 } from 'lucide-react';

export default function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id') || '';
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      data-testid="payment-success-page"
      className="min-h-screen w-full flex items-center justify-center px-6"
      style={{ background: '#0b0f17' }}
    >
      <Card
        data-testid="payment-success-card"
        className={`w-full max-w-md bg-zinc-900/70 backdrop-blur-md border border-zinc-800 p-10 text-center shadow-2xl transition-all duration-500 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}
      >
        <div className="flex justify-center mb-6">
          <div
            data-testid="payment-success-icon"
            className="w-20 h-20 rounded-full bg-emerald-500/15 border border-emerald-500/40 flex items-center justify-center"
          >
            <CheckCircle2 className="w-10 h-10 text-emerald-400" strokeWidth={1.8} />
          </div>
        </div>

        <div
          data-testid="payment-success-brand"
          className="text-xs uppercase tracking-[0.35em] text-amber-400/80 mb-3"
          style={{ fontFamily: 'Barlow Condensed, sans-serif' }}
        >
          Valet Guys
        </div>

        <h1
          data-testid="payment-success-title"
          className="text-3xl font-bold text-white mb-3 tracking-tight"
          style={{ fontFamily: 'Barlow Condensed, sans-serif' }}
        >
          Thank you for your tip!
        </h1>

        <p data-testid="payment-success-message" className="text-sm text-zinc-400 leading-relaxed mb-6">
          Your payment was successful. We&apos;ve passed the tip along to your valet — they appreciate it!
        </p>

        {orderId && (
          <div
            data-testid="payment-success-ref"
            className="text-[10px] text-zinc-600 uppercase tracking-widest border-t border-zinc-800 pt-4 mt-2"
          >
            Ref: {orderId}
          </div>
        )}

        <div
          data-testid="payment-success-drive"
          className="text-xs text-zinc-500 mt-6 italic"
        >
          Drive safe!
        </div>
      </Card>
    </div>
  );
}
