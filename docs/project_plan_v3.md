# SEZ Ledger Automation Tool — Final Project Plan & Build Spec (v3)

**Purpose of this document:** A build specification for an AI coding agent (Claude Code, Devin, or similar — this spec is tool-agnostic) to design and build this application. It is grounded in two real artifacts that were inspected directly: the actual working ledger (`Seza_Stock_Ledger_-_Hackathon.xlsx`) and four real customs entry PDFs (SAD/IM7 forms). The extraction schema, field mappings, and ledger structure below are confirmed, not assumed — each mapping was cross-checked against a real ledger row.

---

## 1. Background

The organization operates within a Special Economic Zone (SEZ) and maintains a stock ledger tracking goods from import through export, including running balances, for SEZA audit purposes. Today this is filled manually from customs entry PDFs — Single Administrative Documents (SAD), form type IM7, issued under the East African Community customs system. The goal is to automate extraction from those PDFs and auto-fill the ledger, including proration and balance-tracking, flagging uncertain data for human review.

## 2. Project Goals

1. Automatically fill data into the SEZ Ledger from uploaded entry documents.
2. Support SEZA audit submissions — output must be the actual audit-ready ledger file.
3. Make it easy to locate/search specific items within import entries.
4. Long-term: integrate with the organization's ERP system to pull entry data automatically instead of via PDF upload.

## 3. Source Document: the SAD/IM7 Customs Form

All four sample entries are the same East African Community "Single Administrative Document (SAD)-ICMS" form, declaration type **IM7**. Structure:

- **Header (page 1, boxes 1–30):** one set of fields covering the whole entry — consignor/exporter (box 2), consignee (box 8), declarant (box 14), country of last consignment (15a), country of destination (17a), currency and exchange rate (22/23), etc. These apply to *every item* in the entry.
- **Box 31–47, repeated once per item line:** each physical item in the shipment gets its own block containing HS code (33), country of origin (34), gross/net mass (35/38), supplementary units (41a), a commercial description, and a flexible "Additional information" block (44) whose field names vary by product category, plus FOB/customs value (45/46) and a tax calculation table (47).
- **Multi-item entries span multiple PDF pages**, each additional page holding more item blocks (e.g. the Jiangxi Hongda entry has 16 items across 9 pages).

This structure is exactly why the ledger has one row per item, not one row per PDF — confirmed in Section 4.

## 4. Confirmed Field Mapping: PDF → Ledger Column

This mapping was verified by finding the corresponding row already in the ledger for the AMEX Healthcare GmbH entry (`26NBOIM710173420`, ledger rows 564–565, internal reference `IMP/090`) and matching every field exactly.

| Ledger column | Source in PDF | Notes |
|---|---|---|
| **A** Consignor / Exporter | Box 2 name + country from the consignor's address | Format used in the ledger: `"{Name} - {COUNTRY}"`. This is one value per entry, same for every item row in the group. |
| **B** Description | Box 32's short "Description of" text | **Not** the long semicolon-separated "Commercial description of the goods" text — that longer string is closer to what's seen pasted raw into the `Sheet2` staging area today, but the target ledger field is the clean short description. |
| **C** Import File Number | **Not present anywhere on the PDF.** | Purely an internal sequential reference the team assigns (e.g. `IMP/090`). The tool must auto-suggest the next number in sequence, editable by the user, with support for `/A`, `/B` suffixes when one shipment is covered by multiple related entries (seen in the ledger as `IMP/077/A`, `IMP/077/B`). |
| **D** Import Entry Date | The date shown beside the entry number near the top of page 1 (also matches the D/J control stamp date) | |
| **E** Import Entry Number | The code printed top-right under "A CUSTOMS OFFICE" (e.g. `26NBOIM710173420`) | This is the number used in the PDF filename and is the unique entry identifier — **not** the longer "7 Reference number" field, which is unused in the ledger. |
| **F** HS code | Box 33 Commodity HS Code | Per item line |
| **G** Country | Box 34 **Country of origin**, per item line | Distinct from column A's country — an entry can have items originating from different countries even under one consignor (confirmed: the AMEX entry has one item from Austria (AT) and one from Cyprus (CY)). |
| **H** Supplementary Units, **I** Unit | Box 41a value and unit suffix (e.g. `637 KGM` → `637`, `KG`) | |
| **J** Quantity Imported | Box 44's `QuantityOrNbOfPacka` field, **when present** | See the important caveat below — this field is not always present under this exact name. |
| **K** Customs Value KES | Box 46 Customs value | |
| **L** BIF Value KES | **"Total Tax due for this item"** from the Box 47 tax table — the sum of whichever duties apply to that item (import duty, excise, VAT, RDL, concession fees, MSS levy) | Confirmed exact match on two separate items in the AMEX document. This is *not* just the RDL line — it's the item's total tax bill. |

