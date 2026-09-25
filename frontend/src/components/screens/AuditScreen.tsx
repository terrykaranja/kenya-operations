import { useEffect, useState } from 'react';
import { getAuditLog, exportAuditCsv } from '../../services/api';
import type { AuditLogEntry } from '../../types/api';

interface Props {
  onNavigate: (page: string) => void;
  showToast: (msg: string, type: 'success' | 'error') => void;
}

export function AuditScreen({ onNavigate, showToast }: Props) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [filters, setFilters] = useState({ entity_type: '', change_type: '' });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await getAuditLog({ ...filters, page, page_size: 50 });
      setLogs(data);
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadLogs(); }, [page]);

  const handleExport = async () => {
    try {
      await exportAuditCsv(filters.entity_type || undefined);
      showToast('CSV downloaded', 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => onNavigate('dashboard')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Dashboard</button>
        <h2 className="text-2xl text-charcoal">Audit Log</h2>
      </div>

      <div className="bg-white rounded-xl border border-cool-steel/30 p-5 mb-6">
        <div className="flex items-center gap-4">
          <div>
            <label className="block font-body text-xs font-medium text-charcoal/70 mb-1">Entity Type</label>
            <select
              value={filters.entity_type}
              onChange={e => setFilters(f => ({ ...f, entity_type: e.target.value }))}
              className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm"
            >
              <option value="">All</option>
              <option value="import_line">Import Line</option>
              <option value="export_line">Export Line</option>
              <option value="user">User</option>
              <option value="allowed_unit">Unit</option>
              <option value="allowed_country">Country</option>
            </select>
          </div>
          <div>
            <label className="block font-body text-xs font-medium text-charcoal/70 mb-1">Change Type</label>
            <select
              value={filters.change_type}
              onChange={e => setFilters(f => ({ ...f, change_type: e.target.value }))}
              className="px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm"
            >
              <option value="">All</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
              <option value="override">Override</option>
            </select>
          </div>
          <div className="flex items-end gap-2 mt-auto">
            <button onClick={() => { setPage(1); loadLogs(); }} className="px-4 py-2 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm transition-colors">
              Filter
            </button>
            <button onClick={handleExport} className="px-4 py-2 bg-charcoal/10 hover:bg-charcoal/20 text-charcoal rounded-lg font-body text-sm transition-colors">
              Export CSV
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-cool-steel/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full font-body text-sm">
            <thead className="bg-cool-steel/10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">Timestamp</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">Entity</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">Change</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">Field</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">Old</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">New</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70">Source</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} className="border-t border-cool-steel/10">
                  <td className="px-4 py-2 text-charcoal/70 whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2">{log.entity_type} #{log.entity_id}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      log.change_type === 'create' ? 'bg-dusty-olive/10 text-dusty-olive' :
                      log.change_type === 'delete' ? 'bg-oxblood/10 text-oxblood' :
                      log.change_type === 'override' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-air-force-blue/10 text-air-force-blue'
                    }`}>{log.change_type}</span>
                  </td>
                  <td className="px-4 py-2 text-charcoal/70">{log.field_name || '-'}</td>
                  <td className="px-4 py-2 text-charcoal/70 max-w-32 truncate">{log.old_value || '-'}</td>
                  <td className="px-4 py-2 text-charcoal/70 max-w-32 truncate">{log.new_value || '-'}</td>
                  <td className="px-4 py-2 text-charcoal/70">{log.source}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-charcoal/50">{loading ? 'Loading...' : 'No audit entries'}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex justify-center gap-3 mt-4">
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1.5 border border-cool-steel/40 rounded font-body text-sm disabled:opacity-30">Prev</button>
        <span className="font-body text-sm text-charcoal/60 py-1.5">Page {page}</span>
        <button onClick={() => setPage(p => p + 1)} disabled={logs.length < 50} className="px-3 py-1.5 border border-cool-steel/40 rounded font-body text-sm disabled:opacity-30">Next</button>
      </div>
    </div>
  );
}
