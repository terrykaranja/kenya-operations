# Open Questions & Assumptions

Running log of assumptions made while building the SEZ Ledger Automation Tool,
and decisions that would benefit from sign-off by the Kenya Operations team.
Updated as each phase of the [project plan](../README.md) progresses.

## Data model (Phase 2.1)

- **Balance columns are stored, not derived.** `ImportLine.balance_quantity` /
  `balance_customs_value` / `balance_bif_value` / `balance_supplementary_units`
  mirror ledger columns W/X/Y/Z but are maintained as real columns updated
  transactionally when exports are confirmed/edited/deleted (Phase 6.4), rather
  than computed on every read. This is what makes row-locking + overdraft
  protection possible under concurrent exports.
- **Column X inconsistency.** `docs/ledger_analysis.md` shows `X2` in the
  source workbook computed as `=L2-V2` (a BIF-value balance) while `X3` onward
  use `=K3-U3` (a customs-value balance) — the header says "Balance Customs
  Value". We treat `X2` as a one-off error in the legacy file and always
  compute `balance_customs_value` as `customs_value_kes - Σ customs_value_exported`
  (K − ΣU), matching the header and the majority pattern.
- **One `ImportLine` row per Excel row with columns A–L filled**, not one row
  per "item group". Multi-item PDFs are expected to produce multiple
  `ImportLine` rows; the legacy "blank continuation" formatting (A/C/D/E blank
  on item 2+) is treated as a display concern for the Excel generator (Phase
  3.3), not a storage concern.

## Authentication (Phase 2.2)

- **Session = JWT in an httpOnly cookie** (`sez_session`, `SECRET_KEY`-signed,
  8‑hour expiry), not a server-side session table. `python-jose` is already in
  `requirements.txt`, this avoids adding a `sessions` table, and it scales
  cleanly across multiple backend workers. Flag if the team wants revocable
  server-side sessions instead (e.g. for a hard "log out everywhere" button).
- Login/admin-user-management responses never return `password_hash`; only
  `UserOut` (id, username, is_admin, is_active, created_at) is exposed.

## PDF Extraction (Phase 4)

- **No sample import/export PDFs** exist in `/resources` yet. The extraction
  layer includes both a real Claude API extractor (`app/extraction/extractor.py`)
  and a mock extractor for development/testing. The mock extractor can be
  triggered via `?use_mock=true` on extraction endpoints. Real Claude-extraction
  accuracy can't be validated until sample PDFs are provided.
- **Claude model** defaults to `claude-sonnet-4-20250514` but is configurable
  via `ANTHROPIC_MODEL` in `.env`.

## Proration logic (Phase 6)

- **Proration formulas**: U = K * T / J, V = L * T / J, R = H * T / J.
  If customs or BIF values are not provided on export confirmation, they
  are auto-calculated using the proration formula.
- **Overdraft protection**: Exports that would make `balance_quantity` negative
  are blocked unless `admin_override=true` is passed with a mandatory `override_reason`.
  The override is logged in the audit trail.

## Not yet available

- **No local Docker** in the current dev sandbox — backend code should be
  tested inside Docker or with Python 3.11 as specified in the Dockerfile.
