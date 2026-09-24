from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base

if TYPE_CHECKING:
    from app.models.import_line import ImportLine


class ExportLine(Base):
    """One SEZ ledger export row (columns M-V), prorated against a parent ImportLine."""

    __tablename__ = "export_lines"

    id: Mapped[int] = mapped_column(primary_key=True)

    import_line_id: Mapped[int] = mapped_column(
        ForeignKey("import_lines.id"), nullable=False, index=True
    )
    source_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    is_legacy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    row_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Columns M-V
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    export_file_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    export_entry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    export_entry_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    ppb_permit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    supplementary_units_exported: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    quantity_exported: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    customs_value_exported: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    bif_value_exported: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    import_line: Mapped["ImportLine"] = relationship(back_populates="export_lines")
