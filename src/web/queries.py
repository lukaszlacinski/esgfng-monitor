from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import HealthcheckResult

# Cumulative curl -w fields stored in the database (in order).
CURL_TIMING_FIELDS = (
    "time_namelookup",
    "time_connect",
    "time_appconnect",
    "time_pretransfer",
    "time_starttransfer",
    "time_total",
)


def as_float(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def result_status(result: HealthcheckResult) -> str:
    if result.error:
        return "error"
    if result.http_status_code is None:
        return "error"
    if 200 <= result.http_status_code < 300:
        return "ok"
    if 400 <= result.http_status_code < 500:
        return "warn"
    return "error"


def list_target_names(session: Session) -> list[str]:
    rows = session.execute(
        select(HealthcheckResult.target_name)
        .distinct()
        .order_by(HealthcheckResult.target_name)
    ).scalars()
    return list(rows)


def latest_results(session: Session) -> list[HealthcheckResult]:
    return list(
        session.execute(
            select(HealthcheckResult)
            .distinct(HealthcheckResult.target_name)
            .order_by(
                HealthcheckResult.target_name,
                HealthcheckResult.checked_at.desc(),
            )
        ).scalars()
    )


def get_target_url(session: Session, target_name: str) -> str | None:
    row = session.execute(
        select(HealthcheckResult.url)
        .where(HealthcheckResult.target_name == target_name)
        .order_by(HealthcheckResult.checked_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row


def recent_results(
    session: Session,
    target_name: str,
    *,
    hours: int,
    limit: int = 2000,
) -> list[HealthcheckResult]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return list(
        session.execute(
            select(HealthcheckResult)
            .where(HealthcheckResult.target_name == target_name)
            .where(HealthcheckResult.checked_at >= since)
            .order_by(HealthcheckResult.checked_at.desc())
            .limit(limit)
        ).scalars()
    )


def cumulative_timings(result: HealthcheckResult) -> dict[str, float | None]:
    """Cumulative curl -w values as stored in the database."""
    return {
        field: as_float(getattr(result, field))
        for field in CURL_TIMING_FIELDS
    }


def timing_stack(result: HealthcheckResult) -> dict[str, float]:
    """Increment between each cumulative curl timing (for stacked charts)."""
    previous = 0.0
    stack: dict[str, float] = {}
    for field in CURL_TIMING_FIELDS:
        cumulative = as_float(getattr(result, field)) or 0.0
        stack[field] = max(0.0, cumulative - previous)
        previous = cumulative
    return stack


def result_to_chart_point(result: HealthcheckResult) -> dict:
    cumulative = cumulative_timings(result)
    return {
        "t": result.checked_at.isoformat(),
        "status": result_status(result),
        "code": result.http_status_code,
        "cumulative": cumulative,
        **timing_stack(result),
    }
