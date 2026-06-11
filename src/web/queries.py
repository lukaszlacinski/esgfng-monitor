from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import HealthcheckResult


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


def result_to_chart_point(result: HealthcheckResult) -> dict:
    return {
        "t": result.checked_at.isoformat(),
        "total": as_float(result.time_total),
        "status": result_status(result),
        "code": result.http_status_code,
    }
