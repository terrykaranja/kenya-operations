"""Export flow API – upload PDF, extract, match to import lines, prorate, and confirm."""

import hashlib
import os
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_admin
from app.extraction.extractor import extract_from_pdf, extract_mock
from app.models.audit_log import AuditLog
from app.models.export_line import ExportLine
from app.models.import_line import ImportLine
from app.models.source_document import SourceDocument
from app.models.user import User
from app.resources import RESOURCES_DIR
from app.schemas.ledger import (
    ExportLineCreate,
    ExportLineOut,
    ExtractionResponse,
    ImportLineSummary,
    ProrationPreview,
    UploadResponse,
)

router = APIRouter(prefix="/api/export", tags=["export"])

UPLOADS_DIR = RESOURCES_DIR / "uploads"


def _ensure_uploads_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_export_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload an export PDF document for extraction."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    max_size = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"File exceeds {max_size // (1024*1024)}MB limit")

    file_hash = hashlib.sha256(content).hexdigest()

    existing = db.query(SourceDocument).filter(SourceDocument.file_hash == file_hash).first()
    if existing:
        return UploadResponse(
            document_id=existing.id,
            filename=file.filename,
            doc_type="export",
            duplicate=True,
            message="This file has already been uploaded.",
        )

    _ensure_uploads_dir()
    storage_name = f"{file_hash[:12]}_{file.filename}"
    storage_path = UPLOADS_DIR / storage_name
    storage_path.write_bytes(content)

    doc = SourceDocument(
        doc_type="export",
        original_filename=file.filename,
        storage_path=str(storage_path),
        file_hash=file_hash,
        uploaded_by_id=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return UploadResponse(
        document_id=doc.id,
        filename=file.filename,
        doc_type="export",
        message="File uploaded successfully. Call /api/export/extract to extract data.",
    )


@router.post("/extract/{document_id}", response_model=ExtractionResponse)
def extract_export_data(
    document_id: int,
    use_mock: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExtractionResponse:
    """Extract structured export data from an uploaded PDF."""
    doc = db.get(SourceDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.doc_type != "export":
        raise HTTPException(status_code=400, detail="Document is not an export document")

    if use_mock:
        result = extract_mock("export")
    else:
        pdf_path = Path(doc.storage_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        result = extract_from_pdf(pdf_path, "export")

    if result.error:
        return ExtractionResponse(
            document_id=document_id,
            doc_type="export",
            error=result.error,
        )

    return ExtractionResponse(
        document_id=document_id,
        doc_type="export",
        export_entries=[entry.model_dump() for entry in result.export_entries],
    )


@router.get("/match-candidates", response_model=list[ImportLineSummary])
def get_match_candidates(
    hs_code: Optional[str] = None,
    description: Optional[str] = None,
    consignor: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ImportLineSummary]:
    """Find import lines that could match an export entry.

    Filters by HS code, description, or consignor, and only returns
    lines with positive remaining balance.
    """
    query = db.query(ImportLine).filter(ImportLine.balance_quantity > 0)

    if hs_code:
        query = query.filter(ImportLine.hs_code == hs_code)
    if description:
        query = query.filter(ImportLine.description.ilike(f"%{description}%"))
    if consignor:
        query = query.filter(ImportLine.consignor_exporter.ilike(f"%{consignor}%"))

    candidates = query.order_by(ImportLine.import_entry_date.asc()).limit(50).all()
    return candidates


@router.post("/preview-proration", response_model=ProrationPreview)
def preview_proration(
    import_line_id: int,
    quantity_exported: Decimal,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProrationPreview:
    """Preview prorated values before confirming an export.

    Proration formulas:
        U (customs value exported) = K × T / J
        V (BIF value exported) = L × T / J
        R (supplementary units exported) = H × T / J
    Where J = quantity_imported, T = quantity_exported, K = customs_value, L = BIF value, H = supp units
    """
    imp = db.get(ImportLine, import_line_id)
    if not imp:
        raise HTTPException(status_code=404, detail="Import line not found")

    if imp.quantity_imported == 0:
        raise HTTPException(status_code=400, detail="Cannot prorate: import quantity is zero (J=0)")

    ratio = quantity_exported / imp.quantity_imported

    prorated_customs = imp.customs_value_kes * ratio
    prorated_bif = (imp.bif_value_kes or Decimal("0")) * ratio
    prorated_supp = (imp.supplementary_units or Decimal("0")) * ratio if imp.supplementary_units else None

    remaining_qty = imp.balance_quantity - quantity_exported
    remaining_customs = imp.balance_customs_value - prorated_customs
    remaining_bif = imp.balance_bif_value - prorated_bif
    remaining_supp = None
    if imp.balance_supplementary_units is not None and prorated_supp is not None:
        remaining_supp = imp.balance_supplementary_units - prorated_supp

    overdraft = remaining_qty < 0
    overdraft_msg = None
    if overdraft:
        overdraft_msg = (
            f"Export quantity ({quantity_exported}) exceeds remaining balance "
            f"({imp.balance_quantity}). Admin override required."
        )

    return ProrationPreview(
        import_line_id=import_line_id,
        import_quantity=imp.quantity_imported,
        import_customs_value=imp.customs_value_kes,
        import_bif_value=imp.bif_value_kes,
        import_supplementary_units=imp.supplementary_units,
        export_quantity=quantity_exported,
        prorated_customs_value=round(prorated_customs, 4),
        prorated_bif_value=round(prorated_bif, 4),
        prorated_supplementary_units=round(prorated_supp, 4) if prorated_supp else None,
        remaining_quantity=remaining_qty,
        remaining_customs_value=round(remaining_customs, 4),
        remaining_bif_value=round(remaining_bif, 4),
        remaining_supplementary_units=round(remaining_supp, 4) if remaining_supp is not None else None,
        overdraft=overdraft,
        overdraft_message=overdraft_msg,
    )


@router.post("/confirm", response_model=list[ExportLineOut])
def confirm_export(
    entries: list[ExportLineCreate],
    source_document_id: Optional[int] = Query(None),
    admin_override: bool = Query(False, description="Allow overdraft with admin override"),
    override_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExportLineOut]:
    """Confirm and store export entries, updating import line balances.

    Proration is automatically calculated if customs_value_exported or
    bif_value_exported are not provided.
    """
    created = []

    for entry in entries:
        imp = db.get(ImportLine, entry.import_line_id)
        if not imp:
            raise HTTPException(
                status_code=404,
                detail=f"Import line {entry.import_line_id} not found",
            )

        if imp.quantity_imported == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Import line {entry.import_line_id}: quantity is zero, cannot prorate",
            )

        # Calculate prorated values if not provided
        ratio = entry.quantity_exported / imp.quantity_imported

        customs_exported = entry.customs_value_exported
        if customs_exported is None:
            customs_exported = round(imp.customs_value_kes * ratio, 4)

        bif_exported = entry.bif_value_exported
        if bif_exported is None:
            bif_exported = round((imp.bif_value_kes or Decimal("0")) * ratio, 4)

        supp_exported = entry.supplementary_units_exported
        if supp_exported is None and imp.supplementary_units:
            supp_exported = round(imp.supplementary_units * ratio, 4)

        # Check overdraft
        new_balance_qty = imp.balance_quantity - entry.quantity_exported
        if new_balance_qty < 0 and not admin_override:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Export quantity ({entry.quantity_exported}) exceeds remaining balance "
                    f"({imp.balance_quantity}) for import line {imp.id}. "
                    f"Use admin_override=true with a reason to proceed."
                ),
            )

        if new_balance_qty < 0 and admin_override:
            if not user.is_admin:
                raise HTTPException(status_code=403, detail="Admin override requires admin privileges")
            if not override_reason:
                raise HTTPException(status_code=400, detail="Override reason is required for overdraft")
            db.add(AuditLog(
                entity_type="import_line",
                entity_id=imp.id,
                change_type="override",
                field_name="balance_quantity",
                old_value=str(imp.balance_quantity),
                new_value=str(new_balance_qty),
                source="human_corrected",
                reason=override_reason,
                user_id=user.id,
            ))

        # Update import line balances
        imp.balance_quantity = new_balance_qty
        imp.balance_customs_value -= customs_exported
        imp.balance_bif_value -= bif_exported
        if imp.balance_supplementary_units is not None and supp_exported is not None:
            imp.balance_supplementary_units -= supp_exported

        # Create export line
        export_line = ExportLine(
            import_line_id=imp.id,
            source_document_id=source_document_id,
            is_legacy=False,
            customer_name=entry.customer_name,
            export_file_number=entry.export_file_number,
            export_entry_date=entry.export_entry_date,
            export_entry_number=entry.export_entry_number,
            ppb_permit=entry.ppb_permit,
            supplementary_units_exported=supp_exported,
            unit=entry.unit,
            quantity_exported=entry.quantity_exported,
            customs_value_exported=customs_exported,
            bif_value_exported=bif_exported,
            created_by_id=user.id,
        )
        db.add(export_line)
        db.flush()

        db.add(AuditLog(
            entity_type="export_line",
            entity_id=export_line.id,
            change_type="create",
            source="human_corrected",
            user_id=user.id,
            new_value=f"Export confirmed against import {imp.id}: qty={entry.quantity_exported}",
        ))

        created.append(export_line)

    db.commit()
    for exp in created:
        db.refresh(exp)

    return created


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_export(
    export_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    """Delete an export line and restore the import line balance. Admin only."""
    export_line = db.get(ExportLine, export_id)
    if not export_line:
        raise HTTPException(status_code=404, detail="Export line not found")

    imp = db.get(ImportLine, export_line.import_line_id)
    if imp:
        # Restore balances
        imp.balance_quantity += export_line.quantity_exported
        imp.balance_customs_value += export_line.customs_value_exported
        imp.balance_bif_value += export_line.bif_value_exported
        if imp.balance_supplementary_units is not None and export_line.supplementary_units_exported:
            imp.balance_supplementary_units += export_line.supplementary_units_exported

    db.add(AuditLog(
        entity_type="export_line",
        entity_id=export_line.id,
        change_type="delete",
        source="human_corrected",
        user_id=user.id,
        old_value=f"Deleted export: qty={export_line.quantity_exported}, import_line={export_line.import_line_id}",
    ))

    db.delete(export_line)
    db.commit()
