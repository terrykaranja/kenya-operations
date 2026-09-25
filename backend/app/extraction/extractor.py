"""PDF extraction using Claude API.

Sends uploaded PDFs to Claude for structured data extraction of SAD/IM7 and
EX3 customs forms (East African Community Single Administrative Document).
Returns structured data with confidence scores for human review.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import anthropic
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExtractedField(BaseModel):
    """A single extracted field with confidence metadata."""
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_text: Optional[str] = None


class ExtractedImportEntry(BaseModel):
    """Structured import entry extracted from a PDF."""
    consignor_exporter: ExtractedField = Field(default_factory=ExtractedField)
    description: ExtractedField = Field(default_factory=ExtractedField)
    import_file_number: ExtractedField = Field(default_factory=ExtractedField)
    import_entry_date: ExtractedField = Field(default_factory=ExtractedField)
    import_entry_number: ExtractedField = Field(default_factory=ExtractedField)
    hs_code: ExtractedField = Field(default_factory=ExtractedField)
    country: ExtractedField = Field(default_factory=ExtractedField)
    supplementary_units: ExtractedField = Field(default_factory=ExtractedField)
    unit: ExtractedField = Field(default_factory=ExtractedField)
    quantity_imported: ExtractedField = Field(default_factory=ExtractedField)
    customs_value_kes: ExtractedField = Field(default_factory=ExtractedField)
    bif_value_kes: ExtractedField = Field(default_factory=ExtractedField)


class ExtractedExportEntry(BaseModel):
    """Structured export entry extracted from a PDF."""
    customer_name: ExtractedField = Field(default_factory=ExtractedField)
    export_file_number: ExtractedField = Field(default_factory=ExtractedField)
    export_entry_date: ExtractedField = Field(default_factory=ExtractedField)
    export_entry_number: ExtractedField = Field(default_factory=ExtractedField)
    ppb_permit: ExtractedField = Field(default_factory=ExtractedField)
    supplementary_units_exported: ExtractedField = Field(default_factory=ExtractedField)
    unit: ExtractedField = Field(default_factory=ExtractedField)
    quantity_exported: ExtractedField = Field(default_factory=ExtractedField)
    customs_value_exported: ExtractedField = Field(default_factory=ExtractedField)
    bif_value_exported: ExtractedField = Field(default_factory=ExtractedField)


class ExtractionResult(BaseModel):
    """Result of PDF extraction."""
    doc_type: str  # "import" or "export"
    import_entries: list[ExtractedImportEntry] = Field(default_factory=list)
    export_entries: list[ExtractedExportEntry] = Field(default_factory=list)
    raw_text: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# SAD/IM7-specific extraction prompts
# ---------------------------------------------------------------------------

IMPORT_EXTRACTION_PROMPT = """\
You are extracting structured data from an East African Community \
"Single Administrative Document (SAD)-ICMS" customs form. The declaration \
type is IM7 (import into a Kenya Special Economic Zone).

## Document layout

The form has a HEADER section (page 1, boxes 1-30) that appears once per \
entry, and a PER-ITEM section (boxes 31-47) that repeats for each line item.

### Header fields (extract once, apply to every item):

1. **Consignor / Exporter (Box 2)** — The shipper's name and country.
   Format the value as "NAME - COUNTRY" (e.g. "SIRMAXO CHEMICALS PVT. LTD - INDIA").
   The country name is typically shown beneath or beside the company name.

2. **Import Entry Number** — Found in the top-right area of page 1, under \
   the heading "A CUSTOMS OFFICE" or nearby. It is an alphanumeric code \
   like `26MBAIM702363171`. The prefix encodes the year, office code, and \
   declaration type (IM7).

3. **Import Entry Date** — The date beside or below the entry number, \
   usually in DD/MM/YYYY format. Convert it to YYYY-MM-DD for output \
   (e.g. `09/04/2026` → `2026-04-09`).

### Per-item fields (extract for EACH line item):

4. **Description (Box 31)** — Short product description \
   (e.g. "SANI CALAMINE-100 ML").

