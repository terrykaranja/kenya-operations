import { useState } from 'react';
import { downloadLedger, runLegacyImport } from '../../services/api';
import type { LegacyImportResult } from '../../types/api';

interface Props {
  isAdmin: boolean;
  onNavigate: (page: string) => void;
  showToast: (msg: string, type: 'success' | 'error') => void;
}

export function DownloadScreen({ isAdmin, onNavigate, showToast }: Props) {
  const [style, setStyle] = useState<'blank_continuation' | 'fully_populated'>('blank_continuation');
  const [downloading, setDownloading] = useState(false);
  const [importingLegacy, setImportingLegacy] = useState(false);
  const [legacyResult, setLegacyResult] = useState<LegacyImportResult | null>(null);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadLedger(style);
      showToast('Ledger downloaded', 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setDownloading(false);
    }
  };

  const handleLegacyImport = async () => {
    setImportingLegacy(true);
    setLegacyResult(null);
    try {
      const result = await runLegacyImport();
      setLegacyResult(result);
      showToast(`Legacy import complete: ${result.import_lines_created} imports, ${result.export_lines_created} exports`, 'success');
    } catch (err: any) {
      showToast(err.message, 'error');
    } finally {
      setImportingLegacy(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => onNavigate('dashboard')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Dashboard</button>
        <h2 className="text-2xl text-charcoal">Download & Data Management</h2>
      </div>

      {/* Download section */}
      <div className="bg-white rounded-xl border border-cool-steel/30 p-6 mb-6">
        <h3 className="text-lg text-charcoal mb-4">Download Stock Ledger</h3>
        <p className="font-body text-sm text-charcoal/70 mb-4">
          Generate and download the complete SEZ stock ledger as a formatted Excel file with all formulas.
        </p>

        <div className="flex items-center gap-6 mb-6">
          <label className="flex items-center gap-2 font-body text-sm text-charcoal cursor-pointer">
            <input
              type="radio"
              name="style"
              checked={style === 'blank_continuation'}
              onChange={() => setStyle('blank_continuation')}
              className="accent-oxblood"
            />
            Blank continuation rows (legacy format)
          </label>
          <label className="flex items-center gap-2 font-body text-sm text-charcoal cursor-pointer">
            <input
              type="radio"
              name="style"
              checked={style === 'fully_populated'}
              onChange={() => setStyle('fully_populated')}
              className="accent-oxblood"
            />
            Fully populated rows
          </label>
        </div>

        <button
          onClick={handleDownload}
          disabled={downloading}
          className="px-6 py-2.5 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
        >
          {downloading ? 'Generating...' : 'Download Excel'}
        </button>
      </div>

      {/* Legacy import section */}
      {isAdmin && (
        <div className="bg-white rounded-xl border border-cool-steel/30 p-6">
          <h3 className="text-lg text-charcoal mb-4">Legacy Data Import</h3>
          <p className="font-body text-sm text-charcoal/70 mb-4">
            Import data from the original Excel ledger file (Seza_Stock_Ledger_Hackathon.xlsx).
            This creates import and export lines from the legacy data. Admin only.
          </p>

          <button
            onClick={handleLegacyImport}
            disabled={importingLegacy}
            className="px-6 py-2.5 bg-charcoal hover:bg-charcoal/80 text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
          >
            {importingLegacy ? 'Importing...' : 'Import Legacy Data'}
          </button>

          {legacyResult && (
            <div className="mt-4 p-4 bg-dusty-olive/10 rounded-lg font-body text-sm">
              <p className="font-medium text-charcoal mb-2">Import Complete</p>
              <p>Import lines created: {legacyResult.import_lines_created}</p>
              <p>Export lines created: {legacyResult.export_lines_created}</p>
              <p>Skipped empty rows: {legacyResult.skipped_empty}</p>
              {legacyResult.warnings.length > 0 && (
                <div className="mt-2">
                  <p className="font-medium text-yellow-700">Warnings:</p>
                  {legacyResult.warnings.map((w, i) => <p key={i} className="text-yellow-700">{w}</p>)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
