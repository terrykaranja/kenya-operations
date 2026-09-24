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

## Not yet available

- **No sample import/export PDFs** exist in `/resources` yet, so Phase 4
  (extraction layer) will initially only be testable against the
  `MockExtractor` and fixture data derived from `docs/ledger_analysis.md`.
  Real Claude-extraction accuracy can't be validated until sample PDFs are
  provided.
- **No local Docker** in the current dev sandbox — backend code is being
  sanity-tested against a local Python 3.14 venv with unpinned latest
  dependency versions (not committed), since the pinned `requirements.txt`
  versions target `python:3.11-slim` per the Dockerfile and don't have
  prebuilt wheels for 3.14. The pinned versions are unchanged for the real
  Docker-based dev/prod path.
