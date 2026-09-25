"""Excel generator – creates a formatted SEZ stock ledger workbook from database records.

Replicates the exact formatting, formulas, and structure of the original ledger file.
Supports two output styles:
  - blank_continuation: Leaves A-E blank on continuation rows (default, matches legacy)
  - fully_populated: Fills all columns on every row
"""

from decimal import Decimal
from io import BytesIO
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, numbers
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.models.export_line import ExportLine
from app.models.import_line import ImportLine

# --- Style constants matching the original ledger ---

HEADER_FONT = Font(name="Calibri", bold=True, size=11)
DATA_FONT = Font(name="Calibri", size=11)
HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
BALANCE_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
WRAP_ALIGN = Alignment(wrap_text=True, vertical="top")
ACCOUNTING_FORMAT = '#,##0.00'

HEADERS = [
    "Consignor / Exporter",              # A
    "Description",                        # B
    "Import File Number",                 # C
    "Import Entry Date",                  # D
    "Import Entry Number",                # E
    "HS code",                            # F
    "Country",                            # G
    "Supplementary Units (41a)",          # H
    "Unit",                               # I
    "Quantity Imported (Repackaged)",      # J
    "Customs Value KES",                  # K
    "BIF Value KES",                      # L
    "Customer Name",                      # M
    "Export File Number",                 # N
    "Export Entry Date",                  # O
    "Export Entry Number",                # P
    "PPB Approved Export Permit App",     # Q
    "Supplementary Units (41a)",          # R
    "Unit",                               # S
    "Quantity Exported",                  # T
    "Customs Value",                      # U
    "BIF Value KES",                      # V
    "Balance Quantity currently in SEZ",  # W
    "Balance Customs Value",             # X
    "BIF Value KES",                      # Y
    "Balance Supplementary Units (41a)",  # Z
]

COLUMN_WIDTHS = {
    "A": 37.1, "B": 142.4, "C": 13.4, "D": 17.4, "E": 23.1,
    "F": 13.1, "G": 10.7, "H": 15.4, "I": 11.1, "J": 16.4,
    "K": 15.6, "L": 15.6, "M": 55.0, "N": 10.6, "O": 17.0,
    "P": 28.9, "Q": 26.0, "R": 15.1, "S": 10.6, "T": 13.6,
    "U": 16.4, "V": 15.7, "W": 16.7, "X": 16.7, "Y": 15.6, "Z": 16.1,
}

NUMERIC_COLS = {"H", "J", "K", "L", "R", "T", "U", "V", "W", "X", "Y", "Z"}
DATE_COLS = {"D", "O"}
BALANCE_COLS = {"W", "X", "Y", "Z"}


def _setup_headers(ws) -> None:
    for col_idx, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        cell.alignment = WRAP_ALIGN

    for letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[letter].width = width

    # Hide column Q (PPB permit) as in original
    ws.column_dimensions["Q"].hidden = True


def _apply_cell_style(cell, col_letter: str, is_balance: bool = False) -> None:
    cell.font = DATA_FONT
    cell.border = THIN_BORDER
    if col_letter in NUMERIC_COLS:
        cell.number_format = ACCOUNTING_FORMAT
    if col_letter in DATE_COLS:
        cell.number_format = 'YYYY-MM-DD'
    if is_balance or col_letter in BALANCE_COLS:
        cell.fill = BALANCE_FILL


