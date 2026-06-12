from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class HealthcheckResult(Base):
    """One GET /healthcheck probe with curl-style timing fields (seconds)."""

    __tablename__ = "healthcheck_results"
    __table_args__ = (
        Index("ix_healthcheck_results_target_checked_at", "target_name", "checked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    target_name: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_namelookup: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    time_connect: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    time_appconnect: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    time_starttransfer: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    time_total: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
