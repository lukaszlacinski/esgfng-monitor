import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpcore


@dataclass
class CurlTimings:
    """Timing fields matching curl -w output (values in seconds)."""

    started_at: float = field(default_factory=time.perf_counter)
    time_namelookup: float | None = None
    time_connect: float | None = None
    time_appconnect: float | None = None
    time_pretransfer: float | None = None
    time_starttransfer: float | None = None
    time_total: float | None = None

    def elapsed(self) -> float:
        return time.perf_counter() - self.started_at


@dataclass
class ProbeResult:
    target_name: str
    url: str
    checked_at: datetime
    http_status_code: int | None
    timings: CurlTimings
    error: str | None = None


def _make_trace_handler(timings: CurlTimings):
    def trace(event_name: str, info: dict[str, Any]) -> None:
        elapsed = time.perf_counter() - timings.started_at
        if event_name == "connection.connect_tcp.started":
            timings.time_namelookup = elapsed
        elif event_name == "connection.connect_tcp.complete":
            timings.time_connect = elapsed
            if timings.time_appconnect is None:
                timings.time_appconnect = elapsed
                timings.time_pretransfer = elapsed
        elif event_name == "connection.start_tls.complete":
            timings.time_appconnect = elapsed
            timings.time_pretransfer = elapsed
        elif event_name in (
            "http11.receive_response_headers.complete",
            "http2.receive_response_headers.complete",
        ):
            timings.time_starttransfer = elapsed

    return trace


def probe_target(
    target_name: str,
    url: str,
    timeout_seconds: float,
) -> ProbeResult:
    timings = CurlTimings()
    checked_at = datetime.now(timezone.utc)
    http_status_code: int | None = None
    error: str | None = None

    try:
        timeout = {
            "connect": timeout_seconds,
            "read": timeout_seconds,
            "write": timeout_seconds,
            "pool": timeout_seconds,
        }
        with httpcore.ConnectionPool() as pool:
            response = pool.request(
                "GET",
                httpcore.URL(url),
                extensions={
                    "trace": _make_trace_handler(timings),
                    "timeout": timeout,
                },
            )
            http_status_code = response.status
            response.read()
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    finally:
        timings.time_total = timings.elapsed()

    return ProbeResult(
        target_name=target_name,
        url=url,
        checked_at=checked_at,
        http_status_code=http_status_code,
        timings=timings,
        error=error,
    )
