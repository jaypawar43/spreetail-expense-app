import { useState, useEffect } from 'react';
import { getImportSession } from '../api/client';

/**
 * ImportReport — Shows anomaly report after CSV import.
 * Color-coded: red = skipped, yellow = flagged, green = auto-fixed
 */
export default function ImportReport({ session }) {
  const [reportData, setReportData] = useState(session);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (session?.id && !session.anomalies) {
      setLoading(true);
      getImportSession(session.id)
        .then(data => {
          setReportData(data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    } else if (session) {
      setReportData(session);
    }
  }, [session]);

  if (!session) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <div className="text-5xl mb-4 opacity-40">📋</div>
        <h2 className="text-xl font-semibold text-white/50 mb-2">No Import Yet</h2>
        <p className="text-white/30 text-sm">Upload a CSV file first to see the import report.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-20 animate-pulse-soft">
        <div className="text-4xl mb-4">⏳</div>
        <p className="text-white/40">Loading report...</p>
      </div>
    );
  }

  const anomalies = reportData?.anomalies || [];

  const filteredAnomalies = filter === 'all'
    ? anomalies
    : anomalies.filter(a => a.action_taken === filter);

  const getActionBadge = (action) => {
    switch (action) {
      case 'skipped': return <span className="badge-red">Skipped</span>;
      case 'flagged': return <span className="badge-yellow">Flagged</span>;
      case 'auto_fixed': return <span className="badge-green">Auto-Fixed</span>;
      case 'normalized': return <span className="badge-green">Normalized</span>;
      case 'imported_as_is': return <span className="badge-blue">Imported</span>;
      default: return <span className="badge-blue">{action}</span>;
    }
  };

  const getSeverityDot = (severity) => {
    const colors = {
      error: 'bg-red-500',
      warning: 'bg-yellow-500',
      info: 'bg-blue-400',
    };
    return <span className={`inline-block w-2 h-2 rounded-full ${colors[severity] || 'bg-gray-400'}`} />;
  };

  const getRowClass = (action) => {
    switch (action) {
      case 'skipped': return 'row-skipped';
      case 'flagged': return 'row-flagged';
      case 'auto_fixed':
      case 'normalized': return 'row-auto-fixed';
      default: return '';
    }
  };

  const stats = [
    { label: 'Total Rows', value: reportData?.total_rows || 0, icon: '📄', color: 'text-white' },
    { label: 'Imported', value: reportData?.imported_rows || 0, icon: '✅', color: 'text-emerald-400' },
    { label: 'Skipped', value: reportData?.skipped_rows || 0, icon: '🚫', color: 'text-red-400' },
    { label: 'Flagged', value: reportData?.flagged_rows || 0, icon: '⚠️', color: 'text-yellow-400' },
    { label: 'Auto-Fixed', value: reportData?.auto_fixed_rows || 0, icon: '🔧', color: 'text-green-400' },
    { label: 'Anomalies', value: anomalies.length, icon: '🔍', color: 'text-purple-400' },
  ];

  const actionCounts = anomalies.reduce((acc, a) => {
    acc[a.action_taken] = (acc[a.action_taken] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-1">
          <span className="gradient-text">Import Report</span>
        </h2>
        <p className="text-white/40 text-sm">
          File: <span className="font-mono text-brand-300">{reportData?.filename}</span>
          {' • '}
          {reportData?.uploaded_at && new Date(reportData.uploaded_at).toLocaleString('en-IN')}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8 animate-stagger">
        {stats.map(stat => (
          <div key={stat.label} className="glass-card p-4 text-center">
            <div className="text-2xl mb-1">{stat.icon}</div>
            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-[11px] text-white/40 font-medium uppercase tracking-wide mt-1">
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            filter === 'all' ? 'bg-brand-600/30 text-brand-300 border border-brand-500/30' : 'text-white/40 hover:text-white/60'
          }`}
          id="filter-all"
        >
          All ({anomalies.length})
        </button>
        {Object.entries(actionCounts).map(([action, count]) => (
          <button
            key={action}
            onClick={() => setFilter(action)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === action ? 'bg-brand-600/30 text-brand-300 border border-brand-500/30' : 'text-white/40 hover:text-white/60'
            }`}
            id={`filter-${action}`}
          >
            {action.replace('_', ' ')} ({count})
          </button>
        ))}
      </div>

      {/* Anomaly Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Row</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Description</th>
                <th>Action</th>
                <th>Original</th>
                <th>Fixed</th>
              </tr>
            </thead>
            <tbody>
              {filteredAnomalies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-white/30">
                    {anomalies.length === 0
                      ? '🎉 No anomalies found — clean data!'
                      : 'No anomalies match this filter.'}
                  </td>
                </tr>
              ) : (
                filteredAnomalies.map((anomaly, idx) => (
                  <tr key={anomaly.id || idx} className={getRowClass(anomaly.action_taken)}>
                    <td className="font-mono text-brand-300 font-semibold">
                      {anomaly.row_number || '—'}
                    </td>
                    <td>
                      <span className="badge-purple text-[10px]">
                        {anomaly.anomaly_type_display || anomaly.anomaly_type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <span className="flex items-center gap-1.5">
                        {getSeverityDot(anomaly.severity)}
                        <span className="text-xs text-white/50 capitalize">{anomaly.severity}</span>
                      </span>
                    </td>
                    <td className="max-w-xs">
                      <p className="text-sm text-white/80 truncate" title={anomaly.description}>
                        {anomaly.description}
                      </p>
                    </td>
                    <td>{getActionBadge(anomaly.action_taken)}</td>
                    <td className="max-w-[150px]">
                      <span className="text-xs text-white/40 font-mono truncate block" title={anomaly.original_value}>
                        {anomaly.original_value || '—'}
                      </span>
                    </td>
                    <td className="max-w-[150px]">
                      <span className="text-xs text-green-400/70 font-mono truncate block" title={anomaly.fixed_value}>
                        {anomaly.fixed_value || '—'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex gap-6 text-xs text-white/30">
        <span className="flex items-center gap-2">
          <span className="w-3 h-1 rounded bg-red-500 inline-block" /> Skipped
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-1 rounded bg-yellow-500 inline-block" /> Flagged
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-1 rounded bg-green-500 inline-block" /> Auto-Fixed / Normalized
        </span>
      </div>
    </div>
  );
}
