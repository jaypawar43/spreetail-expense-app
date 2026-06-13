import { useState, useEffect } from 'react';
import { getSettlements, getConfig, updateConfig } from '../api/client';

/**
 * Balances — Shows who owes whom and simplified settlement plan.
 */
export default function Balances({ sessionId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exchangeRate, setExchangeRate] = useState(83);
  const [editingRate, setEditingRate] = useState(false);
  const [rateInput, setRateInput] = useState('83');

  useEffect(() => {
    if (sessionId) {
      setLoading(true);
      Promise.all([
        getSettlements(sessionId),
        getConfig(),
      ])
        .then(([settleData, configData]) => {
          setData(settleData);
          setExchangeRate(configData.usd_to_inr_rate);
          setRateInput(String(configData.usd_to_inr_rate));
        })
        .catch(() => setError('Failed to load balance data.'))
        .finally(() => setLoading(false));
    }
  }, [sessionId]);

  const handleRateSave = async () => {
    const rate = parseFloat(rateInput);
    if (isNaN(rate) || rate <= 0) return;

    try {
      await updateConfig({ usd_to_inr_rate: rate });
      setExchangeRate(rate);
      setEditingRate(false);

      // Refresh settlements with new rate
      const settleData = await getSettlements(sessionId);
      setData(settleData);
    } catch {
      setError('Failed to update exchange rate.');
    }
  };

  if (!sessionId) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <div className="text-5xl mb-4 opacity-40">💰</div>
        <h2 className="text-xl font-semibold text-white/50 mb-2">No Data Yet</h2>
        <p className="text-white/30 text-sm">Upload a CSV file to see balance calculations.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-20 animate-pulse-soft">
        <div className="text-4xl mb-4">⏳</div>
        <p className="text-white/40">Calculating balances...</p>
      </div>
    );
  }

  const balances = data?.balances || {};
  const settlements = data?.settlements || [];

  // Sort balances: creditors first, then debtors
  const sortedBalances = Object.entries(balances).sort((a, b) => b[1] - a[1]);

  const getBalanceColor = (amount) => {
    if (amount > 10) return 'text-emerald-400';
    if (amount < -10) return 'text-red-400';
    return 'text-white/50';
  };

  const getBalanceLabel = (amount) => {
    if (amount > 10) return 'is owed';
    if (amount < -10) return 'owes';
    return 'settled';
  };

  const personColors = {
    'Aisha': 'from-violet-500/20 to-purple-500/20 border-violet-500/20',
    'Rohan': 'from-blue-500/20 to-cyan-500/20 border-blue-500/20',
    'Priya': 'from-pink-500/20 to-rose-500/20 border-pink-500/20',
    'Meera': 'from-amber-500/20 to-yellow-500/20 border-amber-500/20',
    'Dev': 'from-emerald-500/20 to-green-500/20 border-emerald-500/20',
    'Sam': 'from-orange-500/20 to-red-500/20 border-orange-500/20',
  };

  const getPersonGradient = (name) => personColors[name] || 'from-gray-500/20 to-slate-500/20 border-gray-500/20';

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">
            <span className="gradient-text">Balances & Settlements</span>
          </h2>
          <p className="text-white/40 text-sm mt-1">
            All amounts converted to INR
          </p>
        </div>

        {/* Exchange Rate */}
        <div className="glass-card px-4 py-3 flex items-center gap-3">
          <span className="text-xs text-white/40">1 USD =</span>
          {editingRate ? (
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={rateInput}
                onChange={(e) => setRateInput(e.target.value)}
                className="input-field w-20 text-sm py-1 px-2"
                id="rate-input"
              />
              <span className="text-xs text-white/40">INR</span>
              <button onClick={handleRateSave} className="text-green-400 text-sm hover:text-green-300">✓</button>
              <button onClick={() => setEditingRate(false)} className="text-red-400 text-sm hover:text-red-300">✕</button>
            </div>
          ) : (
            <button
              onClick={() => setEditingRate(true)}
              className="text-brand-300 font-mono font-semibold hover:text-brand-200 transition-colors"
              id="edit-rate-btn"
            >
              ₹{exchangeRate}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 rounded-xl border border-red-500/20 bg-red-500/[0.06]">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Balance Cards */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-white/70 mb-4">Net Balances</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 animate-stagger">
          {sortedBalances.map(([name, amount]) => (
            <div
              key={name}
              className={`rounded-xl p-5 border bg-gradient-to-br ${getPersonGradient(name)} transition-all duration-200 hover:scale-[1.02]`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-bold text-white">{name}</span>
                <span className={`text-xs font-medium ${getBalanceColor(amount)} opacity-80`}>
                  {getBalanceLabel(amount)}
                </span>
              </div>
              <div className={`text-2xl font-bold font-mono ${getBalanceColor(amount)}`}>
                {amount >= 0 ? '+' : ''}₹{Math.abs(Math.round(amount)).toLocaleString('en-IN')}
              </div>
              <div className="mt-2 text-[10px] text-white/30 uppercase tracking-wider font-medium">
                Net balance
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Settlement Plan */}
      <div>
        <h3 className="text-lg font-semibold text-white/70 mb-4">
          Settlement Plan
          <span className="text-sm font-normal text-white/30 ml-2">
            ({settlements.length} transaction{settlements.length !== 1 ? 's' : ''} needed)
          </span>
        </h3>

        {settlements.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <div className="text-4xl mb-3">🎉</div>
            <p className="text-white/50">All settled! No transactions needed.</p>
          </div>
        ) : (
          <div className="space-y-3 animate-stagger">
            {settlements.map((settle, idx) => (
              <div key={idx} className="settlement-arrow group">
                {/* From */}
                <div className="flex items-center gap-2 min-w-[100px]">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                    style={{ background: 'rgba(255, 107, 107, 0.15)', color: '#ff6b6b' }}>
                    {settle.from[0]}
                  </div>
                  <span className="font-semibold text-white">{settle.from}</span>
                </div>

                {/* Arrow */}
                <div className="flex-1 flex items-center justify-center gap-2">
                  <div className="h-px flex-1 bg-gradient-to-r from-red-500/30 to-green-500/30" />
                  <div className="px-4 py-1.5 rounded-full text-sm font-bold font-mono whitespace-nowrap"
                    style={{ background: 'var(--gradient-brand)', color: 'white' }}>
                    ₹{Math.round(settle.amount).toLocaleString('en-IN')}
                  </div>
                  <div className="flex items-center text-white/20">
                    <span className="text-lg">→</span>
                  </div>
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent to-green-500/30" />
                </div>

                {/* To */}
                <div className="flex items-center gap-2 min-w-[100px] justify-end">
                  <span className="font-semibold text-white">{settle.to}</span>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                    style={{ background: 'rgba(81, 207, 102, 0.15)', color: '#51cf66' }}>
                    {settle.to[0]}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary */}
        {settlements.length > 0 && (
          <div className="mt-6 glass-card p-4">
            <h4 className="text-sm font-semibold text-white/50 mb-3">Summary</h4>
            <div className="space-y-1">
              {settlements.map((s, i) => (
                <p key={i} className="text-sm text-white/60">
                  <span className="text-red-400 font-medium">{s.from}</span>
                  {' owes '}
                  <span className="text-green-400 font-medium">{s.to}</span>
                  {' '}
                  <span className="font-mono font-bold text-white">
                    ₹{Math.round(s.amount).toLocaleString('en-IN')}
                  </span>
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
