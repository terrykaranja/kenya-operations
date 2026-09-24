from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base

if TYPE_CHECKING:
    from app.models.export_line import ExportLine


class ImportLine(Base):
    """One SEZ ledger import row (columns A-L), with running export balances (W/X/Y/Z).

    Balance columns are stored (not derived on read) because export confirmation
    updates them transactionally under a row lock to prevent overdraft races
    (see Phase 6.4 of the project plan).
    """

    __tablename__ = "import_lines"

    id: Mapped[int] = mapped_column(primary_key=True)

    source_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("source_documents.id"), nullable=True
    )
    is_legacy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    row_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Columns A-L
    consignor_exporter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    import_file_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    import_entry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    import_entry_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    hs_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    supplementary_units: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    quantity_imported: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    customs_value_kes: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    bif_value_kes: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    # Running balances (columns W/X/Y/Z)
    balance_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_customs_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_bif_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_supplementary_units: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)

    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    export_lines: Mapped[list["ExportLine"]] = relationship(
        back_populates="import_line", cascade="all, delete-orphan"
    )
