import { useState } from 'react';
import { confirmExport, getMatchCandidates, previewProration } from '../../services/api';
import type { ExtractionResponse, ImportLineSummary, ProrationPreview, ExtractedExportEntry } from '../../types/api';

interface Props {
  extraction: ExtractionResponse;
  onConfirmed: () => void;
  onNavigate: (page: string) => void;
  showToast: (msg: string, type: 'success' | 'error') => void;
}

const FIELDS: { key: keyof ExtractedExportEntry; label: string; type?: string }[] = [
  { key: 'customer_name', label: 'Customer Name' },
  { key: 'export_file_number', label: 'File Number' },
  { key: 'export_entry_date', label: 'Entry Date', type: 'date' },
  { key: 'export_entry_number', label: 'Entry Number' },
  { key: 'ppb_permit', label: 'PPB Permit' },
  { key: 'supplementary_units_exported', label: 'Supp. Units', type: 'number' },
  { key: 'unit', label: 'Unit' },
  { key: 'quantity_exported', label: 'Quantity Exported', type: 'number' },
  { key: 'customs_value_exported', label: 'Customs Value', type: 'number' },
  { key: 'bif_value_exported', label: 'BIF Value', type: 'number' },
];

export function ExportReviewScreen({ extraction, onConfirmed, onNavigate, showToast }: Props) {
  const [entries, setEntries] = useState(
    extraction.export_entries.map(e => {
      const row: Record<string, string> = {};
      for (const f of FIELDS) row[f.key] = e[f.key].value ?? '';
      return row;
    })
  );

  const [selectedImports, setSelectedImports] = useState<(number | null)[]>(
    extraction.export_entries.map(() => null)
  );
  const [candidates, setCandidates] = useState<ImportLineSummary[]>([]);
  const [prorations, setProrations] = useState<(ProrationPreview | null)[]>(
    extraction.export_entries.map(() => null)
  );
  const [activeIdx, setActiveIdx] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const updateField = (idx: number, field: string, value: string) => {
    setEntries(prev => prev.map((e, i) => i === idx ? { ...e, [field]: value } : e));
  };

  const findCandidates = async (idx: number) => {
    setActiveIdx(idx);
    setSearching(true);
    try {
      const entry = entries[idx];
      const results = await getMatchCandidates({
        description: entry.customer_name || undefined,
      });
      setCandidates(results);
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setSearching(false);
    }
  };

  const selectImport = async (entryIdx: number, importId: number) => {
    setSelectedImports(prev => prev.map((v, i) => i === entryIdx ? importId : v));
    setActiveIdx(null);
    const qty = Number(entries[entryIdx].quantity_exported);
    if (qty > 0) {
      try {
        const preview = await previewProration(importId, qty);
        setProrations(prev => prev.map((v, i) => i === entryIdx ? preview : v));
        // Auto-fill prorated values
        if (preview.prorated_customs_value) {
          updateField(entryIdx, 'customs_value_exported', String(preview.prorated_customs_value));
        }
        if (preview.prorated_bif_value) {
          updateField(entryIdx, 'bif_value_exported', String(preview.prorated_bif_value));
        }
      } catch { /* ignore preview errors */ }
    }
  };

  const handleConfirm = async () => {
    const missing = selectedImports.findIndex(v => v === null);
    if (missing >= 0) {
      showToast(`Item ${missing + 1}: no import line selected`, 'error');
      return;
    }

    setSubmitting(true);
    try {
      const payload = entries.map((e, i) => ({
        import_line_id: selectedImports[i],
        customer_name: e.customer_name || null,
        export_file_number: e.export_file_number || null,
        export_entry_date: e.export_entry_date || null,
        export_entry_number: e.export_entry_number || null,
        ppb_permit: e.ppb_permit || null,
        supplementary_units_exported: e.supplementary_units_exported ? Number(e.supplementary_units_exported) : null,
        unit: e.unit || null,
        quantity_exported: Number(e.quantity_exported) || 0,
        customs_value_exported: e.customs_value_exported ? Number(e.customs_value_exported) : null,
        bif_value_exported: e.bif_value_exported ? Number(e.bif_value_exported) : null,
      }));
      await confirmExport(payload, extraction.document_id);
      showToast(`${entries.length} export line(s) confirmed`, 'success');
      onConfirmed();
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => onNavigate('upload-export')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Back</button>
        <h2 className="text-2xl text-charcoal">Review Export & Match to Import</h2>
      </div>

      <div className="space-y-6">
        {entries.map((entry, idx) => (
          <div key={idx} className="bg-white rounded-xl border border-cool-steel/30 p-5">
            <h3 className="text-lg text-charcoal mb-4">Export Item {idx + 1}</h3>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
              {FIELDS.map(f => (
                <div key={f.key}>
                  <label className="block font-body text-xs font-medium text-charcoal/70 mb-1">{f.label}</label>
                  <input
                    type={f.type || 'text'}
                    value={entry[f.key]}
                    onChange={e => updateField(idx, f.key, e.target.value)}
                    className="w-full px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm"
                  />
                </div>
              ))}
            </div>

            {/* Import line matching */}
            <div className="border-t border-cool-steel/20 pt-4 mt-4">
              <div className="flex items-center gap-3 mb-3">
                <span className="font-body text-sm font-medium text-charcoal">Matched Import Line:</span>
                {selectedImports[idx] ? (
                  <span className="font-body text-sm text-dusty-olive">#{selectedImports[idx]}</span>
                ) : (
                  <span className="font-body text-sm text-oxblood">Not selected</span>
                )}
                <button
                  onClick={() => findCandidates(idx)}
                  className="px-3 py-1 bg-air-force-blue/10 hover:bg-air-force-blue/20 text-air-force-blue rounded font-body text-xs transition-colors"
                >
                  {searching && activeIdx === idx ? 'Searching...' : 'Find Matches'}
                </button>
              </div>

              {activeIdx === idx && candidates.length > 0 && (
                <div className="bg-brand-white rounded-lg border border-cool-steel/30 max-h-48 overflow-y-auto">
                  {candidates.map(c => (
                    <button
                      key={c.id}
                      onClick={() => selectImport(idx, c.id)}
                      className="w-full text-left px-4 py-2 hover:bg-air-force-blue/5 border-b border-cool-steel/10 last:border-0"
                    >
                      <div className="font-body text-sm">
                        <span className="font-medium">#{c.id}</span> {c.description?.substring(0, 60)}
                      </div>
                      <div className="font-body text-xs text-charcoal/60">
                        HS: {c.hs_code} | Bal: {c.balance_quantity?.toLocaleString()} {c.unit} | {c.consignor_exporter?.substring(0, 40)}
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {prorations[idx] && (
                <div className={`mt-3 p-3 rounded-lg font-body text-sm ${prorations[idx]!.overdraft ? 'bg-oxblood/10 text-oxblood' : 'bg-dusty-olive/10 text-charcoal'}`}>
                  <p>Prorated Customs: KES {prorations[idx]!.prorated_customs_value.toLocaleString()}</p>
                  <p>Prorated BIF: KES {prorations[idx]!.prorated_bif_value.toLocaleString()}</p>
                  <p>Remaining Qty: {prorations[idx]!.remaining_quantity.toLocaleString()}</p>
                  {prorations[idx]!.overdraft && (
                    <p className="font-medium mt-1">{prorations[idx]!.overdraft_message}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 mt-6">
        <div className="flex-1" />
        <button onClick={() => onNavigate('dashboard')} className="px-4 py-2.5 border border-cool-steel/40 rounded-lg font-body text-sm text-charcoal hover:bg-cool-steel/10 transition-colors">
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          disabled={submitting || entries.length === 0}
          className="px-6 py-2.5 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
        >
          {submitting ? 'Confirming...' : `Confirm ${entries.length} Export(s)`}
        </button>
      </div>
    </div>
  );
}
