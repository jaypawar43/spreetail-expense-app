import { useState, useEffect } from 'react';
import { getPersons, createPerson, updatePerson } from '../api/client';

/**
 * PersonManager — View and manage roommates and guests.
 */
export default function PersonManager() {
  const [persons, setPersons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', is_permanent: false });
  const [saving, setSaving] = useState(false);

  const fetchPersons = async () => {
    setLoading(true);
    try {
      const data = await getPersons();
      setPersons(data.results || data);
    } catch {
      setError('Failed to load persons.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPersons();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    setSaving(true);
    try {
      await createPerson(formData);
      setFormData({ name: '', is_permanent: false });
      setShowForm(false);
      await fetchPersons();
    } catch (err) {
      setError(err.response?.data?.name?.[0] || 'Failed to create person.');
    } finally {
      setSaving(false);
    }
  };

  const handleTogglePermanent = async (person) => {
    try {
      await updatePerson(person.id, { is_permanent: !person.is_permanent });
      await fetchPersons();
    } catch {
      setError('Failed to update person.');
    }
  };

  const roommates = persons.filter(p => p.is_permanent);
  const guests = persons.filter(p => !p.is_permanent);

  const personEmojis = ['👤', '👩', '👨', '🧑', '👱', '🧔', '👩‍🦱', '👨‍🦰'];

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">
            <span className="gradient-text">People</span>
          </h2>
          <p className="text-white/40 text-sm mt-1">
            {roommates.length} roommate{roommates.length !== 1 ? 's' : ''}
            {' • '}
            {guests.length} guest{guests.length !== 1 ? 's' : ''}
          </p>
        </div>

        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary text-sm"
          id="add-person-btn"
        >
          + Add Person
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 rounded-xl border border-red-500/20 bg-red-500/[0.06]">
          <p className="text-red-400 text-sm flex items-center gap-2">
            ⚠️ {error}
            <button onClick={() => setError(null)} className="ml-auto text-white/30 hover:text-white/60">✕</button>
          </p>
        </div>
      )}

      {/* Add Person Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="glass-card p-5 mb-6 animate-slide-up">
          <h3 className="text-sm font-semibold text-white/60 mb-4">Add New Person</h3>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-xs text-white/40 mb-1 block">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="input-field"
                placeholder="Enter name"
                id="person-name-input"
                autoFocus
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer px-4 py-3 rounded-xl border border-white/[0.08] hover:border-white/[0.15] transition-colors">
              <input
                type="checkbox"
                checked={formData.is_permanent}
                onChange={(e) => setFormData(prev => ({ ...prev, is_permanent: e.target.checked }))}
                className="w-4 h-4 rounded border-white/20 bg-white/5 text-brand-500 focus:ring-brand-500"
                id="person-permanent-checkbox"
              />
              <span className="text-sm text-white/60">Permanent roommate</span>
            </label>
            <button
              type="submit"
              disabled={saving || !formData.name.trim()}
              className="btn-primary text-sm disabled:opacity-50"
              id="save-person-btn"
            >
              {saving ? '...' : 'Save'}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-center py-12 animate-pulse-soft">
          <p className="text-white/40">Loading people...</p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Roommates */}
          <div>
            <h3 className="text-lg font-semibold text-white/70 mb-4 flex items-center gap-2">
              🏠 Roommates
              <span className="badge-green text-[10px]">{roommates.length}</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-stagger">
              {roommates.map((person, idx) => (
                <div key={person.id} className="glass-card-hover p-5 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                    style={{ background: 'rgba(81, 207, 102, 0.1)' }}>
                    {personEmojis[idx % personEmojis.length]}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-white">{person.name}</h4>
                    <p className="text-xs text-white/30">
                      {person.expense_count || 0} expenses paid
                    </p>
                  </div>
                  <span className="badge-green text-[10px]">Roommate</span>
                </div>
              ))}
              {roommates.length === 0 && (
                <p className="text-white/30 text-sm col-span-full">No roommates yet.</p>
              )}
            </div>
          </div>

          {/* Guests */}
          <div>
            <h3 className="text-lg font-semibold text-white/70 mb-4 flex items-center gap-2">
              ✈️ Guests & Temporary
              <span className="badge-yellow text-[10px]">{guests.length}</span>
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 animate-stagger">
              {guests.map((person, idx) => (
                <div key={person.id} className="glass-card-hover p-5 flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                    style={{ background: 'rgba(255, 212, 59, 0.1)' }}>
                    {personEmojis[(idx + 4) % personEmojis.length]}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-white">{person.name}</h4>
                    <p className="text-xs text-white/30">
                      {person.expense_count || 0} expenses paid
                    </p>
                  </div>
                  <button
                    onClick={() => handleTogglePermanent(person)}
                    className="badge-yellow text-[10px] hover:bg-yellow-500/20 transition-colors cursor-pointer"
                    title="Click to promote to roommate"
                  >
                    Guest
                  </button>
                </div>
              ))}
              {guests.length === 0 && (
                <p className="text-white/30 text-sm col-span-full">No guests yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
