from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from database.connection import get_engine, wait_for_db
from database.models import Base, FinancialMetricsRecord

METRIC_FIELDS = [
    "revenue", "net_income", "operating_income", "cash_flow",
    "total_assets", "total_liabilities", "risk_factors", "growth_drivers",
]
TEXT_FIELDS = METRIC_FIELDS[:6]

_initialized = False


def init_db() -> None:
    """Create tables if they don't exist (runs once per process)."""
    global _initialized
    if not _initialized:
        wait_for_db()
        Base.metadata.create_all(get_engine())
        _initialized = True


def save_metrics(company: str, year: int | None, metrics: dict) -> None:
    """Insert KPIs, or update them if this company+year already exists."""
    init_db()

    row = {"company": company, "year": year}
    for field in METRIC_FIELDS:
        value = metrics.get(field)
        row[field] = str(value) if field in TEXT_FIELDS and value is not None else value

    stmt = insert(FinancialMetricsRecord).values(**row)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_company_year",
        set_={**{f: stmt.excluded[f] for f in METRIC_FIELDS}, "updated_at": func.now()},
    )

    with get_engine().begin() as conn:
        conn.execute(stmt)


def get_metrics(company: str | None = None, year: int | None = None) -> list[dict]:
    """Read saved KPIs in a template/JSON-friendly shape."""
    init_db()
    query = select(FinancialMetricsRecord).order_by(FinancialMetricsRecord.company)
    if company:
        query = query.where(FinancialMetricsRecord.company == company)
    if year:
        query = query.where(FinancialMetricsRecord.year == year)

    with get_engine().connect() as conn:
        rows = conn.execute(query).mappings().all()

    results = []
    for r in rows:
        row = dict(r)
        for field in ("risk_factors", "growth_drivers"):
            if isinstance(row[field], list):
                row[field] = "\n".join(row[field])   # template expects newline text
        for field in ("created_at", "updated_at"):
            if row[field] is not None:
                row[field] = row[field].isoformat()  # JSON-serializable
        results.append(row)
    return results


if __name__ == "__main__":
    save_metrics("TestCo", 2099, {"revenue": "$1 million", "risk_factors": ["test risk"]})
    print(get_metrics("TestCo", 2099))