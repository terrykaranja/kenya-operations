// API client for SEZ Ledger backend

const BASE = '/api';

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...opts.headers as Record<string, string> },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export const login = (username: string, password: string) =>
  request<import('../types/api').User>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });

export const logout = () => request<void>('/auth/logout', { method: 'POST' });

export const getMe = () => request<import('../types/api').User>('/auth/me');

// Dashboard
export const getDashboard = () => request<import('../types/api').DashboardStats>('/ledger/dashboard');

// Import flow
export const uploadImportPdf = async (file: File): Promise<import('../types/api').UploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/import/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
};

export const extractImport = (docId: number, useMock = false) =>
  request<import('../types/api').ExtractionResponse>(`/import/extract/${docId}?use_mock=${useMock}`, { method: 'POST' });

export const confirmImport = (entries: any[], sourceDocId?: number) =>
  request<import('../types/api').ImportLine[]>(
    `/import/confirm${sourceDocId ? `?source_document_id=${sourceDocId}` : ''}`,
    { method: 'POST', body: JSON.stringify(entries) },
  );

// Export flow
export const uploadExportPdf = async (file: File): Promise<import('../types/api').UploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/export/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
};

export const extractExport = (docId: number, useMock = false) =>
  request<import('../types/api').ExtractionResponse>(`/export/extract/${docId}?use_mock=${useMock}`, { method: 'POST' });

export const getMatchCandidates = (params: { hs_code?: string; description?: string; consignor?: string }) => {
  const qs = new URLSearchParams();
  if (params.hs_code) qs.set('hs_code', params.hs_code);
  if (params.description) qs.set('description', params.description);
  if (params.consignor) qs.set('consignor', params.consignor);
  return request<import('../types/api').ImportLineSummary[]>(`/export/match-candidates?${qs}`);
};

export const previewProration = (importLineId: number, quantityExported: number) =>
  request<import('../types/api').ProrationPreview>(
    `/export/preview-proration?import_line_id=${importLineId}&quantity_exported=${quantityExported}`,
    { method: 'POST' },
  );

export const confirmExport = (entries: any[], sourceDocId?: number) =>
  request<import('../types/api').ExportLine[]>(
    `/export/confirm${sourceDocId ? `?source_document_id=${sourceDocId}` : ''}`,
    { method: 'POST', body: JSON.stringify(entries) },
  );

export const deleteExport = (id: number) =>
  request<void>(`/export/${id}`, { method: 'DELETE' });

// Search & Ledger
export const searchImportLines = (params: Record<string, string | boolean | number>) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== '' && v !== undefined) qs.set(k, String(v)); });
  return request<import('../types/api').ImportLineSummary[]>(`/ledger/search?${qs}`);
};

export const getImportLineDetail = (id: number) =>
  request<import('../types/api').ImportLine>(`/ledger/import-lines/${id}`);

// Audit
export const getAuditLog = (params: Record<string, string | number> = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== '' && v !== undefined) qs.set(k, String(v)); });
  return request<import('../types/api').AuditLogEntry[]>(`/ledger/audit?${qs}`);
};

// Download
export const downloadLedger = async (style = 'blank_continuation') => {
  const res = await fetch(`${BASE}/ledger/download?style=${style}`, { credentials: 'include' });
  if (!res.ok) throw new Error('Download failed');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'SEZ_Stock_Ledger.xlsx';
  a.click();
  URL.revokeObjectURL(url);
};

// Legacy import
export const runLegacyImport = () =>
  request<import('../types/api').LegacyImportResult>('/ledger/import-legacy', { method: 'POST' });

// Admin
export const listUsers = () => request<import('../types/api').User[]>('/admin/users');
export const createUser = (data: { username: string; password: string; is_admin: boolean }) =>
  request<import('../types/api').User>('/admin/users', { method: 'POST', body: JSON.stringify(data) });
export const updateUser = (id: number, data: any) =>
  request<import('../types/api').User>(`/admin/users/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteUser = (id: number) =>
  request<void>(`/admin/users/${id}`, { method: 'DELETE' });

export const listUnits = () => request<import('../types/api').AllowedUnit[]>('/admin/units');
export const createUnit = (data: { code: string; description?: string }) =>
  request<import('../types/api').AllowedUnit>('/admin/units', { method: 'POST', body: JSON.stringify(data) });

export const listCountries = () => request<import('../types/api').AllowedCountry[]>('/admin/countries');
export const createCountry = (data: { code: string; name: string }) =>
  request<import('../types/api').AllowedCountry>('/admin/countries', { method: 'POST', body: JSON.stringify(data) });

export const exportAuditCsv = async (entityType?: string) => {
  const qs = entityType ? `?entity_type=${entityType}` : '';
  const res = await fetch(`${BASE}/ledger/audit/export${qs}`, { credentials: 'include' });
  if (!res.ok) throw new Error('Export failed');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'audit_log.csv';
  a.click();
  URL.revokeObjectURL(url);
};
