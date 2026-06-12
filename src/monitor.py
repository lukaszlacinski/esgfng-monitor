import argparse
import logging
import sys
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config

from config import get_settings, project_root
from db import get_session
from models import HealthcheckResult
from probe import ProbeResult, probe_target

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    root = project_root()
    alembic_ini = root / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Alembic config not found: {alembic_ini}")

    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(alembic_cfg, "head")


def store_result(result: ProbeResult) -> None:
    timings = result.timings
    with get_session() as session:
        session.add(
            HealthcheckResult(
                target_name=result.target_name,
                url=result.url,
                checked_at=result.checked_at,
                http_status_code=result.http_status_code,
                time_namelookup=timings.time_namelookup,
                time_connect=timings.time_connect,
                time_appconnect=timings.time_appconnect,
                time_starttransfer=timings.time_starttransfer,
                time_total=timings.time_total,
                error=result.error,
            )
        )

    if result.error:
        logger.warning("%s probe failed: %s", result.target_name, result.error)
    else:
        logger.info(
            "%s %s total=%.3fs status=%s",
            result.target_name,
            result.checked_at.isoformat(),
            timings.time_total or 0.0,
            result.http_status_code,
        )


def probe_url(url: str, name: str | None = None) -> ProbeResult:
    target_name = name or urlparse(url).hostname or url
    result = probe_target(target_name, url, get_settings().request_timeout_seconds)
    store_result(result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe ESGF-NG service URLs and store curl-like timings in PostgreSQL.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Create or update database tables")

    probe_parser = subparsers.add_parser(
        "probe",
        help="Probe one URL, store the result, and exit",
    )
    probe_parser.add_argument("url", help="URL to probe (GET request)")
    probe_parser.add_argument(
        "--name",
        help="Target name stored in the database (default: URL hostname)",
    )

    subparsers.add_parser("serve", help="Run the web dashboard")

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    args = build_parser().parse_args(argv)

    if args.command == "migrate":
        logger.info("Running database migrations")
        run_migrations()
        return 0

    if args.command == "probe":
        result = probe_url(args.url, args.name)
        return 1 if result.error else 0

    if args.command == "serve":
        from web.app import run_server

        run_server()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
