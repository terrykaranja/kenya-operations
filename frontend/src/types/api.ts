// API types matching backend Pydantic schemas

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ImportLine {
  id: number;
  consignor_exporter: string | null;
  description: string | null;
  import_file_number: string | null;
  import_entry_date: string | null;
  import_entry_number: string | null;
  hs_code: string | null;
  country: string | null;
  supplementary_units: number | null;
  unit: string | null;
  quantity_imported: number;
  customs_value_kes: number;
  bif_value_kes: number | null;
  balance_quantity: number;
  balance_customs_value: number;
  balance_bif_value: number;
  balance_supplementary_units: number | null;
  is_legacy: boolean;
  created_at: string;
  export_lines: ExportLine[];
}

export interface ImportLineSummary {
  id: number;
  consignor_exporter: string | null;
  description: string | null;
  import_file_number: string | null;
  import_entry_number: string | null;
  hs_code: string | null;
  country: string | null;
  unit: string | null;
  quantity_imported: number;
  customs_value_kes: number;
  balance_quantity: number;
  balance_customs_value: number;
}

export interface ExportLine {
  id: number;
  import_line_id: number;
  customer_name: string | null;
  export_file_number: string | null;
  export_entry_date: string | null;
  export_entry_number: string | null;
  ppb_permit: string | null;
  supplementary_units_exported: number | null;
  unit: string | null;
  quantity_exported: number;
  customs_value_exported: number;
  bif_value_exported: number;
  is_legacy: boolean;
  created_at: string;
}

export interface ExtractedField {
  value: string | null;
  confidence: number;
  source_text: string | null;
}

export interface ExtractedImportEntry {
  consignor_exporter: ExtractedField;
  description: ExtractedField;
  import_file_number: ExtractedField;
  import_entry_date: ExtractedField;
  import_entry_number: ExtractedField;
  hs_code: ExtractedField;
  country: ExtractedField;
  supplementary_units: ExtractedField;
  unit: ExtractedField;
  quantity_imported: ExtractedField;
  customs_value_kes: ExtractedField;
  bif_value_kes: ExtractedField;
}

export interface ExtractedExportEntry {
  customer_name: ExtractedField;
  export_file_number: ExtractedField;
  export_entry_date: ExtractedField;
  export_entry_number: ExtractedField;
  ppb_permit: ExtractedField;
  supplementary_units_exported: ExtractedField;
  unit: ExtractedField;
  quantity_exported: ExtractedField;
  customs_value_exported: ExtractedField;
  bif_value_exported: ExtractedField;
}

export interface ExtractionResponse {
  document_id: number;
  doc_type: string;
  import_entries: ExtractedImportEntry[];
  export_entries: ExtractedExportEntry[];
  error: string | null;
}

export interface UploadResponse {
  document_id: number;
  filename: string;
  doc_type: string;
  duplicate: boolean;
  message: string;
}

export interface ProrationPreview {
  import_line_id: number;
  import_quantity: number;
  import_customs_value: number;
  import_bif_value: number | null;
  import_supplementary_units: number | null;
  export_quantity: number;
  prorated_customs_value: number;
  prorated_bif_value: number;
  prorated_supplementary_units: number | null;
  remaining_quantity: number;
  remaining_customs_value: number;
  remaining_bif_value: number;
  remaining_supplementary_units: number | null;
  overdraft: boolean;
  overdraft_message: string | null;
}

export interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  change_type: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  source: string;
  reason: string | null;
  user_id: number | null;
  created_at: string;
}

export interface DashboardStats {
  total_import_lines: number;
  total_export_lines: number;
  open_balance_lines: number;
  total_documents: number;
  recent_activity: AuditLogEntry[];
}

export interface AllowedUnit {
  id: number;
  code: string;
  description: string | null;
  active: boolean;
}

export interface AllowedCountry {
  id: number;
  code: string;
  name: string;
  active: boolean;
}

export interface LegacyImportResult {
  import_lines_created: number;
  export_lines_created: number;
  skipped_empty: number;
  warnings: string[];
}