### Important caveat: Box 44 is not a fixed schema

Box 44 ("Additional information") is a flexible name/value block, and **which field names appear depends on the product category**:
- Pharmaceutical items (AMEX, S Kant) carry a `QuantityOrNbOfPacka` field directly giving the total individual-unit count — this is what maps to column J.
- Medical device items (Jiangxi Hongda's syringes/catheters) instead carry `NbOfPackages` and `PiecesPerPackage` separately, with **no** `QuantityOrNbOfPacka` field at all — the true quantity has to be derived (`NbOfPackages × PiecesPerPackage`) or located under a different concept entirely.

**Implication for the build:** the extraction step cannot rely on a fixed field-name lookup for column J (or for other Box 44-derived values). It needs to be prompted conceptually — "find the total count of individual units for this item, wherever that figure lives in the additional-information block" — which is exactly the kind of flexible document understanding an LLM-based extractor (rather than rigid regex/positional OCR) is suited for. This should be treated as a first-class design constraint, not an edge case to patch later. **[PENDING: confirm the correct derivation for non-pharma product categories against a few more real examples, ideally with the corresponding ledger row, before finalizing the extraction prompt.]**

## 5. Confirmed Ledger Structure (`Sheet1`)

One flat table, one row per item line, columns A–Z:

| Col | Header | Populated by |
|---|---|---|
| A–L | Consignor, Description, Import File Number, Import Entry Date, Import Entry Number, HS code, Country, Supp. Units, Unit, Quantity Imported, Customs Value KES, BIF Value KES | **Import extraction** (Section 4) — A/C/D/E only on the first row of a multi-item entry's group |
| M–Q | Customer Name, Export File Number, Export Entry Date, Export Entry Number, PPB Permit Ref. | **Export extraction** (schema TBD — see Section 10) |
| R–T | Supplementary Units, Unit, Quantity Exported | **Export extraction**, with R usually prorated |
| U, V | Customs Value, BIF Value (export side) | **Formula**: `= (Imported Value × Quantity Exported) / Quantity Imported` |
| W–Z | Balance Quantity, Balance Customs Value, Balance BIF Value, Balance Supplementary Units | **Formula**: `= Imported total − SUM(all exported values in the group)`, extending across every shipment row in the group |

**Multi-item import → multiple rows:** a single PDF like the Jiangxi Hongda entry (16 items) produces 16 rows, sharing the same A/C/D/E values (populated once, on the first row).

**Multiple partial exports against one import row → additional sub-rows appended below**, each carrying only columns M–T, with the group's W/X/Y/Z formulas extended to reference every new row's T (and R) cell.

## 6. Core Functional Requirements

1. **Upload one entry document (PDF) at a time** — import or export — through a simple web interface.
2. **Extract structured data** per Section 4's confirmed mapping, using an LLM-based extractor that reasons about field *meaning* rather than fixed positions, given Box 44's variability.
3. **Auto-suggest the next Import File Number**, editable by the user; support `/A`, `/B` suffixes.
4. **Append rows into `Sheet1`** following the exact structural conventions in Section 5.
5. **Prorate quantities, weights, and values** using the exact formulas in Section 5/7.
6. **Track running balances** per import item line in a persistent database (Section 8).
7. **Let a user search** an import line by entry number, description, consignor, or HS code.
8. **Flag low-confidence extractions** for human review before anything is written to the ledger or database — particularly the Box 44 quantity derivation, which is the least standardized field.
9. **Produce a downloadable ledger file** in the exact existing format — same headers, columns, formulas — audit-submittable without manual cleanup.
10. **Log an audit trail**: what was auto-extracted vs. human-corrected, by whom, when.

## 7. Confirmed Proration & Balance Formulas

```
Customs Value Exported (U) = (Customs Value Imported (K) × Quantity Exported (T)) / Quantity Imported (J)
BIF Value Exported (V)     = (BIF Value Imported (L) × Quantity Exported (T)) / Quantity Imported (J)

Balance Quantity (W)        = Quantity Imported (J) − SUM(all T in the group)
Balance Customs Value (X)   = Customs Value Imported (K) − SUM(all U in the group)
Balance BIF Value (Y)       = BIF Value Imported (L) − SUM(all V in the group)
Balance Supp. Units (Z)     = Supplementary Units Imported (H) − SUM(all R in the group)
```

## 8. Data Model

**`import_lines`** (one row per item within an import entry)
- id, consignor, description, import_file_number, import_entry_date, import_entry_number, hs_code, country_of_origin
- supplementary_units, unit, quantity_imported, customs_value_kes, bif_value_kes (total item tax)
- quantity_remaining, customs_value_remaining, bif_value_remaining, supplementary_units_remaining (live running balance)
- source_pdf_reference, extraction_confidence (JSON per field, flagging especially the Box-44-derived quantity), status, created_by/at

**`export_lines`** (one row per shipment applied against an import line)
- id, import_line_id (FK), customer_name, export_file_number, export_entry_date, export_entry_number, ppb_permit_ref
- supplementary_units_exported, unit, quantity_exported, customs_value_exported, bif_value_exported (computed via the formulas in Section 7)
- source_pdf_reference, extraction_confidence, status, created_by/at

**`audit_log`**
- id, entity_type, entity_id, field_changed, old_value, new_value, changed_by, changed_at, change_type (auto_extracted / human_corrected)

## 9. User Flow (MVP)

1. User opens the app, selects entry type: **Import** or **Export**.
2. User uploads a single PDF (potentially multi-page/multi-item).
3. System extracts one structured record per item line, flags low-confidence fields (especially any Box 44-derived quantity), and suggests the next Import File Number.
4. User reviews/corrects, confirms.
5. **If Import:** one `import_lines` row created per item, full balances = imported totals.
6. **If Export:** user (or an auto-suggested match by description/HS code) selects which `import_lines` row(s) this export draws against; system computes exported value via the ratio formula, creates `export_lines` row(s), decrements the linked import line's balance.
7. User downloads the ledger — regenerated from the database into the exact `Sheet1` format, formulas intact.
8. Every action logged.

## 10. Open Items / Information Still Needed

- [ ] **Sample export entry PDF(s)** — none have been reviewed yet. The export-side schema (columns M–T) is inferred from the ledger alone and needs the same PDF-to-ledger verification done here for the import side.
- [ ] Confirm the Box 44 quantity derivation for non-pharma product categories (medical devices, consumables, equipment) against a few more real examples with known ledger outcomes.
- [ ] Confirm whether one export PDF reliably maps to one or many import lines, or needs manual matching every time.
- [ ] Confirm the "blank continuation row" display convention for the downloadable file — replicate exactly, or fully populate every row (functionally equivalent, easier to build)?
- [ ] Confirm whether `Sheet2` (the staging area) should be kept as a visible "pending review" tab, or retired now that extraction is automated.
- [ ] Confirm country code normalization rules — Box 34 already gives clean ISO-2 codes in the samples seen, but the legacy ledger data has inconsistencies (e.g. `FRANCE` instead of `FR`) worth deciding how to handle going forward.
- [ ] Number of concurrent users / where the tool will be hosted.

## 11. Technical Architecture (recommended)

**Type of application: a web application** (browser-based UI, internally hosted), not a desktop-installed program — multiple staff can use it from any PC, it's easy to add login/audit logging, and it gives a clean path to later ERP integration.

| Layer | Technology | Why |
|---|---|---|
| Backend / API | Python (FastAPI) | Best ecosystem for PDF parsing and Excel generation |
| PDF data extraction | Claude API (document understanding), prompted with the exact confirmed schema in Section 4 and explicit handling for Box 44's variability | Handles the demonstrated inconsistency in field names across product categories; returns structured JSON with a confidence flag per field |
| Excel generation | `openpyxl` | Regenerate `Sheet1` from the database on each download, replicating the real file's headers, column order, number formats, and formula strings (not hardcoded values) |
| Database | PostgreSQL (SQLite for prototype) | Required for running balances and audit trail |
| Frontend | Simple web UI | Upload screen, review/confirm screen (with the Box-44-derived quantity clearly flagged when uncertain), search screen, download button |
| Auth | Basic login | For audit log attribution |
| Hosting | Internal server | Keeps SEZ/customs data inside organizational control |

If building with an AI coding agent such as Claude Code or Devin, hand this document over directly as the spec — the confirmed field mappings in Section 4 and formulas in Section 7 are the parts that must be implemented exactly as written, since they were verified against real data rather than assumed.

## 12. Build Phases

**Phase 1 — Foundations:** backend setup, DB schema, auth; PDF upload + extraction endpoint returning structured JSON with per-field confidence, targeting the Section 4 schema; review/confirm UI.

**Phase 2 — Import flow:** persist confirmed import lines with starting balances; Excel generation matching the real file's exact conventions (test against the actual uploaded workbook).

**Phase 3 — Export flow + proration:** export extraction + review screen (once sample export PDFs are available); import-line matching/search UI; the exact ratio-based proration formulas; the "append sub-row, extend balance formula range" logic, with dedicated unit tests mirroring real multi-shipment scenarios from the ledger.

**Phase 4 — Search, audit, and download:** search/filter UI; audit log viewer; "download current ledger" verified with zero formula errors before every delivery.

**Phase 5 — Hardening:** block/flag exports exceeding remaining balance; normalize country codes without altering historical rows; error handling for malformed/unreadable PDFs; full regression suite on proration/balance logic, including the Box 44 quantity-derivation edge cases.

**Phase 6 — Future:** ERP integration to replace manual PDF upload.

## 13. Acceptance Criteria (MVP)

- Uploading a single-item import PDF (e.g. the AMEX/S Kant style) produces one correct `Sheet1`-equivalent row, matching Section 4's mapping exactly.
- Uploading a multi-item import PDF (e.g. the Jiangxi Hongda style, 16 items) produces one correctly grouped row per item, including correct handling of its non-standard Box 44 quantity fields.
- Uploading an export PDF and matching it to an import line correctly computes `U`/`V` via the exact ratio formula and correctly updates the group's balance.
- A second, later partial export against the same import line correctly extends the balance calculation.
- The downloaded `.xlsx` opens cleanly with zero formula errors and matches the existing file's formatting closely enough to be audit-submittable without manual cleanup.
- Every auto-filled and human-corrected field is recorded in the audit log.
- A user can find a specific import line by entry number, description, or HS code in a few seconds.

---

*Next step: share sample export entry PDFs, and 2–3 more import PDFs from non-pharma product categories, so the remaining Box 44 derivation and the entire export-side schema can be confirmed the same way the import side was in this document.*
