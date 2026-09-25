"""Legacy Excel parser – reads the SEZ stock ledger workbook and reconstructs
import groups with their associated export sub-rows.

The parser handles the "blank continuation" pattern where columns A-E are blank
on the 2nd+ items within the same import group, and export rows (M-V filled)
appear on the same row as their parent import or on subsequent rows.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import openpyxl


@dataclass
class ParsedExportRow:
    """Data extracted from columns M-V of one ledger row."""
    row_number: int
    customer_name: Optional[str] = None
    export_file_number: Optional[str] = None
    export_entry_date: Optional[date] = None
    export_entry_number: Optional[str] = None
    ppb_permit: Optional[str] = None
    supplementary_units_exported: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity_exported: Optional[Decimal] = None
    customs_value_exported: Optional[Decimal] = None
    bif_value_exported: Optional[Decimal] = None


@dataclass
class ParsedImportRow:
    """Data extracted from columns A-L of one ledger row, plus child exports."""
    row_number: int
    consignor_exporter: Optional[str] = None
    description: Optional[str] = None
    import_file_number: Optional[str] = None
    import_entry_date: Optional[date] = None
    import_entry_number: Optional[str] = None
    hs_code: Optional[str] = None
    country: Optional[str] = None
    supplementary_units: Optional[Decimal] = None
    unit: Optional[str] = None
    quantity_imported: Optional[Decimal] = None
    customs_value_kes: Optional[Decimal] = None
    bif_value_kes: Optional[Decimal] = None
    exports: list[ParsedExportRow] = field(default_factory=list)


def _to_decimal(val) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def _to_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def _to_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _has_import_data(row_cells: dict) -> bool:
    """Return True if this row has any import-side data (A-L) worth capturing."""
    # A row is an import row if it has quantity (J) or HS code (F) or entry number (E)
    return any(row_cells.get(col) is not None for col in ["J", "F", "E", "C", "A"])


def _has_export_data(row_cells: dict) -> bool:
    """Return True if this row has export-side data (M-V)."""
    return any(row_cells.get(col) is not None for col in ["M", "T", "P", "N"])


def _is_new_import_group(row_cells: dict) -> bool:
    """A new import group starts when column A (consignor) is populated,
    OR when column C (file number) is populated and looks different from
    a continuation row."""
    return row_cells.get("A") is not None or row_cells.get("C") is not None


def parse_export_row(row_num: int, cells: dict) -> ParsedExportRow:
    return ParsedExportRow(
        row_number=row_num,
        customer_name=_to_str(cells.get("M")),
        export_file_number=_to_str(cells.get("N")),
        export_entry_date=_to_date(cells.get("O")),
        export_entry_number=_to_str(cells.get("P")),
        ppb_permit=_to_str(cells.get("Q")),
        supplementary_units_exported=_to_decimal(cells.get("R")),
        unit=_to_str(cells.get("S")),
        quantity_exported=_to_decimal(cells.get("T")),
        customs_value_exported=_to_decimal(cells.get("U")),
        bif_value_exported=_to_decimal(cells.get("V")),
    )


def parse_import_row(row_num: int, cells: dict) -> ParsedImportRow:
    return ParsedImportRow(
        row_number=row_num,
        consignor_exporter=_to_str(cells.get("A")),
        description=_to_str(cells.get("B")),
        import_file_number=_to_str(cells.get("C")),
        import_entry_date=_to_date(cells.get("D")),
        import_entry_number=_to_str(cells.get("E")),
        hs_code=_to_str(cells.get("F")),
        country=_to_str(cells.get("G")),
        supplementary_units=_to_decimal(cells.get("H")),
        unit=_to_str(cells.get("I")),
        quantity_imported=_to_decimal(cells.get("J")),
        customs_value_kes=_to_decimal(cells.get("K")),
        bif_value_kes=_to_decimal(cells.get("L")),
    )


COL_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def parse_ledger(path: Path) -> list[ParsedImportRow]:
    """Parse the SEZ stock ledger Excel file and return a list of import groups.

    Each ParsedImportRow contains the import-side data and a list of associated
    ParsedExportRow objects. The parser handles:
    - Blank continuation rows (A-E blank on 2nd+ items)
    - Export rows on the same row as the import
    - Multiple export rows per import group
    - Formula cells (reads cached values via data_only=True)
    """
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    ws = wb["Sheet1"]

    imports: list[ParsedImportRow] = []
    current_import: Optional[ParsedImportRow] = None

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
        cells: dict = {}
        for cell in row:
            col_letter = cell.column_letter if hasattr(cell, 'column_letter') else COL_LETTERS[cell.column - 1] if hasattr(cell, 'column') else None
            if col_letter:
                cells[col_letter] = cell.value

        has_import = _has_import_data(cells)
        has_export = _has_export_data(cells)

        if not has_import and not has_export:
            continue

        if has_import and _is_new_import_group(cells):
            current_import = parse_import_row(row_idx, cells)
            imports.append(current_import)
            if has_export:
                current_import.exports.append(parse_export_row(row_idx, cells))
        elif has_import and current_import is not None:
            # Continuation row with import data but no new group marker
            # This is a separate import line within the same conceptual group
            new_import = parse_import_row(row_idx, cells)
            # Inherit consignor/file info from parent if blank
            if new_import.consignor_exporter is None:
                new_import.consignor_exporter = current_import.consignor_exporter
            if new_import.import_file_number is None:
                new_import.import_file_number = current_import.import_file_number
            if new_import.import_entry_date is None:
                new_import.import_entry_date = current_import.import_entry_date
            if new_import.import_entry_number is None:
                new_import.import_entry_number = current_import.import_entry_number
            imports.append(new_import)
            current_import = new_import
            if has_export:
                current_import.exports.append(parse_export_row(row_idx, cells))
        elif has_export and current_import is not None:
            # Export-only row, attach to current import
            current_import.exports.append(parse_export_row(row_idx, cells))
        elif has_export and current_import is None:
            # Orphan export row — shouldn't happen but handle gracefully
            pass

    wb.close()
    return imports
