# API Documentation

## Base URL

All endpoints are prefixed with `/api`. During development, the Vite frontend proxies `/api/*` to `http://localhost:8000`.

## Authentication

Session-based authentication using JWT in an httpOnly cookie (`sez_session`).

### POST `/api/auth/login`
Login with username and password. Sets session cookie.
```json
// Request
{ "username": "admin", "password": "secret" }
// Response 200
{ "id": 1, "username": "admin", "is_admin": true, "is_active": true, "created_at": "..." }
```

### POST `/api/auth/logout`
Clears session cookie. Returns 200.

### GET `/api/auth/me`
Returns current authenticated user. 401 if not logged in.

---

## Import Flow

### POST `/api/import/upload`
Upload an import PDF. Multipart form with `file` field.
```json
// Response 200
{ "document_id": 1, "filename": "import.pdf", "doc_type": "import", "duplicate": false, "message": "..." }
```

### POST `/api/import/extract/{document_id}?use_mock=false`
Extract structured data from uploaded PDF using Claude API.
```json
// Response 200
{
  "document_id": 1,
  "doc_type": "import",
  "import_entries": [{
    "consignor_exporter": { "value": "ACME", "confidence": 0.9, "source_text": "..." },
    ...
  }],
  "error": null
}
```

### POST `/api/import/confirm?source_document_id=1`
Confirm reviewed import entries. Creates ImportLine records with full balances.
```json
// Request body: list of ImportLineCreate
[{
  "consignor_exporter": "ACME",
  "description": "Widgets",
  "import_entry_number": "25NBOIM001",
  "hs_code": "84713000",
  "country": "CN",
  "unit": "UNT",
  "quantity_imported": 500,
  "customs_value_kes": 250000,
  "bif_value_kes": 50000
}]
// Response 200: list of ImportLineOut
```

---

## Export Flow

### POST `/api/export/upload`
Upload an export PDF. Same format as import upload.

### POST `/api/export/extract/{document_id}?use_mock=false`
Extract export data from PDF. Returns `ExtractionResponse` with `export_entries`.

### GET `/api/export/match-candidates?hs_code=...&description=...&consignor=...`
Find import lines with positive balance that could match an export. Returns list of `ImportLineSummary`.

### POST `/api/export/preview-proration?import_line_id=1&quantity_exported=250`
Preview prorated values before confirming.
```json
// Response 200
{
  "import_line_id": 1,
  "export_quantity": 250,
  "prorated_customs_value": 12500,
  "prorated_bif_value": 2500,
  "remaining_quantity": 750,
  "overdraft": false,
  "overdraft_message": null
}
```

### POST `/api/export/confirm?source_document_id=1&admin_override=false&override_reason=`
Confirm export entries. Auto-prorates customs/BIF values using formula: `U = K * T / J`.
```json
// Request body: list of ExportLineCreate
[{
  "import_line_id": 1,
  "customer_name": "BUYER",
  "quantity_exported": 250,
  "export_entry_number": "25NBOEX001"
}]
```

### DELETE `/api/export/{export_id}`
Delete an export line and restore import balance. Admin only.

---

## Search & Ledger

### GET `/api/ledger/dashboard`
Dashboard statistics: total imports/exports, open balances, recent activity.

### GET `/api/ledger/search?entry_number=...&hs_code=...&open_balance_only=true&page=1&page_size=50`
Search import lines with filters. Returns list of `ImportLineSummary`.

### GET `/api/ledger/import-lines/{id}`
Full import line detail including export history.

### GET `/api/ledger/audit?entity_type=...&change_type=...&page=1`
Query audit log entries.

### GET `/api/ledger/audit/export?entity_type=import_line`
Export audit log as CSV. Admin only.

### GET `/api/ledger/download?style=blank_continuation`
Download complete ledger as Excel (.xlsx). Styles: `blank_continuation` or `fully_populated`.

### POST `/api/ledger/import-legacy`
Import legacy data from `resources/Seza_Stock_Ledger_Hackathon.xlsx`. Admin only. Idempotent (fails if data exists).

---

## Admin

### GET `/api/admin/users`
List all users. Admin only.

### POST `/api/admin/users`
Create user. `{ "username": "...", "password": "...", "is_admin": false }`

### PUT `/api/admin/users/{id}`
Update user. Optional fields: `password`, `is_admin`, `is_active`.

### DELETE `/api/admin/users/{id}`
Delete user. Cannot delete self.

### GET/POST `/api/admin/units`
List/create allowed units (e.g., KG, UNT).

### GET/POST `/api/admin/countries`
List/create allowed countries (e.g., KE, CN).

---

## System

### GET `/health`
Liveness check. Returns `{ "status": "ok" }`.
