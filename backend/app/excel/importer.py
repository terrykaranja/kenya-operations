"""Legacy import – reads the parsed Excel data and creates database records.

Usage:
    python -m app.excel.importer resources/Seza_Stock_Ledger_Hackathon.xlsx
"""

import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.export_line import ExportLine
from app.models.import_line import ImportLine
from app.excel.parser import ParsedImportRow, parse_ledger


def _dec(val, default="0") -> Decimal:
    """Convert to Decimal, defaulting to 0 if None."""
    if val is None:
        return Decimal(default)
    return val


def import_legacy_data(db: Session, path: Path) -> dict:
    """Import legacy Excel data into the database.

    Returns a summary dict with counts and any discrepancies.
    """
    parsed = parse_ledger(path)

    stats = {
        "import_lines_created": 0,
        "export_lines_created": 0,
        "skipped_empty": 0,
        "warnings": [],
    }

    for parsed_import in parsed:
        if parsed_import.quantity_imported is None and parsed_import.customs_value_kes is None:
            stats["skipped_empty"] += 1
            continue

        qty = _dec(parsed_import.quantity_imported)
        customs = _dec(parsed_import.customs_value_kes)
        bif = _dec(parsed_import.bif_value_kes)
        supp = parsed_import.supplementary_units

        # Calculate total exported quantities for balance
        total_qty_exported = Decimal("0")
        total_customs_exported = Decimal("0")
        total_bif_exported = Decimal("0")
        total_supp_exported = Decimal("0")

        for exp in parsed_import.exports:
            total_qty_exported += _dec(exp.quantity_exported)
            total_customs_exported += _dec(exp.customs_value_exported)
            total_bif_exported += _dec(exp.bif_value_exported)
            total_supp_exported += _dec(exp.supplementary_units_exported)

        import_line = ImportLine(
            is_legacy=True,
            row_order=parsed_import.row_number,
            consignor_exporter=parsed_import.consignor_exporter,
            description=parsed_import.description,
            import_file_number=parsed_import.import_file_number,
            import_entry_date=parsed_import.import_entry_date,
            import_entry_number=parsed_import.import_entry_number,
            hs_code=parsed_import.hs_code,
            country=parsed_import.country,
            supplementary_units=supp,
            unit=parsed_import.unit,
            quantity_imported=qty,
            customs_value_kes=customs,
            bif_value_kes=bif,
            # Balances = import - total exports
            balance_quantity=qty - total_qty_exported,
            balance_customs_value=customs - total_customs_exported,
            balance_bif_value=bif - total_bif_exported,
            balance_supplementary_units=(_dec(supp) - total_supp_exported) if supp else None,
        )
        db.add(import_line)
        db.flush()  # Get the ID

        stats["import_lines_created"] += 1

        # Create audit log for import
        db.add(AuditLog(
            entity_type="import_line",
            entity_id=import_line.id,
            change_type="create",
            source="system",
            new_value=f"Legacy import from row {parsed_import.row_number}",
        ))

        # Create export lines
        for exp in parsed_import.exports:
            if exp.quantity_exported is None:
                continue

            export_line = ExportLine(
                import_line_id=import_line.id,
                is_legacy=True,
                row_order=exp.row_number,
                customer_name=exp.customer_name,
                export_file_number=exp.export_file_number,
                export_entry_date=exp.export_entry_date,
                export_entry_number=exp.export_entry_number,
                ppb_permit=exp.ppb_permit,
                supplementary_units_exported=exp.supplementary_units_exported,
                unit=exp.unit,
                quantity_exported=_dec(exp.quantity_exported),
                customs_value_exported=_dec(exp.customs_value_exported),
                bif_value_exported=_dec(exp.bif_value_exported),
            )
            db.add(export_line)
            db.flush()
            stats["export_lines_created"] += 1

            db.add(AuditLog(
                entity_type="export_line",
                entity_id=export_line.id,
                change_type="create",
                source="system",
                new_value=f"Legacy import from row {exp.row_number}",
            ))

        # Check for negative balances
        if import_line.balance_quantity < 0:
            stats["warnings"].append(
                f"Row {parsed_import.row_number}: negative balance_quantity "
                f"({import_line.balance_quantity})"
            )

    db.commit()
    return stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.excel.importer <path_to_excel>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if legacy data already exists
        existing = db.query(ImportLine).filter(ImportLine.is_legacy == True).count()
        if existing > 0:
            print(f"Warning: {existing} legacy import lines already exist.")
            print("Skipping import to avoid duplicates. Delete existing data first.")
            sys.exit(1)

        print(f"Parsing {path}...")
        stats = import_legacy_data(db, path)
        print(f"Import complete:")
        print(f"  Import lines created: {stats['import_lines_created']}")
        print(f"  Export lines created: {stats['export_lines_created']}")
        print(f"  Skipped empty rows: {stats['skipped_empty']}")
        if stats["warnings"]:
            print(f"  Warnings:")
            for w in stats["warnings"]:
                print(f"    - {w}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
