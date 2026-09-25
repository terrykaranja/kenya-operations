import { useEffect, useState } from 'react';
import {
  listUsers, createUser, updateUser, deleteUser,
  listUnits, createUnit,
  listCountries, createCountry,
} from '../../services/api';
import type { User, AllowedUnit, AllowedCountry } from '../../types/api';

interface Props {
  currentUser: User;
  onNavigate: (page: string) => void;
  showToast: (msg: string, type: 'success' | 'error') => void;
}

export function AdminScreen({ currentUser, onNavigate, showToast }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [units, setUnits] = useState<AllowedUnit[]>([]);
  const [countries, setCountries] = useState<AllowedCountry[]>([]);
  const [tab, setTab] = useState<'users' | 'units' | 'countries'>('users');

  // Form states
  const [newUser, setNewUser] = useState({ username: '', password: '', is_admin: false });
  const [newUnit, setNewUnit] = useState({ code: '', description: '' });
  const [newCountry, setNewCountry] = useState({ code: '', name: '' });

  useEffect(() => {
    listUsers().then(setUsers).catch(e => showToast(e.message, 'error'));
    listUnits().then(setUnits).catch(e => showToast(e.message, 'error'));
    listCountries().then(setCountries).catch(e => showToast(e.message, 'error'));
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createUser(newUser);
      setNewUser({ username: '', password: '', is_admin: false });
      const updated = await listUsers();
      setUsers(updated);
      showToast('User created', 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleToggleAdmin = async (user: User) => {
    try {
      await updateUser(user.id, { is_admin: !user.is_admin });
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, is_admin: !u.is_admin } : u));
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u));
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteUser = async (user: User) => {
    try {
      await deleteUser(user.id);
      setUsers(prev => prev.filter(u => u.id !== user.id));
      showToast('User deleted', 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleCreateUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createUnit(newUnit);
      setNewUnit({ code: '', description: '' });
      setUnits(await listUnits());
      showToast('Unit added', 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleCreateCountry = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createCountry(newCountry);
      setNewCountry({ code: '', name: '' });
      setCountries(await listCountries());
      showToast('Country added', 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const tabs = [
    { key: 'users' as const, label: 'Users' },
    { key: 'units' as const, label: 'Units' },
    { key: 'countries' as const, label: 'Countries' },
  ];

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => onNavigate('dashboard')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Dashboard</button>
        <h2 className="text-2xl text-charcoal">Admin Panel</h2>
      </div>

      <div className="flex gap-1 mb-6">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg font-body text-sm transition-colors ${
              tab === t.key ? 'bg-oxblood text-white' : 'bg-cool-steel/10 text-charcoal hover:bg-cool-steel/20'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Users tab */}
      {tab === 'users' && (
        <div>
          <form onSubmit={handleCreateUser} className="bg-white rounded-xl border border-cool-steel/30 p-5 mb-6">
            <h3 className="text-base text-charcoal mb-3">Create User</h3>
            <div className="flex items-end gap-3">
              <div>
                <label className="block font-body text-xs text-charcoal/70 mb-1">Username</label>
                <input value={newUser.username} onChange={e => setNewUser(u => ({ ...u, username: e.target.value }))} required className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm" />
              </div>
              <div>
                <label className="block font-body text-xs text-charcoal/70 mb-1">Password</label>
                <input type="password" value={newUser.password} onChange={e => setNewUser(u => ({ ...u, password: e.target.value }))} required className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm" />
              </div>
              <label className="flex items-center gap-2 font-body text-sm pb-2">
                <input type="checkbox" checked={newUser.is_admin} onChange={e => setNewUser(u => ({ ...u, is_admin: e.target.checked }))} />
                Admin
              </label>
              <button type="submit" className="px-4 py-2 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm transition-colors">Create</button>
            </div>
          </form>

          <div className="bg-white rounded-xl border border-cool-steel/30 overflow-hidden">
            <table className="w-full font-body text-sm">
              <thead className="bg-cool-steel/10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs">ID</th>
                  <th className="px-4 py-3 text-left text-xs">Username</th>
                  <th className="px-4 py-3 text-center text-xs">Admin</th>
                  <th className="px-4 py-3 text-center text-xs">Active</th>
                  <th className="px-4 py-3 text-left text-xs">Created</th>
                  <th className="px-4 py-3 text-xs"></th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className="border-t border-cool-steel/10">
                    <td className="px-4 py-2">{u.id}</td>
                    <td className="px-4 py-2 font-medium">{u.username}</td>
                    <td className="px-4 py-2 text-center">
                      <button onClick={() => handleToggleAdmin(u)} className={`px-2 py-0.5 rounded text-xs ${u.is_admin ? 'bg-oxblood/10 text-oxblood' : 'bg-cool-steel/10 text-charcoal/50'}`}>
                        {u.is_admin ? 'Yes' : 'No'}
                      </button>
                    </td>
                    <td className="px-4 py-2 text-center">
                      <button onClick={() => handleToggleActive(u)} className={`px-2 py-0.5 rounded text-xs ${u.is_active ? 'bg-dusty-olive/10 text-dusty-olive' : 'bg-oxblood/10 text-oxblood'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </button>
                    </td>
                    <td className="px-4 py-2 text-charcoal/60">{new Date(u.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-2">
                      {u.id !== currentUser.id && (
                        <button onClick={() => handleDeleteUser(u)} className="text-oxblood hover:underline text-xs">Delete</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Units tab */}
      {tab === 'units' && (
        <div>
          <form onSubmit={handleCreateUnit} className="bg-white rounded-xl border border-cool-steel/30 p-5 mb-6">
            <h3 className="text-base text-charcoal mb-3">Add Unit</h3>
            <div className="flex items-end gap-3">
              <div>
                <label className="block font-body text-xs text-charcoal/70 mb-1">Code</label>
                <input value={newUnit.code} onChange={e => setNewUnit(u => ({ ...u, code: e.target.value.toUpperCase() }))} required placeholder="KG" className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm w-24" />
              </div>
              <div>
                <label className="block font-body text-xs text-charcoal/70 mb-1">Description</label>
                <input value={newUnit.description} onChange={e => setNewUnit(u => ({ ...u, description: e.target.value }))} placeholder="Kilograms" className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm" />
              </div>
              <button type="submit" className="px-4 py-2 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm transition-colors">Add</button>
            </div>
          </form>
          <div className="bg-white rounded-xl border border-cool-steel/30 p-5">
            <div className="flex flex-wrap gap-2">
              {units.map(u => (
                <span key={u.id} className="px-3 py-1.5 bg-cool-steel/10 rounded-lg font-body text-sm">
                  <span className="font-medium">{u.code}</span>
                  {u.description && <span className="text-charcoal/60"> - {u.description}</span>}
                </span>
              ))}
              {units.length === 0 && <p className="font-body text-sm text-charcoal/50">No units configured</p>}
            </div>
          </div>
        </div>
      )}

      {/* Countries tab */}
      {tab === 'countries' && (
        <div>
          <form onSubmit={handleCreateCountry} className="bg-white rounded-xl border border-cool-steel/30 p-5 mb-6">
            <h3 className="text-base text-charcoal mb-3">Add Country</h3>
            <div className="flex items-end gap-3">
              <div>
                <label className="block font-body text-xs text-charcoal/70 mb-1">Code (ISO)</label>
                <input value={newCountry.code} onChange={e => setNewCountry(c => ({ ...c, code: e.target.value.toUpperCase() }))} required maxLength={2} placeholder="KE" className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm w-20" />
              </div>
              <div>
                <label className="block font-body text-xs text-charcoal/70 mb-1">Name</label>
                <input value={newCountry.name} onChange={e => setNewCountry(c => ({ ...c, name: e.target.value }))} required placeholder="Kenya" className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm" />
              </div>
              <button type="submit" className="px-4 py-2 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm transition-colors">Add</button>
            </div>
          </form>
          <div className="bg-white rounded-xl border border-cool-steel/30 p-5">
            <div className="flex flex-wrap gap-2">
              {countries.map(c => (
                <span key={c.id} className="px-3 py-1.5 bg-cool-steel/10 rounded-lg font-body text-sm">
                  <span className="font-medium">{c.code}</span> - {c.name}
                </span>
              ))}
              {countries.length === 0 && <p className="font-body text-sm text-charcoal/50">No countries configured</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
