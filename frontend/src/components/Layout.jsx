import { useState, useEffect } from 'react';

/**
 * Layout — Main app shell with sidebar navigation and content area.
 */
export default function Layout({ tabs, activeTab, onTabChange, children }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* ─── Top Bar ─────────────────────────────────────── */}
      <header className="border-b border-white/[0.06] px-6 py-4 flex items-center justify-between"
        style={{ background: 'rgba(19, 20, 31, 0.8)', backdropFilter: 'blur(12px)' }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
            style={{ background: 'var(--gradient-brand)' }}>
            💸
          </div>
          <div>
            <h1 className="text-lg font-bold gradient-text">Expense Splitter</h1>
            <p className="text-[11px] text-white/30 font-medium tracking-wide">SMART SHARED EXPENSE MANAGEMENT</p>
          </div>
        </div>
        <div className="text-xs text-white/30 font-mono">
          {time.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
        </div>
      </header>

      {/* ─── Tab Navigation ──────────────────────────────── */}
      <nav className="border-b border-white/[0.06] px-6"
        style={{ background: 'rgba(19, 20, 31, 0.5)' }}>
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map((tab, index) => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
              className={`
                relative flex items-center gap-2 px-5 py-3.5 text-sm font-medium
                transition-all duration-200 rounded-t-lg whitespace-nowrap
                ${activeTab === tab.id
                  ? 'text-white border-b-2 border-brand-500'
                  : 'text-white/40 hover:text-white/70 border-b-2 border-transparent'
                }
              `}
              style={{
                animationDelay: `${index * 50}ms`,
              }}
            >
              <span className="text-base">{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.badge > 0 && (
                <span className="ml-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse-soft">
                  {tab.badge}
                </span>
              )}
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                  style={{ background: 'var(--gradient-brand)' }} />
              )}
            </button>
          ))}
        </div>
      </nav>

      {/* ─── Content Area ────────────────────────────────── */}
      <main className="flex-1 p-6 lg:p-8 max-w-[1400px] mx-auto w-full">
        <div className="animate-fade-in">
          {children}
        </div>
      </main>

      {/* ─── Footer ──────────────────────────────────────── */}
      <footer className="border-t border-white/[0.04] px-6 py-3 text-center">
        <p className="text-[11px] text-white/20">
          Expense Splitter • Built with Django REST Framework + React • Spreetail Assignment
        </p>
      </footer>
    </div>
  );
}