5. **HS Commodity Code (Box 33)** — The 8-digit tariff heading \
   (e.g. `30049000`). Sometimes split across sub-boxes 33.1-33.5; \
   concatenate them into a single 8-digit string.

6. **Country of Origin (Box 34)** — ISO 2-letter country code \
   (e.g. `IN` for India).

7. **Supplementary Units (Box 41a)** — A number followed by a unit suffix. \
   Example: `1350 KGM`. Split this into TWO fields:
   - supplementary_units = the numeric part (e.g. `1350`)
   - unit = the unit code, normalized: KGM → KG, UNT → UNT, LTR → LT, \
     PCE → UNT, etc.

8. **Quantity Imported (Box 44)** — This is the total count of individual \
   units (tablets, bottles, vials, pieces, etc.). IMPORTANT: the field name \
   in Box 44 VARIES by product category:
   - For pharmaceutical items: look for `QuantityOrNbOfPacka` — this gives \
     the unit count directly.
   - For medical devices / other items: look for `NbOfPackages` and \
     `PiecesPerPackage` — multiply them to get the total unit count \
     (quantity = NbOfPackages × PiecesPerPackage).
   - If you see both field types, use the correct one for the product type.
   - Extract the TOTAL INDIVIDUAL UNITS regardless of field naming.

9. **Customs Value KES (Box 46)** — The statistical/customs value in KES \
   after exchange rate conversion. This is a monetary amount, possibly \
   with thousands separators. Return as a plain number string without \
   commas (e.g. `1234567.89`).

10. **BIF Value KES (Box 47 tax table)** — Look at Box 47's tax \
    calculation table. Find the line labeled "Total Tax due for this item" \
    or "Total" at the bottom of the tax table. This is the SUM of ALL \
    duty/tax lines (import duty, excise duty, VAT, Railway Development \
    Levy, concession fees, MSS levy, etc.). Return that total as a plain \
    number string. Do NOT return just one tax line — return the TOTAL of \
    all duties for this item.

### Fields NOT in the PDF:

11. **Import File Number** — This is an internal sequential reference \
    (e.g. IMP/090) that is NOT present in the PDF. Always set this to \
    `{"value": null, "confidence": 0.0, "source_text": ""}`.

## Output format

Return a JSON object with an "items" array. Each element represents one \
line item from the form. Header fields (consignor, entry number, date) \
should be repeated identically on every item.

```json
{
  "items": [
    {
      "consignor_exporter": {"value": "...", "confidence": 0.95, "source_text": "..."},
      "description": {"value": "...", "confidence": 0.9, "source_text": "..."},
      "import_file_number": {"value": null, "confidence": 0.0, "source_text": ""},
      "import_entry_date": {"value": "2026-04-09", "confidence": 0.95, "source_text": "09/04/2026"},
      "import_entry_number": {"value": "26MBAIM702363171", "confidence": 0.95, "source_text": "..."},
      "hs_code": {"value": "30049000", "confidence": 0.9, "source_text": "..."},
      "country": {"value": "IN", "confidence": 0.95, "source_text": "..."},
      "supplementary_units": {"value": "1350", "confidence": 0.85, "source_text": "1350 KGM"},
      "unit": {"value": "KG", "confidence": 0.9, "source_text": "KGM"},
      "quantity_imported": {"value": "54000", "confidence": 0.85, "source_text": "QuantityOrNbOfPacka: 54000"},
      "customs_value_kes": {"value": "1234567.89", "confidence": 0.9, "source_text": "..."},
      "bif_value_kes": {"value": "567890.12", "confidence": 0.85, "source_text": "Total Tax due for this item: 567890.12"}
    }
  ]
}
```

IMPORTANT RULES:
- If a field cannot be found, set value to null and confidence to 0.0.
- If the document contains multiple line items (boxes 31-47 repeating), \
  extract EACH as a separate item in the array.
- For monetary values, strip commas and currency symbols; return plain \
  decimal strings.
