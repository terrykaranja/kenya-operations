import { useCallback, useState } from 'react';
import { uploadImportPdf, uploadExportPdf, extractImport, extractExport } from '../../services/api';
import type { ExtractionResponse, UploadResponse } from '../../types/api';

interface Props {
  docType: 'import' | 'export';
  onExtracted: (result: ExtractionResponse) => void;
  onNavigate: (page: string) => void;
}

export function UploadScreen({ docType, onExtracted, onNavigate }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState('');

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are accepted');
      return;
    }
    setFile(f);
    setError('');
    setUploadResult(null);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const uploadFn = docType === 'import' ? uploadImportPdf : uploadExportPdf;
      const result = await uploadFn(file);
      setUploadResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleExtract = async (useMock = false) => {
    if (!uploadResult) return;
    setExtracting(true);
    setError('');
    try {
      const extractFn = docType === 'import' ? extractImport : extractExport;
      const result = await extractFn(uploadResult.document_id, useMock);
      if (result.error) {
        setError(result.error);
      } else {
        onExtracted(result);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => onNavigate('dashboard')} className="font-body text-sm text-air-force-blue hover:underline">&larr; Dashboard</button>
        <h2 className="text-2xl text-charcoal">Upload {docType === 'import' ? 'Import' : 'Export'} Document</h2>
      </div>

      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
          dragOver ? 'border-air-force-blue bg-air-force-blue/5' : 'border-cool-steel/40 bg-white'
        }`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <p className="font-body text-charcoal/60 mb-4">
          {file ? file.name : 'Drag & drop a PDF file here, or click to select'}
        </p>
        <input
          type="file"
          accept=".pdf"
          onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }}
          className="hidden"
          id="file-input"
        />
        <label
          htmlFor="file-input"
          className="inline-block px-4 py-2 bg-cool-steel/20 hover:bg-cool-steel/30 rounded-lg font-body text-sm text-charcoal cursor-pointer transition-colors"
        >
          Choose File
        </label>
      </div>

      {error && (
        <div className="mt-4 px-4 py-3 bg-oxblood/10 text-oxblood rounded-lg font-body text-sm">{error}</div>
      )}

      {file && !uploadResult && (
        <div className="mt-6 flex gap-3">
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="px-5 py-2.5 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload PDF'}
          </button>
        </div>
      )}

      {uploadResult && (
        <div className="mt-6 bg-white rounded-xl border border-cool-steel/30 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className={`w-2 h-2 rounded-full ${uploadResult.duplicate ? 'bg-yellow-500' : 'bg-dusty-olive'}`} />
            <p className="font-body text-sm text-charcoal">{uploadResult.message}</p>
          </div>

          <div className="flex gap-3 mt-4">
            <button
              onClick={() => handleExtract(false)}
              disabled={extracting}
              className="px-5 py-2.5 bg-oxblood hover:bg-oxblood-dark text-white rounded-lg font-body text-sm font-medium transition-colors disabled:opacity-50"
            >
              {extracting ? 'Extracting...' : 'Extract with AI'}
            </button>
            <button
              onClick={() => handleExtract(true)}
              disabled={extracting}
              className="px-5 py-2.5 bg-charcoal/10 hover:bg-charcoal/20 text-charcoal rounded-lg font-body text-sm transition-colors disabled:opacity-50"
            >
              Use Mock Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
