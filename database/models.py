from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FinancialMetricsRecord(Base):
    __tablename__ = "financial_metrics"
    __table_args__ = (UniqueConstraint("company", "year", name="uq_company_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String(100), index=True)
    year: Mapped[int | None] = mapped_column(Integer, index=True)

    revenue: Mapped[str | None] = mapped_column(Text)
    net_income: Mapped[str | None] = mapped_column(Text)
    operating_income: Mapped[str | None] = mapped_column(Text)
    cash_flow: Mapped[str | None] = mapped_column(Text)
    total_assets: Mapped[str | None] = mapped_column(Text)
    total_liabilities: Mapped[str | None] = mapped_column(Text)
    risk_factors: Mapped[list | str | None] = mapped_column(JSONB)
    growth_drivers: Mapped[list | str | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )