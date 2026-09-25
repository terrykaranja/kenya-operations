import { useEffect, useState } from 'react';
import { getDashboard } from '../../services/api';
import type { DashboardStats } from '../../types/api';

interface Props {
  onNavigate: (page: string) => void;
}

export function DashboardScreen({ onNavigate }: Props) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard().then(setStats).catch(e => setError(e.message));
  }, []);

  if (error) return <div className="p-6 text-oxblood font-body">{error}</div>;
  if (!stats) return <div className="p-6 font-body text-charcoal/70">Loading dashboard...</div>;

  const cards = [
    { label: 'Import Lines', value: stats.total_import_lines, color: 'bg-air-force-blue' },
    { label: 'Export Lines', value: stats.total_export_lines, color: 'bg-dusty-olive' },
    { label: 'Open Balances', value: stats.open_balance_lines, color: 'bg-oxblood' },
    { label: 'Documents', value: stats.total_documents, color: 'bg-charcoal' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl text-charcoal">Dashboard</h2>
          <p className="font-body text-sm text-charcoal/60 mt-1">SEZ Stock Ledger Overview</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => onNavigate('upload-import')} className="px-4 py-2 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors">
            Upload Import
          </button>
          <button onClick={() => onNavigate('upload-export')} className="px-4 py-2 bg-air-force-blue hover:bg-air-force-blue/80 text-white rounded-lg font-body text-sm font-medium transition-colors">
            Upload Export
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map(c => (
          <div key={c.label} className="bg-white rounded-xl border border-cool-steel/30 p-5">
            <div className={`w-2 h-2 rounded-full ${c.color} mb-3`} />
            <p className="text-3xl font-light text-charcoal">{c.value.toLocaleString()}</p>
            <p className="font-body text-xs text-charcoal/60 mt-1 uppercase tracking-wider">{c.label}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-8">
        <button onClick={() => onNavigate('search')} className="bg-white rounded-xl border border-cool-steel/30 p-5 text-left hover:border-air-force-blue/50 transition-colors">
          <h3 className="text-lg text-charcoal">Search Ledger</h3>
          <p className="font-body text-sm text-charcoal/60 mt-1">Find import lines by entry number, HS code, description, or consignor</p>
        </button>
        <button onClick={() => onNavigate('download')} className="bg-white rounded-xl border border-cool-steel/30 p-5 text-left hover:border-air-force-blue/50 transition-colors">
          <h3 className="text-lg text-charcoal">Download Ledger</h3>
          <p className="font-body text-sm text-charcoal/60 mt-1">Export the complete stock ledger as a formatted Excel file</p>
        </button>
      </div>

      <div className="bg-white rounded-xl border border-cool-steel/30 p-5">
        <h3 className="text-lg text-charcoal mb-4">Recent Activity</h3>
        {stats.recent_activity.length === 0 ? (
          <p className="font-body text-sm text-charcoal/50">No recent activity</p>
        ) : (
          <div className="space-y-2">
            {stats.recent_activity.map(log => (
              <div key={log.id} className="flex items-center justify-between py-2 border-b border-cool-steel/20 last:border-0">
                <div className="font-body text-sm">
                  <span className="font-medium text-charcoal">{log.change_type}</span>
                  <span className="text-charcoal/60"> on {log.entity_type} #{log.entity_id}</span>
                </div>
                <span className="font-body text-xs text-charcoal/50">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