def generate_ledger(
    db: Session,
    style: str = "blank_continuation",
) -> BytesIO:
    """Generate a complete SEZ stock ledger workbook from the database.

    Args:
        db: Database session.
        style: "blank_continuation" (default) or "fully_populated".

    Returns:
        BytesIO buffer containing the .xlsx file.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    _setup_headers(ws)

    # Fetch all import lines ordered by row_order (legacy) or id
    import_lines = (
        db.query(ImportLine)
        .order_by(ImportLine.row_order.asc().nullslast(), ImportLine.id.asc())
        .all()
    )

    current_row = 2
    prev_consignor = None
    prev_file_number = None
    prev_entry_date = None
    prev_entry_number = None

    for imp in import_lines:
        exports = (
            db.query(ExportLine)
            .filter(ExportLine.import_line_id == imp.id)
            .order_by(ExportLine.row_order.asc().nullslast(), ExportLine.id.asc())
            .all()
        )

        import_start_row = current_row

        # Determine if this is a continuation (same consignor group)
        is_continuation = (
            style == "blank_continuation"
            and prev_consignor == imp.consignor_exporter
            and prev_file_number == imp.import_file_number
            and imp.consignor_exporter is not None
        )

        # Write import-side data (A-L)
        col_map = {
            "A": imp.consignor_exporter if not is_continuation else None,
            "B": imp.description,
            "C": imp.import_file_number if not is_continuation else None,
            "D": imp.import_entry_date if not is_continuation else None,
            "E": imp.import_entry_number if not is_continuation else None,
            "F": imp.hs_code,
            "G": imp.country,
            "H": imp.supplementary_units,
            "I": imp.unit,
            "J": imp.quantity_imported,
            "K": imp.customs_value_kes,
            "L": imp.bif_value_kes,
        }

        for col_letter, value in col_map.items():
            col_idx = ord(col_letter) - ord("A") + 1
            cell = ws.cell(row=current_row, column=col_idx, value=value)
            _apply_cell_style(cell, col_letter)

        # Write first export on same row if exists
        if exports:
            exp = exports[0]
            _write_export_row(ws, current_row, exp)
            _write_balance_formulas(ws, current_row, import_start_row, [current_row])
        else:
            # No exports — balance = full import values
            _write_balance_no_exports(ws, current_row, imp)

        current_row += 1

        # Write additional exports on subsequent rows
        export_rows = [import_start_row]
        for exp in exports[1:]:
            _write_export_row(ws, current_row, exp)
            export_rows.append(current_row)
            current_row += 1

        # Rewrite balance formulas with all export rows
        if len(exports) > 1:
            _write_balance_formulas(ws, import_start_row, import_start_row, export_rows)

        prev_consignor = imp.consignor_exporter
        prev_file_number = imp.import_file_number
        prev_entry_date = imp.import_entry_date
        prev_entry_number = imp.import_entry_number

    # Freeze panes
    ws.freeze_panes = f"A{min(current_row, 552)}"

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _write_export_row(ws, row: int, exp: ExportLine) -> None:
    export_map = {
        "M": exp.customer_name,
        "N": exp.export_file_number,
        "O": exp.export_entry_date,
        "P": exp.export_entry_number,
        "Q": exp.ppb_permit,
        "R": exp.supplementary_units_exported,
        "S": exp.unit,
        "T": exp.quantity_exported,
        "U": exp.customs_value_exported,
        "V": exp.bif_value_exported,
    }
    for col_letter, value in export_map.items():
        col_idx = ord(col_letter) - ord("A") + 1
        cell = ws.cell(row=row, column=col_idx, value=value)
        _apply_cell_style(cell, col_letter)


def _write_balance_formulas(ws, import_row: int, data_row: int, export_rows: list[int]) -> None:
    """Write W/X/Y/Z balance formulas.

    W = J - SUM(T exports)
    X = K - SUM(U exports)
    Y = L - SUM(V exports)
    Z = H - SUM(R exports)
    """
    if len(export_rows) == 1:
        er = export_rows[0]
        w_formula = f"=J{data_row}-T{er}"
        x_formula = f"=K{data_row}-U{er}"
        y_formula = f"=L{data_row}-V{er}"
        z_formula = f"=H{data_row}-R{er}"
    else:
        t_refs = "-".join(f"T{r}" for r in export_rows)
        u_refs = "-".join(f"U{r}" for r in export_rows)
        v_refs = "-".join(f"V{r}" for r in export_rows)
        r_refs = "-".join(f"R{r}" for r in export_rows)
        w_formula = f"=J{data_row}-{t_refs}"
        x_formula = f"=K{data_row}-{u_refs}"
        y_formula = f"=L{data_row}-{v_refs}"
        z_formula = f"=H{data_row}-{r_refs}"

    formulas = {"W": w_formula, "X": x_formula, "Y": y_formula, "Z": z_formula}
    for col_letter, formula in formulas.items():
        col_idx = ord(col_letter) - ord("A") + 1
        cell = ws.cell(row=import_row, column=col_idx, value=formula)
        _apply_cell_style(cell, col_letter, is_balance=True)


def _write_balance_no_exports(ws, row: int, imp: ImportLine) -> None:
    """When there are no exports, balance equals the import values."""
    balance_map = {
        "W": f"=J{row}",
        "X": f"=K{row}",
        "Y": f"=L{row}",
        "Z": f"=H{row}",
    }
    for col_letter, formula in balance_map.items():
        col_idx = ord(col_letter) - ord("A") + 1
        cell = ws.cell(row=row, column=col_idx, value=formula)
        _apply_cell_style(cell, col_letter, is_balance=True)
