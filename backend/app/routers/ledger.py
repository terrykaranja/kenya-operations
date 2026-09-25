"""Search, audit log, download, and dashboard endpoints."""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.deps import get_current_user, get_db, require_admin
from app.excel.generator import generate_ledger
from app.excel.importer import import_legacy_data
from app.models.audit_log import AuditLog
from app.models.export_line import ExportLine
from app.models.import_line import ImportLine
from app.models.source_document import SourceDocument
from app.models.user import User
from app.resources import resource_path
from app.schemas.ledger import (
    AuditLogOut,
    AuditLogQuery,
    DashboardStats,
    ImportLineOut,
    ImportLineSummary,
    LegacyImportResult,
)

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


# --- Dashboard ---

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardStats:
    """Get dashboard statistics."""
    total_imports = db.query(func.count(ImportLine.id)).scalar() or 0
    total_exports = db.query(func.count(ExportLine.id)).scalar() or 0
    open_balance = db.query(func.count(ImportLine.id)).filter(
        ImportLine.balance_quantity > 0
    ).scalar() or 0
    total_docs = db.query(func.count(SourceDocument.id)).scalar() or 0

    recent = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )

    return DashboardStats(
        total_import_lines=total_imports,
        total_export_lines=total_exports,
        open_balance_lines=open_balance,
        total_documents=total_docs,
        recent_activity=recent,
    )


# --- Search ---

@router.get("/search", response_model=list[ImportLineSummary])
def search_import_lines(
    entry_number: Optional[str] = None,
    file_number: Optional[str] = None,
    description: Optional[str] = None,
    consignor: Optional[str] = None,
    hs_code: Optional[str] = None,
    country: Optional[str] = None,
    open_balance_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ImportLineSummary]:
    """Search import lines with various filters."""
    query = db.query(ImportLine)

    if entry_number:
        query = query.filter(ImportLine.import_entry_number.ilike(f"%{entry_number}%"))
    if file_number:
        query = query.filter(ImportLine.import_file_number.ilike(f"%{file_number}%"))
    if description:
        query = query.filter(ImportLine.description.ilike(f"%{description}%"))
    if consignor:
        query = query.filter(ImportLine.consignor_exporter.ilike(f"%{consignor}%"))
    if hs_code:
        query = query.filter(ImportLine.hs_code == hs_code)
    if country:
        query = query.filter(ImportLine.country == country)
    if open_balance_only:
        query = query.filter(ImportLine.balance_quantity > 0)

    offset = (page - 1) * page_size
    results = query.order_by(ImportLine.id.desc()).offset(offset).limit(page_size).all()
    return results


@router.get("/import-lines/{import_line_id}", response_model=ImportLineOut)
def get_import_line_detail(
    import_line_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ImportLineOut:
    """Get full details of an import line including its exports."""
    imp = (
        db.query(ImportLine)
        .options(joinedload(ImportLine.export_lines))
        .filter(ImportLine.id == import_line_id)
        .first()
    )
    if not imp:
        raise HTTPException(status_code=404, detail="Import line not found")
    return imp


# --- Audit Log ---

@router.get("/audit", response_model=list[AuditLogOut])
def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    change_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditLogOut]:
    """Query audit log entries with filters."""
    query = db.query(AuditLog)

    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if change_type:
        query = query.filter(AuditLog.change_type == change_type)

    offset = (page - 1) * page_size
    results = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
    return results


@router.get("/audit/export")
def export_audit_csv(
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Export audit log as CSV. Admin only."""
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    logs = query.order_by(AuditLog.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Entity Type", "Entity ID", "Change Type", "Field",
        "Old Value", "New Value", "Source", "Reason", "User ID", "Timestamp",
    ])
    for log in logs:
        writer.writerow([
            log.id, log.entity_type, log.entity_id, log.change_type,
            log.field_name, log.old_value, log.new_value, log.source,
            log.reason, log.user_id, log.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )


# --- Raw entries CSV export ---

@router.get("/entries/export")
def export_entries_csv(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Export every uploaded import and export entry as CSV. Admin only.

    Unlike /download (which renders the formatted SEZ ledger workbook),
    this is a flat dump of every ImportLine and ExportLine row, useful for
    ad-hoc reporting/auditing of everything that's been uploaded so far.
    """
    import_lines = db.query(ImportLine).order_by(ImportLine.id).all()
    export_lines = (
        db.query(ExportLine)
        .options(joinedload(ExportLine.import_line))
        .order_by(ExportLine.id)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["IMPORT ENTRIES"])
    writer.writerow([
        "ID", "Legacy", "Consignor/Exporter", "Description", "File Number",
        "Entry Date", "Entry Number", "HS Code", "Country", "Supplementary Units",
        "Unit", "Qty Imported", "Customs Value (KES)", "BIF Value (KES)",
        "Balance Qty", "Balance Customs Value", "Balance BIF Value",
        "Balance Supplementary Units", "Uploaded At",
    ])
    for line in import_lines:
        writer.writerow([
            line.id, line.is_legacy, line.consignor_exporter, line.description,
            line.import_file_number,
            line.import_entry_date.isoformat() if line.import_entry_date else None,
            line.import_entry_number, line.hs_code, line.country,
            line.supplementary_units, line.unit, line.quantity_imported,
            line.customs_value_kes, line.bif_value_kes, line.balance_quantity,
            line.balance_customs_value, line.balance_bif_value,
            line.balance_supplementary_units, line.created_at.isoformat(),
        ])

    writer.writerow([])
    writer.writerow(["EXPORT ENTRIES"])
    writer.writerow([
        "ID", "Import Line ID", "Legacy", "Customer Name", "File Number",
        "Entry Date", "Entry Number", "PPB Permit", "Supplementary Units",
        "Unit", "Qty Exported", "Customs Value Exported", "BIF Value Exported",
        "Uploaded At",
    ])
    for line in export_lines:
        writer.writerow([
            line.id, line.import_line_id, line.is_legacy, line.customer_name,
            line.export_file_number,
            line.export_entry_date.isoformat() if line.export_entry_date else None,
            line.export_entry_number, line.ppb_permit,
            line.supplementary_units_exported, line.unit, line.quantity_exported,
            line.customs_value_exported, line.bif_value_exported,
            line.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sez_ledger_entries.csv"},
    )


# --- Excel Download ---

@router.get("/download")
def download_ledger(
    style: str = Query("blank_continuation", pattern="^(blank_continuation|fully_populated)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download the complete SEZ stock ledger as an Excel file."""
    buffer = generate_ledger(db, style=style)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=SEZ_Stock_Ledger.xlsx",
        },
    )


# --- Legacy Import ---

@router.post("/import-legacy", response_model=LegacyImportResult)
def run_legacy_import(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> LegacyImportResult:
    """Import legacy data from the Excel file. Admin only.

    Reads from resources/Seza_Stock_Ledger_Hackathon.xlsx.
    """
    xlsx_path = resource_path("Seza_Stock_Ledger_Hackathon.xlsx")
    if not xlsx_path.exists():
        raise HTTPException(status_code=404, detail="Legacy Excel file not found in resources/")

    # Check for existing legacy data
    existing = db.query(ImportLine).filter(ImportLine.is_legacy == True).count()
    if existing > 0:
        raise HTTPException(
            status_code=409,
            detail=f"{existing} legacy import lines already exist. Delete them first to re-import.",
        )

    stats = import_legacy_data(db, xlsx_path)
    return LegacyImportResult(**stats)