- Dates must be in YYYY-MM-DD format.
- The import_file_number is ALWAYS null with confidence 0.0.
- Return ONLY valid JSON, no explanatory text outside the JSON block."""


EXPORT_EXTRACTION_PROMPT = """\
You are extracting structured data from an East African Community \
"Single Administrative Document (SAD)-ICMS" customs form. The declaration \
type is EX3 (export from a Kenya Special Economic Zone).

## Document layout

The form has a HEADER section (page 1, boxes 1-30) that appears once per \
entry, and a PER-ITEM section (boxes 31-47) that repeats for each line item.

### Header fields (extract once, apply to every item):

1. **Customer Name (Box 8 — Consignee)** — The recipient / buyer of the \
   exported goods. Found in Box 8 labeled "Consignee". Format as the \
   company or organization name, including location if present \
   (e.g. "IFRC SRCS- GAROWE (SOMALIA)").

2. **Export Entry Number** — Found in the top-right area of page 1, under \
   "A CUSTOMS OFFICE" or nearby. Alphanumeric code like `26NBOEX308196982`. \
   The prefix encodes year, office code, and declaration type (EX3).

3. **Export Entry Date** — The date beside or below the entry number. \
   Convert from DD/MM/YYYY to YYYY-MM-DD format.

Note: Box 2 (Consignor/Exporter) on EX3 forms is the SEZ company itself \
(the entity exporting). The CUSTOMER is in Box 8.

### Per-item fields (extract for EACH line item):

4. **Description (implicit from Box 31)** — While not a named output \
   field, use the product description from Box 31 to inform your \
   understanding of the product category.

5. **PPB Permit** — PPB (Pharmacy and Poisons Board) approved export \
   permit application number if present in the document. Often found in \
   Box 44 additional information or attached documents. If not visible, \
   set to null with confidence 0.0.

6. **Supplementary Units Exported (Box 41a)** — A number followed by a \
   unit suffix (e.g. `500 KGM`). Split into:
   - supplementary_units_exported = the numeric part (e.g. `500`)
   - unit = normalized unit code: KGM → KG, UNT → UNT, LTR → LT, etc.

7. **Quantity Exported (Box 44)** — Total count of individual units \
   exported. Same logic as imports:
   - Pharmaceutical items: look for `QuantityOrNbOfPacka`.
   - Medical devices: multiply `NbOfPackages × PiecesPerPackage`.
   - Extract TOTAL INDIVIDUAL UNITS regardless of the field name used.

8. **Customs Value Exported (Box 46)** — Customs/statistical value in \
   KES. Return as a plain number string without commas.

9. **BIF Value Exported (Box 47 tax table)** — Total tax due for the \
   item from Box 47's tax table. Sum of ALL duty lines (import duty, \
   excise, VAT, levies, etc.). For exports this may be zero or minimal, \
   but extract whatever the total shows.

### Fields NOT in the PDF:

10. **Export File Number** — Internal sequential reference (e.g. EXP/002), \
    NOT present in the PDF. Always set to \
    `{"value": null, "confidence": 0.0, "source_text": ""}`.

## Output format

Return a JSON object with an "items" array:

```json
{
  "items": [
    {
      "customer_name": {"value": "...", "confidence": 0.95, "source_text": "..."},
      "export_file_number": {"value": null, "confidence": 0.0, "source_text": ""},
      "export_entry_date": {"value": "2026-03-15", "confidence": 0.95, "source_text": "15/03/2026"},
      "export_entry_number": {"value": "26NBOEX308196982", "confidence": 0.95, "source_text": "..."},
      "ppb_permit": {"value": null, "confidence": 0.0, "source_text": ""},
      "supplementary_units_exported": {"value": "500", "confidence": 0.85, "source_text": "500 KGM"},
      "unit": {"value": "KG", "confidence": 0.9, "source_text": "KGM"},
      "quantity_exported": {"value": "12000", "confidence": 0.85, "source_text": "..."},
      "customs_value_exported": {"value": "987654.32", "confidence": 0.9, "source_text": "..."},
      "bif_value_exported": {"value": "0", "confidence": 0.85, "source_text": "Total Tax: 0"}
    }
  ]
}
```

