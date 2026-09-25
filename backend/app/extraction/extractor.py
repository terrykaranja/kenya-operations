"""PDF extraction using Claude API.

Sends uploaded PDFs to Claude for structured data extraction of import/export
entries. Returns structured data with confidence scores for human review.
"""

import base64
import json
import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

import anthropic
from pydantic import BaseModel, Field


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


IMPORT_EXTRACTION_PROMPT = """You are extracting structured data from a Kenya SEZ (Special Economic Zone) customs document for import entries into a stock ledger.

Extract ALL import line items from this document. For each item, extract:
- consignor_exporter: The company/entity shipping the goods (consignor or exporter name)
- description: Product description
- import_file_number: Import file reference (e.g., IMP/001)
- import_entry_date: Date of import entry (YYYY-MM-DD format)
- import_entry_number: Import entry number (e.g., 25NBOIM701162254)
- hs_code: HS tariff code (e.g., 29336900)
- country: ISO 2-letter country code of origin (e.g., KE, IN, CN)
- supplementary_units: Supplementary units quantity (41a)
- unit: Unit of measurement (KG or UNT)
- quantity_imported: Total quantity imported/repackaged
- customs_value_kes: Customs value in KES
- bif_value_kes: BIF (Bond/Insurance/Freight) value in KES

For each field, provide:
- value: The extracted value as a string
- confidence: Float 0-1 indicating confidence (1.0 = clearly visible, 0.5 = partially readable, 0.0 = guessed)
- source_text: The raw text from the document this was extracted from

Return JSON in this exact format:
{
  "items": [
    {
      "consignor_exporter": {"value": "...", "confidence": 0.9, "source_text": "..."},
      "description": {"value": "...", "confidence": 0.9, "source_text": "..."},
      ...all other fields...
    }
  ]
}

If a field cannot be found, set value to null and confidence to 0.0.
If the document contains multiple line items (e.g. semicolon-delimited entries), extract each as a separate item."""


EXPORT_EXTRACTION_PROMPT = """You are extracting structured data from a Kenya SEZ (Special Economic Zone) customs document for export entries into a stock ledger.

Extract ALL export line items from this document. For each item, extract:
- customer_name: The customer/recipient of the exported goods
- export_file_number: Export file reference (e.g., EXP/002)
- export_entry_date: Date of export entry (YYYY-MM-DD format)
- export_entry_number: Export entry number (e.g., 25NBOEX302333540)
- ppb_permit: PPB approved export permit application number
- supplementary_units_exported: Supplementary units exported (41a)
- unit: Unit of measurement (KG or UNT)
- quantity_exported: Total quantity exported
- customs_value_exported: Customs value of exported goods in KES
- bif_value_exported: BIF value of exported goods in KES

For each field, provide:
- value: The extracted value as a string
- confidence: Float 0-1 indicating confidence
- source_text: The raw text this was extracted from

Return JSON in this exact format:
{
  "items": [
    {
      "customer_name": {"value": "...", "confidence": 0.9, "source_text": "..."},
      "export_file_number": {"value": "...", "confidence": 0.9, "source_text": "..."},
      ...all other fields...
    }
  ]
}

If a field cannot be found, set value to null and confidence to 0.0."""


def extract_from_pdf(pdf_path: Path, doc_type: str) -> ExtractionResult:
    """Extract structured data from a PDF using Claude API.

    Args:
        pdf_path: Path to the PDF file.
        doc_type: "import" or "export".

    Returns:
        ExtractionResult with extracted entries and confidence scores.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    if not api_key or api_key == "your_anthropic_api_key_here":
        return ExtractionResult(
            doc_type=doc_type,
            error="ANTHROPIC_API_KEY not configured. Please set it in .env file.",
        )

    try:
        pdf_data = pdf_path.read_bytes()
        pdf_b64 = base64.standard_b64encode(pdf_data).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)

        prompt = IMPORT_EXTRACTION_PROMPT if doc_type == "import" else EXPORT_EXTRACTION_PROMPT

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
            raw_text=response_text if 'response_text' in dir() else None,
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


def extract_mock(doc_type: str) -> ExtractionResult:
    """Return mock extraction data for development/testing."""
    if doc_type == "import":
        return ExtractionResult(
            doc_type="import",
            import_entries=[
                ExtractedImportEntry(
                    consignor_exporter=ExtractedField(value="TECHNO RELIEF SERVICES - KENYA", confidence=0.95, source_text="TECHNO RELIEF SERVICES"),
                    description=ExtractedField(value="WATER PURIFICATION TABLETS(SODIUM DICHLOROISOCYANURATE)", confidence=0.9, source_text="WATER PURIFICATION TABLETS"),
                    import_file_number=ExtractedField(value="IMP/000", confidence=0.85, source_text="IMP/000"),
                    import_entry_date=ExtractedField(value="2025-01-31", confidence=0.9, source_text="31/01/2025"),
                    import_entry_number=ExtractedField(value="25NBOIM701162254", confidence=0.95, source_text="25NBOIM701162254"),
                    hs_code=ExtractedField(value="29336900", confidence=0.9, source_text="29336900"),
                    country=ExtractedField(value="KE", confidence=0.95, source_text="KENYA"),
                    supplementary_units=ExtractedField(value="300", confidence=0.8, source_text="300"),
                    unit=ExtractedField(value="KG", confidence=0.95, source_text="KG"),
                    quantity_imported=ExtractedField(value="8800", confidence=0.9, source_text="8,800"),
                    customs_value_kes=ExtractedField(value="26400", confidence=0.85, source_text="26,400.00"),
                    bif_value_kes=ExtractedField(value="0", confidence=0.5, source_text=""),
                ),
            ],
        )
    else:
        return ExtractionResult(
            doc_type="export",
            export_entries=[
                ExtractedExportEntry(
                    customer_name=ExtractedField(value="IFRC SRCS- GAROWE (SOMALIA)", confidence=0.9, source_text="IFRC SRCS GAROWE"),
                    export_file_number=ExtractedField(value="EXP/002", confidence=0.85, source_text="EXP/002"),
                    export_entry_date=ExtractedField(value="2025-02-27", confidence=0.9, source_text="27/02/2025"),
                    export_entry_number=ExtractedField(value="25NBOEX302333540", confidence=0.95, source_text="25NBOEX302333540"),
                    ppb_permit=ExtractedField(value=None, confidence=0.0, source_text=""),
                    supplementary_units_exported=ExtractedField(value="300", confidence=0.8, source_text="300"),
                    unit=ExtractedField(value="KG", confidence=0.95, source_text="KG"),
                    quantity_exported=ExtractedField(value="8800", confidence=0.9, source_text="8,800"),
                    customs_value_exported=ExtractedField(value="26400", confidence=0.85, source_text="26,400.00"),
                    bif_value_exported=ExtractedField(value="0", confidence=0.5, source_text=""),
                ),
            ],
        )
