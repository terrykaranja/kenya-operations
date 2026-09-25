"""Import flow API – upload PDF, extract data, review, and confirm import entries."""

import hashlib
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.extraction.extractor import extract_from_pdf, extract_mock
from app.models.audit_log import AuditLog
from app.models.import_line import ImportLine
from app.models.source_document import SourceDocument
from app.models.user import User
from app.resources import RESOURCES_DIR
from app.schemas.ledger import (
    ExtractionResponse,
    ImportLineCreate,
    ImportLineOut,
    UploadResponse,
)

router = APIRouter(prefix="/api/import", tags=["import"])

UPLOADS_DIR = RESOURCES_DIR / "uploads"


def _ensure_uploads_dir():
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_import_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadResponse:
    """Upload an import PDF document for extraction."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    max_size = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")) * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail=f"File exceeds {max_size // (1024*1024)}MB limit")

    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate (scoped to doc_type: the same PDF bytes can
    # legitimately be uploaded once as an import doc and once as an export
    # doc, e.g. after correcting a mis-classified upload)
    existing = (
        db.query(SourceDocument)
        .filter(SourceDocument.file_hash == file_hash, SourceDocument.doc_type == "import")
        .first()
    )
    if existing:
        return UploadResponse(
            document_id=existing.id,
            filename=file.filename,
            doc_type="import",
            duplicate=True,
            message="This file has already been uploaded. You can re-extract if needed.",
        )

    _ensure_uploads_dir()
    storage_name = f"{file_hash[:12]}_{file.filename}"
    storage_path = UPLOADS_DIR / storage_name
    storage_path.write_bytes(content)

    doc = SourceDocument(
        doc_type="import",
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
        doc_type="import",
        message="File uploaded successfully. Call /api/import/extract to extract data.",
    )


@router.post("/extract/{document_id}", response_model=ExtractionResponse)
def extract_import_data(
    document_id: int,
    use_mock: bool = Query(False, description="Use mock extractor for testing"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExtractionResponse:
    """Extract structured import data from an uploaded PDF."""
    doc = db.get(SourceDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.doc_type != "import":
        raise HTTPException(status_code=400, detail="Document is not an import document")

    if use_mock:
        result = extract_mock("import")
    else:
        pdf_path = Path(doc.storage_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        result = extract_from_pdf(pdf_path, "import")

    if result.error:
        return ExtractionResponse(
            document_id=document_id,
            doc_type="import",
            error=result.error,
        )

    return ExtractionResponse(
        document_id=document_id,
        doc_type="import",
        import_entries=[
            entry.model_dump() for entry in result.import_entries
        ],
    )


@router.post("/confirm", response_model=list[ImportLineOut])
def confirm_import(
    entries: list[ImportLineCreate],
    source_document_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ImportLineOut]:
    """Confirm and store reviewed import entries in the database."""
    created = []

    for entry in entries:
        bif = entry.bif_value_kes or Decimal("0")

        import_line = ImportLine(
            source_document_id=source_document_id,
            is_legacy=False,
            consignor_exporter=entry.consignor_exporter,
            description=entry.description,
            import_file_number=entry.import_file_number,
            import_entry_date=entry.import_entry_date,
            import_entry_number=entry.import_entry_number,
            hs_code=entry.hs_code,
            country=entry.country,
            supplementary_units=entry.supplementary_units,
            unit=entry.unit,
            quantity_imported=entry.quantity_imported,
            customs_value_kes=entry.customs_value_kes,
            bif_value_kes=bif,
            # Initial balances = full import values (no exports yet)
            balance_quantity=entry.quantity_imported,
            balance_customs_value=entry.customs_value_kes,
            balance_bif_value=bif,
            balance_supplementary_units=entry.supplementary_units,
            created_by_id=user.id,
        )
        db.add(import_line)
        db.flush()

        db.add(AuditLog(
            entity_type="import_line",
            entity_id=import_line.id,
            change_type="create",
            source="human_corrected",
            user_id=user.id,
            new_value=f"Import confirmed: {entry.import_entry_number or 'N/A'}",
        ))

        created.append(import_line)

    db.commit()
    for imp in created:
        db.refresh(imp)

    return created