IMPORTANT RULES:
- If a field cannot be found, set value to null and confidence to 0.0.
- If the document contains multiple line items, extract EACH as a \
  separate item in the array.
- Strip commas and currency symbols from monetary values.
- Dates must be in YYYY-MM-DD format.
- The export_file_number is ALWAYS null with confidence 0.0.
- Return ONLY valid JSON, no explanatory text outside the JSON block."""


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

def get_api_key() -> Optional[str]:
    """Resolve the Anthropic API key.

    Checks the following sources in order:
    1. The ``app_settings`` database table (key_name = 'anthropic_api_key').
    2. The ``ANTHROPIC_API_KEY`` environment variable.

    Returns ``None`` if no key is found in either location.
    """
    # 1. Try database lookup (gracefully skip if model/table not ready)
    try:
        from app.db import SessionLocal
        from app.models.config import AppSetting  # may not exist yet

        db = SessionLocal()
        try:
            setting = (
                db.query(AppSetting)
                .filter(AppSetting.key == "anthropic_api_key")
                .first()
            )
            if setting and setting.value:
                logger.debug("API key loaded from app_settings table")
                return setting.value
        finally:
            db.close()
    except Exception:
        # AppSetting model or table may not exist yet — that's fine
        logger.debug(
            "Could not load API key from database (model/table may not exist); "
            "falling back to environment variable"
        )

    # 2. Fall back to environment variable
    env_key = os.getenv("ANTHROPIC_API_KEY")
    if env_key and env_key != "your_anthropic_api_key_here":
        return env_key

    return None


# ---------------------------------------------------------------------------
# PDF extraction via Claude API
# ---------------------------------------------------------------------------

def extract_from_pdf(pdf_path: Path, doc_type: str) -> ExtractionResult:
    """Extract structured data from a SAD/IM7 or EX3 PDF using Claude API.

    Args:
        pdf_path: Path to the PDF file.
        doc_type: "import" or "export".

    Returns:
        ExtractionResult with extracted entries and confidence scores.
    """
    api_key = get_api_key()
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    if not api_key:
        return ExtractionResult(
            doc_type=doc_type,
            error="ANTHROPIC_API_KEY not configured. Set it in .env or in "
                  "Admin > Settings (app_settings table).",
        )

    try:
        pdf_data = pdf_path.read_bytes()
        pdf_b64 = base64.standard_b64encode(pdf_data).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            IMPORT_EXTRACTION_PROMPT
            if doc_type == "import"
            else EXPORT_EXTRACTION_PROMPT
        )

        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        response_text = message.content[0].text

        # Parse JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        data = json.loads(json_text.strip())
        items = data.get("items", [])

        result = ExtractionResult(doc_type=doc_type, raw_text=response_text)

        if doc_type == "import":
            for item in items:
                entry = ExtractedImportEntry()
                for field_name in ExtractedImportEntry.model_fields:
                    if field_name in item:
                        field_data = item[field_name]
                        if isinstance(field_data, dict):
                            setattr(entry, field_name, ExtractedField(**field_data))
                result.import_entries.append(entry)
        else:
            for item in items:
                entry = ExtractedExportEntry()
                for field_name in ExtractedExportEntry.model_fields:
                    if field_name in item:
                        field_data = item[field_name]
                        if isinstance(field_data, dict):
                            setattr(entry, field_name, ExtractedField(**field_data))
                result.export_entries.append(entry)

        return result

    except json.JSONDecodeError as e:
        return ExtractionResult(
            doc_type=doc_type,
            error=f"Failed to parse extraction response as JSON: {e}",
            raw_text=response_text if "response_text" in dir() else None,
        )
    except anthropic.APIError as e:
        return ExtractionResult(
            doc_type=doc_type,
            error=f"Claude API error: {e}",
        )
    except Exception as e:
        return ExtractionResult(
            doc_type=doc_type,
            error=f"Extraction error: {e}",
        )


# ---------------------------------------------------------------------------
# Mock extraction for development/testing
# ---------------------------------------------------------------------------

def extract_mock(doc_type: str) -> ExtractionResult:
    """Return mock extraction data matching a realistic Sirmaxo SAD/IM7 entry."""
    if doc_type == "import":
        return ExtractionResult(
            doc_type="import",
            import_entries=[
                ExtractedImportEntry(
                    consignor_exporter=ExtractedField(
                        value="SIRMAXO CHEMICALS PVT. LTD - INDIA",
                        confidence=0.95,
                        source_text="SIRMAXO CHEMICALS PVT. LTD\nINDIA",
                    ),
                    description=ExtractedField(
                        value="SANI CALAMINE-100 ML",
                        confidence=0.9,
                        source_text="SANI CALAMINE-100 ML",
                    ),
                    import_file_number=ExtractedField(
                        value=None,
                        confidence=0.0,
                        source_text="",
                    ),
                    import_entry_date=ExtractedField(
                        value="2026-04-09",
                        confidence=0.95,
                        source_text="09/04/2026",
                    ),
                    import_entry_number=ExtractedField(
                        value="26MBAIM702363171",
                        confidence=0.95,
                        source_text="26MBAIM702363171",
                    ),
                    hs_code=ExtractedField(
                        value="30049000",
                        confidence=0.9,
                        source_text="3004 90 00",
                    ),
                    country=ExtractedField(
                        value="IN",
                        confidence=0.95,
                        source_text="IN",
                    ),
                    supplementary_units=ExtractedField(
                        value="1350",
                        confidence=0.85,
                        source_text="1350 KGM",
                    ),
                    unit=ExtractedField(
                        value="KG",
                        confidence=0.95,
                        source_text="KGM",
                    ),
                    quantity_imported=ExtractedField(
                        value="54000",
                        confidence=0.85,
                        source_text="QuantityOrNbOfPacka: 54000",
                    ),
                    customs_value_kes=ExtractedField(
                        value="4528903.50",
                        confidence=0.9,
                        source_text="4,528,903.50",
                    ),
                    bif_value_kes=ExtractedField(
                        value="1764271.37",
                        confidence=0.85,
                        source_text="Total Tax due for this item: 1,764,271.37",
                    ),
                ),
            ],
        )
    else:
        return ExtractionResult(
            doc_type="export",
            export_entries=[
                ExtractedExportEntry(
                    customer_name=ExtractedField(
                        value="IFRC SRCS- GAROWE (SOMALIA)",
                        confidence=0.9,
                        source_text="IFRC SRCS GAROWE\nSOMALIA",
                    ),
                    export_file_number=ExtractedField(
                        value=None,
                        confidence=0.0,
                        source_text="",
                    ),
                    export_entry_date=ExtractedField(
                        value="2026-02-27",
                        confidence=0.9,
                        source_text="27/02/2026",
                    ),
                    export_entry_number=ExtractedField(
                        value="26NBOEX308196982",
                        confidence=0.95,
                        source_text="26NBOEX308196982",
                    ),
                    ppb_permit=ExtractedField(
                        value=None,
                        confidence=0.0,
                        source_text="",
                    ),
                    supplementary_units_exported=ExtractedField(
                        value="300",
                        confidence=0.8,
                        source_text="300 KGM",
                    ),
                    unit=ExtractedField(
                        value="KG",
                        confidence=0.95,
                        source_text="KGM",
                    ),
                    quantity_exported=ExtractedField(
                        value="8800",
                        confidence=0.9,
                        source_text="QuantityOrNbOfPacka: 8800",
                    ),
                    customs_value_exported=ExtractedField(
                        value="26400.00",
                        confidence=0.85,
                        source_text="26,400.00",
                    ),
                    bif_value_exported=ExtractedField(
                        value="0",
                        confidence=0.5,
                        source_text="Total Tax due for this item: 0",
                    ),
                ),
            ],
        )
