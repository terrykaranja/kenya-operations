import { useState } from 'react';
import { confirmImport } from '../../services/api';
import type { ExtractedImportEntry, ExtractionResponse } from '../../types/api';

interface Props {
  extraction: ExtractionResponse;
  onConfirmed: () => void;
  onNavigate: (page: string) => void;
  showToast: (msg: string, type: 'success' | 'error') => void;
}

const FIELDS: { key: keyof ExtractedImportEntry; label: string; type?: string }[] = [
  { key: 'consignor_exporter', label: 'Consignor / Exporter' },
  { key: 'description', label: 'Description' },
  { key: 'import_file_number', label: 'File Number' },
  { key: 'import_entry_date', label: 'Entry Date', type: 'date' },
  { key: 'import_entry_number', label: 'Entry Number' },
  { key: 'hs_code', label: 'HS Code' },
  { key: 'country', label: 'Country' },
  { key: 'supplementary_units', label: 'Supp. Units', type: 'number' },
  { key: 'unit', label: 'Unit' },
  { key: 'quantity_imported', label: 'Quantity Imported', type: 'number' },
  { key: 'customs_value_kes', label: 'Customs Value (KES)', type: 'number' },
  { key: 'bif_value_kes', label: 'BIF Value (KES)', type: 'number' },
];

function confidenceColor(c: number): string {
  if (c >= 0.8) return '';
  if (c >= 0.5) return 'ring-2 ring-yellow-400';
  return 'ring-2 ring-oxblood';
}

export function ImportReviewScreen({ extraction, onConfirmed, onNavigate, showToast }: Props) {
  const [entries, setEntries] = useState<Record<string, string>[]>(
    extraction.import_entries.map(e => {
      const row: Record<string, string> = {};
      for (const f of FIELDS) {
        row[f.key] = e[f.key].value ?? '';
      }
      return row;
    })
  );
  const [submitting, setSubmitting] = useState(false);

  const updateField = (idx: number, field: string, value: string) => {
    setEntries(prev => prev.map((e, i) => i === idx ? { ...e, [field]: value } : e));
  };

  const addRow = () => {
    const empty: Record<string, string> = {};
    for (const f of FIELDS) empty[f.key] = '';
    setEntries(prev => [...prev, empty]);
  };

  const removeRow = (idx: number) => {
    setEntries(prev => prev.filter((_, i) => i !== idx));
  };

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      const payload = entries.map(e => ({
        consignor_exporter: e.consignor_exporter || null,
        description: e.description || null,
        import_file_number: e.import_file_number || null,
        import_entry_date: e.import_entry_date || null,
        import_entry_number: e.import_entry_number || null,
        hs_code: e.hs_code || null,
        country: e.country || null,
        supplementary_units: e.supplementary_units ? Number(e.supplementary_units) : null,
        unit: e.unit || null,
        quantity_imported: Number(e.quantity_imported) || 0,
        customs_value_kes: Number(e.customs_value_kes) || 0,
        bif_value_kes: e.bif_value_kes ? Number(e.bif_value_kes) : null,
      }));
      await confirmImport(payload, extraction.document_id);
      showToast(`${entries.length} import line(s) confirmed`, 'success');
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
        <button onClick={() => onNavigate('upload-import')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Back</button>
        <h2 className="text-2xl text-charcoal">Review Extracted Import Data</h2>
      </div>

      <p className="font-body text-sm text-charcoal/60 mb-4">
        Review and correct the extracted data below. Fields with low confidence are highlighted.
        <span className="inline-block w-3 h-3 ring-2 ring-yellow-400 rounded ml-2 align-middle" /> Medium
        <span className="inline-block w-3 h-3 ring-2 ring-oxblood rounded ml-2 align-middle" /> Low
      </p>

      <div className="space-y-6">
        {entries.map((entry, idx) => (
          <div key={idx} className="bg-white rounded-xl border border-cool-steel/30 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg text-charcoal">Item {idx + 1}</h3>
              {entries.length > 1 && (
                <button onClick={() => removeRow(idx)} className="font-body text-sm text-oxblood hover:underline">Remove</button>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {FIELDS.map(f => {
                const extracted = extraction.import_entries[idx];
                const conf = extracted ? extracted[f.key].confidence : 1;
                return (
                  <div key={f.key}>
                    <label className="block font-body text-xs font-medium text-charcoal/70 mb-1">{f.label}</label>
                    <input
                      type={f.type || 'text'}
                      value={entry[f.key]}
                      onChange={e => updateField(idx, f.key, e.target.value)}
                      className={`w-full px-3 py-2 border border-cool-steel/40 rounded-lg font-body text-sm ${confidenceColor(conf)}`}
                      title={extracted ? `Source: ${extracted[f.key].source_text || 'N/A'} | Confidence: ${(conf * 100).toFixed(0)}%` : ''}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 mt-6">
        <button onClick={addRow} className="px-4 py-2.5 bg-charcoal/10 hover:bg-charcoal/20 rounded-lg font-body text-sm text-charcoal transition-colors">
          + Add Item
        </button>
        <div className="flex-1" />
        <button onClick={() => onNavigate('dashboard')} className="px-4 py-2.5 border border-cool-steel/40 rounded-lg font-body text-sm text-charcoal hover:bg-cool-steel/10 transition-colors">
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          disabled={submitting || entries.length === 0}
          className="px-6 py-2.5 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
        >
          {submitting ? 'Confirming...' : `Confirm ${entries.length} Item(s)`}
        </button>
      </div>
    </div>
  );
}
