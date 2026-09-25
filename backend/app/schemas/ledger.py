"""Pydantic schemas for import/export ledger operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Import Line schemas ---

class ImportLineBase(BaseModel):
    consignor_exporter: Optional[str] = None
    description: Optional[str] = None
    import_file_number: Optional[str] = None
    import_entry_date: Optional[date] = None
    import_entry_number: Optional[str] = None
    hs_code: Optional[str] = None
    country: Optional[str] = None
    supplementary_units: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity_imported: Decimal
    customs_value_kes: Decimal
    bif_value_kes: Optional[Decimal] = None


class ImportLineCreate(ImportLineBase):
    """Used when confirming an extracted import entry."""
    pass


class ExportLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    import_line_id: int
    customer_name: Optional[str] = None
    export_file_number: Optional[str] = None
    export_entry_date: Optional[date] = None
    export_entry_number: Optional[str] = None
    ppb_permit: Optional[str] = None
    supplementary_units_exported: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity_exported: Decimal
    customs_value_exported: Decimal
    bif_value_exported: Decimal
    is_legacy: bool
    created_at: datetime


class ImportLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    consignor_exporter: Optional[str] = None
    description: Optional[str] = None
    import_file_number: Optional[str] = None
    import_entry_date: Optional[date] = None
    import_entry_number: Optional[str] = None
    hs_code: Optional[str] = None
    country: Optional[str] = None
    supplementary_units: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity_imported: Decimal
    customs_value_kes: Decimal
    bif_value_kes: Optional[Decimal] = None
    balance_quantity: Decimal
    balance_customs_value: Decimal
    balance_bif_value: Decimal
    balance_supplementary_units: Optional[Decimal] = None
    is_legacy: bool
    created_at: datetime
    export_lines: list[ExportLineOut] = Field(default_factory=list)


class ImportLineSearch(BaseModel):
    """Query parameters for searching import lines."""
    entry_number: Optional[str] = None
    file_number: Optional[str] = None
    description: Optional[str] = None
    consignor: Optional[str] = None
    hs_code: Optional[str] = None
    country: Optional[str] = None
    open_balance_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class ImportLineSummary(BaseModel):
    """Compact import line for search results and matching candidates."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    consignor_exporter: Optional[str] = None
    description: Optional[str] = None
    import_file_number: Optional[str] = None
    import_entry_number: Optional[str] = None
    hs_code: Optional[str] = None
    country: Optional[str] = None
    unit: Optional[str] = None
    quantity_imported: Decimal
    customs_value_kes: Decimal
    balance_quantity: Decimal
    balance_customs_value: Decimal


# --- Export Line schemas ---

class ExportLineCreate(BaseModel):
    """Used when confirming an extracted export entry."""
    import_line_id: int
    customer_name: Optional[str] = None
    export_file_number: Optional[str] = None
    export_entry_date: Optional[date] = None
    export_entry_number: Optional[str] = None
    ppb_permit: Optional[str] = None
    supplementary_units_exported: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity_exported: Decimal
    # These will be calculated via proration if not provided
    customs_value_exported: Optional[Decimal] = None
    bif_value_exported: Optional[Decimal] = None


class ProrationPreview(BaseModel):
    """Preview of prorated values before confirming an export."""
    import_line_id: int
    import_quantity: Decimal
    import_customs_value: Decimal
    import_bif_value: Optional[Decimal] = None
    import_supplementary_units: Optional[Decimal] = None
    export_quantity: Decimal
    # Prorated values
    prorated_customs_value: Decimal
    prorated_bif_value: Decimal
    prorated_supplementary_units: Optional[Decimal] = None
    # Remaining after export
    remaining_quantity: Decimal
    remaining_customs_value: Decimal
    remaining_bif_value: Decimal
    remaining_supplementary_units: Optional[Decimal] = None
    # Warnings
    overdraft: bool = False
    overdraft_message: Optional[str] = None


# --- Upload / Extraction schemas ---

class UploadResponse(BaseModel):
    document_id: int
    filename: str
    doc_type: str
    duplicate: bool = False
    message: str


class ExtractedFieldOut(BaseModel):
    value: Optional[str] = None
    confidence: float = 0.0
    source_text: Optional[str] = None


class ExtractedImportEntryOut(BaseModel):
    consignor_exporter: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    description: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    import_file_number: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    import_entry_date: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    import_entry_number: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    hs_code: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    country: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    supplementary_units: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    unit: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    quantity_imported: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    customs_value_kes: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    bif_value_kes: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)


class ExtractedExportEntryOut(BaseModel):
    customer_name: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    export_file_number: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    export_entry_date: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    export_entry_number: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    ppb_permit: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    supplementary_units_exported: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    unit: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    quantity_exported: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    customs_value_exported: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)
    bif_value_exported: ExtractedFieldOut = Field(default_factory=ExtractedFieldOut)


class ExtractionResponse(BaseModel):
    document_id: int
    doc_type: str
    import_entries: list[ExtractedImportEntryOut] = Field(default_factory=list)
    export_entries: list[ExtractedExportEntryOut] = Field(default_factory=list)
    error: Optional[str] = None


# --- Audit log schemas ---

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_type: str
    entity_id: int
    change_type: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    source: str
    reason: Optional[str] = None
    user_id: Optional[int] = None
    created_at: datetime


class AuditLogQuery(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    user_id: Optional[int] = None
    change_type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


# --- Dashboard schemas ---

class DashboardStats(BaseModel):
    total_import_lines: int
    total_export_lines: int
    open_balance_lines: int
    total_documents: int
    recent_activity: list[AuditLogOut]


# --- Legacy import schema ---

class LegacyImportResult(BaseModel):
    import_lines_created: int
    export_lines_created: int
    skipped_empty: int
    warnings: list[str]
