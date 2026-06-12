import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

CURL_WRITEOUT = "\t".join(
    [
        "%{time_namelookup}",
        "%{time_connect}",
        "%{time_appconnect}",
        "%{time_starttransfer}",
        "%{time_total}",
        "%{http_code}",
    ]
)


@dataclass
class CurlTimings:
    """Timing fields matching curl -w output (values in seconds)."""

    time_namelookup: float | None = None
    time_connect: float | None = None
    time_appconnect: float | None = None
    time_starttransfer: float | None = None
    time_total: float | None = None


@dataclass
class ProbeResult:
    target_name: str
    url: str
    checked_at: datetime
    http_status_code: int | None
    timings: CurlTimings
    error: str | None = None


def _parse_curl_output(stdout: str) -> tuple[CurlTimings, int | None]:
    line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    parts = line.split("\t")
    if len(parts) != 6:
        raise ValueError(f"unexpected curl output: {stdout!r}")

    timings = CurlTimings(
        time_namelookup=float(parts[0]),
        time_connect=float(parts[1]),
        time_appconnect=float(parts[2]),
        time_starttransfer=float(parts[3]),
        time_total=float(parts[4]),
    )
    if parts[5] == "000":
        return timings, None
    return timings, int(parts[5])


def probe_target(
    target_name: str,
    url: str,
    timeout_seconds: float,
) -> ProbeResult:
    checked_at = datetime.now(timezone.utc)
    timings = CurlTimings()
    http_status_code: int | None = None
    error: str | None = None

    curl = shutil.which("curl")
    if curl is None:
        return ProbeResult(
            target_name=target_name,
            url=url,
            checked_at=checked_at,
            http_status_code=None,
            timings=timings,
            error="curl not found in PATH",
        )

    try:
        completed = subprocess.run(
            [
                curl,
                "-o",
                "/dev/null",
                "-s",
                "-m",
                str(int(timeout_seconds)),
                "-w",
                CURL_WRITEOUT,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 5,
            check=False,
        )
        timings, http_status_code = _parse_curl_output(completed.stdout)
        if completed.returncode != 0:
            error = completed.stderr.strip() or f"curl exited with code {completed.returncode}"
        elif http_status_code is None:
            error = "connection failed"
    except subprocess.TimeoutExpired:
        error = f"curl timed out after {timeout_seconds}s"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

    return ProbeResult(
        target_name=target_name,
        url=url,
        checked_at=checked_at,
        http_status_code=http_status_code,
        timings=timings,
        error=error,
    )
