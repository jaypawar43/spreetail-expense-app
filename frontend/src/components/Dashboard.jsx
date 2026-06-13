import { useState, useEffect, useCallback } from 'react';
import { getExpenses } from '../api/client';

/**
 * Dashboard — Expense table with filters by person, date range, currency, and search.
 */
export default function Dashboard({ sessionId }) {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);

  // Filters
  const [filters, setFilters] = useState({
    person: '',
    date_from: '',
    date_to: '',
    currency: '',
    search: '',
    settlement: '',
  });

  const fetchExpenses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page };
      if (sessionId) params.session = sessionId;
      if (filters.person) params.person = filters.person;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.currency) params.currency = filters.currency;
      if (filters.search) params.search = filters.search;
      if (filters.settlement) params.settlement = filters.settlement;

      const data = await getExpenses(params);
      setExpenses(data.results || data);
      setTotalCount(data.count || (data.results || data).length);
    } catch (err) {
      setError('Failed to load expenses. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [sessionId, filters, page]);

  useEffect(() => {
    fetchExpenses();
  }, [fetchExpenses]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({
      person: '',
      date_from: '',
      date_to: '',
      currency: '',
      search: '',
      settlement: '',
    });
    setPage(1);
  };

  const formatAmount = (amount, currency) => {
    const symbol = currency === 'USD' ? '$' : '₹';
    const num = parseFloat(amount);
    return `${symbol}${num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  if (!sessionId) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <div className="text-5xl mb-4 opacity-40">📊</div>
        <h2 className="text-xl font-semibold text-white/50 mb-2">No Data Yet</h2>
        <p className="text-white/30 text-sm">Upload a CSV file to view the expense dashboard.</p>
      </div>
    );
  }

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">
            <span className="gradient-text">Expense Dashboard</span>
          </h2>
          <p className="text-white/40 text-sm mt-1">
            {totalCount} expenses found
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Search */}
          <div className="col-span-2 md:col-span-1">
            <input
              type="text"
              placeholder="🔍 Search expenses..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              className="input-field text-sm"
              id="filter-search"
            />
          </div>

          {/* Person */}
          <select
            value={filters.person}
            onChange={(e) => handleFilterChange('person', e.target.value)}
            className="input-field text-sm"
            id="filter-person"
          >
            <option value="">All People</option>
            {['Aisha', 'Rohan', 'Priya', 'Meera', 'Dev', 'Sam'].map(name => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>

          {/* Date From */}
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => handleFilterChange('date_from', e.target.value)}
            className="input-field text-sm"
            id="filter-date-from"
            placeholder="From date"
          />

          {/* Date To */}
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => handleFilterChange('date_to', e.target.value)}
            className="input-field text-sm"
            id="filter-date-to"
            placeholder="To date"
          />

          {/* Currency */}
          <select
            value={filters.currency}
            onChange={(e) => handleFilterChange('currency', e.target.value)}
            className="input-field text-sm"
            id="filter-currency"
          >
            <option value="">All Currencies</option>
            <option value="INR">₹ INR</option>
            <option value="USD">$ USD</option>
          </select>

          {/* Clear Button */}
          <button
            onClick={clearFilters}
            className="btn-secondary text-sm"
            id="clear-filters-btn"
          >
            ✕ Clear
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 rounded-xl border border-red-500/20 bg-red-500/[0.06]">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="text-center py-12 animate-pulse-soft">
            <p className="text-white/40">Loading expenses...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Paid By</th>
                  <th className="text-right">Amount</th>
                  <th>Currency</th>
                  <th>Split</th>
                  <th>Split With</th>
                  <th>Notes</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {expenses.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="text-center py-8 text-white/30">
                      No expenses found.
                    </td>
                  </tr>
                ) : (
                  expenses.map((expense) => (
                    <tr
                      key={expense.id}
                      className={`${expense.is_settlement ? 'opacity-60' : ''} ${expense.is_flagged ? 'row-flagged' : ''}`}
                    >
                      <td className="font-mono text-white/40 text-xs">{expense.original_row}</td>
                      <td className="whitespace-nowrap text-sm">{formatDate(expense.date)}</td>
                      <td className="max-w-[200px]">
                        <span className="text-sm text-white/90 truncate block" title={expense.description}>
                          {expense.description}
                        </span>
                        {expense.category && (
                          <span className="text-[10px] text-white/30">{expense.category}</span>
                        )}
                      </td>
                      <td>
                        <span className="text-sm font-medium text-brand-300">
                          {expense.paid_by_name || '—'}
                        </span>
                      </td>
                      <td className={`text-right font-mono font-semibold text-sm ${
                        parseFloat(expense.amount) < 0 ? 'text-red-400' :
                        parseFloat(expense.amount) === 0 ? 'text-yellow-400' : 'text-white'
                      }`}>
                        {formatAmount(expense.amount, expense.currency)}
                      </td>
                      <td>
                        <span className={`text-xs font-mono ${expense.currency === 'USD' ? 'text-green-400' : 'text-white/50'}`}>
                          {expense.currency}
                        </span>
                      </td>
                      <td>
                        <span className="badge-blue text-[10px]">
                          {expense.split_type || (expense.is_settlement ? 'settlement' : '—')}
                        </span>
                      </td>
                      <td className="max-w-[180px]">
                        <span className="text-xs text-white/40 truncate block" title={expense.split_with_raw}>
                          {expense.split_with_raw || '—'}
                        </span>
                      </td>
                      <td className="max-w-[150px]">
                        <span className="text-xs text-white/30 italic truncate block" title={expense.notes}>
                          {expense.notes || '—'}
                        </span>
                      </td>
                      <td>
                        {expense.is_settlement && <span className="badge-purple text-[10px]">Settlement</span>}
                        {expense.is_flagged && <span className="badge-yellow text-[10px]">Flagged</span>}
                        {!expense.is_settlement && !expense.is_flagged && (
                          <span className="badge-green text-[10px]">OK</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalCount > 50 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary text-sm disabled:opacity-30"
          >
            ← Previous
          </button>
          <span className="px-4 py-2 text-sm text-white/40">
            Page {page} of {Math.ceil(totalCount / 50)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 50 >= totalCount}
            className="btn-secondary text-sm disabled:opacity-30"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
