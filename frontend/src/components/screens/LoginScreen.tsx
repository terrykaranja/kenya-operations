import { useState } from 'react';
import { login } from '../../services/api';
import type { User } from '../../types/api';

interface Props {
  onLogin: (user: User) => void;
}

export function LoginScreen({ onLogin }: Props) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(username, password);
      onLogin(user);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-white">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl text-charcoal">SEZ Ledger</h1>
          <p className="mt-2 font-body text-sm text-charcoal/70">Kenya Operations Stock Ledger Automation</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-cool-steel/30 p-8 shadow-sm">
          <div className="mb-5">
            <label className="block font-body text-sm font-medium text-charcoal mb-1.5">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 border border-cool-steel/40 rounded-lg font-body text-sm focus:outline-none focus:ring-2 focus:ring-air-force-blue/50 focus:border-air-force-blue"
              required
              autoFocus
            />
          </div>
          <div className="mb-6">
            <label className="block font-body text-sm font-medium text-charcoal mb-1.5">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-cool-steel/40 rounded-lg font-body text-sm focus:outline-none focus:ring-2 focus:ring-air-force-blue/50 focus:border-air-force-blue"
              required
            />
          </div>

          {error && (
            <div className="mb-4 px-3 py-2 bg-oxblood/10 text-oxblood rounded-lg font-body text-sm">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
