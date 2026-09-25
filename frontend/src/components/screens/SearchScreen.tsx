import { useState } from 'react';
import { getImportLineDetail, searchImportLines, deleteExport } from '../../services/api';
import type { ImportLine, ImportLineSummary } from '../../types/api';

interface Props {
  onNavigate: (page: string) => void;
  showToast: (msg: string, type: 'success' | 'error') => void;
}

export function SearchScreen({ onNavigate, showToast }: Props) {
  const [filters, setFilters] = useState({
    entry_number: '',
    file_number: '',
    description: '',
    consignor: '',
    hs_code: '',
    country: '',
    open_balance_only: false,
  });
  const [results, setResults] = useState<ImportLineSummary[]>([]);
  const [detail, setDetail] = useState<ImportLine | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    setDetail(null);
    try {
      const data = await searchImportLines(filters);
      setResults(data);
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (id: number) => {
    try {
      const data = await getImportLineDetail(id);
      setDetail(data);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  const handleDeleteExport = async (exportId: number) => {
    try {
      await deleteExport(exportId);
      showToast('Export deleted and balance restored', 'success');
      if (detail) handleViewDetail(detail.id);
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => onNavigate('dashboard')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Dashboard</button>
        <h2 className="text-2xl text-charcoal">Search Ledger</h2>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-cool-steel/30 p-5 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
          {[
            { key: 'entry_number', label: 'Entry Number' },
            { key: 'file_number', label: 'File Number' },
            { key: 'description', label: 'Description' },
            { key: 'consignor', label: 'Consignor' },
            { key: 'hs_code', label: 'HS Code' },
            { key: 'country', label: 'Country' },
          ].map(f => (
            <div key={f.key}>
              <label className="block font-body text-xs font-medium text-charcoal/70 mb-1">{f.label}</label>
              <input
                type="text"
                value={(filters as any)[f.key]}
                onChange={e => setFilters(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="w-full px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm"
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
              />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 font-body text-sm text-charcoal">
            <input
              type="checkbox"
              checked={filters.open_balance_only}
              onChange={e => setFilters(prev => ({ ...prev, open_balance_only: e.target.checked }))}
              className="rounded"
            />
            Open balance only
          </label>
          <div className="flex-1" />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-5 py-2 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-white rounded-xl border border-cool-steel/30 overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table className="w-full font-body text-sm">
              <thead className="bg-cool-steel/10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70 uppercase">ID</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70 uppercase">Entry #</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70 uppercase">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-charcoal/70 uppercase">HS Code</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-charcoal/70 uppercase">Qty Imported</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-charcoal/70 uppercase">Balance Qty</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-charcoal/70 uppercase">Balance Value</th>
                </tr>
              </thead>
              <tbody>
                {results.map(r => (
                  <tr
                    key={r.id}
                    onClick={() => handleViewDetail(r.id)}
                    className="border-t border-cool-steel/10 hover:bg-air-force-blue/5 cursor-pointer"
                  >
                    <td className="px-4 py-3 text-charcoal">{r.id}</td>
                    <td className="px-4 py-3 text-charcoal">{r.import_entry_number || '-'}</td>
                    <td className="px-4 py-3 text-charcoal max-w-xs truncate">{r.description || '-'}</td>
                    <td className="px-4 py-3 text-charcoal">{r.hs_code || '-'}</td>
                    <td className="px-4 py-3 text-right text-charcoal">{r.quantity_imported?.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={r.balance_quantity > 0 ? 'text-dusty-olive font-medium' : 'text-charcoal/50'}>
                        {r.balance_quantity?.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-charcoal">{r.balance_customs_value?.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {results.length === 0 && !loading && (
        <p className="font-body text-sm text-charcoal/50 text-center py-8">Run a search to see results</p>
      )}

      {/* Detail view */}
      {detail && (
        <div className="bg-white rounded-xl border border-cool-steel/30 p-5">
          <h3 className="text-lg text-charcoal mb-4">Import Line #{detail.id}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[
              ['Consignor', detail.consignor_exporter],
              ['Description', detail.description],
              ['File #', detail.import_file_number],
              ['Entry Date', detail.import_entry_date],
              ['Entry #', detail.import_entry_number],
              ['HS Code', detail.hs_code],
              ['Country', detail.country],
              ['Unit', detail.unit],
              ['Qty Imported', detail.quantity_imported?.toLocaleString()],
              ['Customs Value', `KES ${detail.customs_value_kes?.toLocaleString()}`],
              ['BIF Value', detail.bif_value_kes ? `KES ${detail.bif_value_kes.toLocaleString()}` : '-'],
              ['Balance Qty', detail.balance_quantity?.toLocaleString()],
              ['Balance Customs', `KES ${detail.balance_customs_value?.toLocaleString()}`],
              ['Balance BIF', `KES ${detail.balance_bif_value?.toLocaleString()}`],
            ].map(([label, val]) => (
              <div key={label as string}>
                <p className="font-body text-xs text-charcoal/60 uppercase">{label}</p>
                <p className="font-body text-sm text-charcoal mt-0.5">{val || '-'}</p>
              </div>
            ))}
          </div>

          {detail.export_lines.length > 0 && (
            <>
              <h4 className="text-base text-charcoal mb-3 border-t border-cool-steel/20 pt-4">Export History</h4>
              <div className="overflow-x-auto">
                <table className="w-full font-body text-sm">
                  <thead className="bg-cool-steel/10">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs">ID</th>
                      <th className="px-3 py-2 text-left text-xs">Customer</th>
                      <th className="px-3 py-2 text-left text-xs">Entry #</th>
                      <th className="px-3 py-2 text-right text-xs">Qty</th>
                      <th className="px-3 py-2 text-right text-xs">Customs</th>
                      <th className="px-3 py-2 text-right text-xs">BIF</th>
                      <th className="px-3 py-2 text-xs"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.export_lines.map(ex => (
                      <tr key={ex.id} className="border-t border-cool-steel/10">
                        <td className="px-3 py-2">{ex.id}</td>
                        <td className="px-3 py-2 max-w-xs truncate">{ex.customer_name || '-'}</td>
                        <td className="px-3 py-2">{ex.export_entry_number || '-'}</td>
                        <td className="px-3 py-2 text-right">{ex.quantity_exported?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{ex.customs_value_exported?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right">{ex.bif_value_exported?.toLocaleString()}</td>
                        <td className="px-3 py-2">
                          <button
                            onClick={() => handleDeleteExport(ex.id)}
                            className="text-oxblood hover:underline text-xs"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
