# esgfng-monitor

ESGF-NG Core Services Monitor probes HTTP endpoints on a schedule, records curl-style timing breakdowns, and stores the results in PostgreSQL.

Each probe runs as a short-lived process with the target URL passed on the command line. This design works well with cron: one cron line per service, so probes run in parallel at fixed wall-clock times without blocking each other.

## Prerequisites

- Python 3.10+
- PostgreSQL
- `curl` (probes use `curl -w` for timing measurements)

## Installation

```bash
git clone git@github.com:lukaszlacinski/esgfng-monitor.git
cd esgfng-monitor

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Copy the example environment file and edit it for your database:

```bash
cp config/monitor.env.example .env
# edit .env — cron reads this file; shell exports are not used
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONITOR_DATABASE_URL` | yes | — | PostgreSQL URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/monitor` |
| `MONITOR_REQUEST_TIMEOUT_SECONDS` | no | `30` | Per-request timeout in seconds |
| `MONITOR_WEB_HOST` | no | `127.0.0.1` | Web dashboard bind address |
| `MONITOR_WEB_PORT` | no | `8080` | Web dashboard port |
| `MONITOR_WEB_RESULTS_HOURS` | no | `24` | Hours of history on target detail pages |

Settings are read from a `.env` file in the project root and from environment variables (prefixed with `MONITOR_`). Environment variables override `.env` values.

## Database setup

### PostgreSQL on Ubuntu

Install PostgreSQL:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Create the `monitor` user and database (matches `config/monitor.env.example`; change the password in production):

```bash
sudo -u postgres psql <<'EOF'
CREATE USER monitor WITH PASSWORD 'monitor';
CREATE DATABASE monitor OWNER monitor;
GRANT ALL PRIVILEGES ON DATABASE monitor TO monitor;
EOF
```

On PostgreSQL 15 and later, also grant schema permissions so migrations can create tables:

```bash
sudo -u postgres psql -d monitor <<'EOF'
GRANT ALL ON SCHEMA public TO monitor;
EOF
```

Verify the connection:

```bash
psql "postgresql://monitor:monitor@localhost:5432/monitor" -c '\conninfo'
```

### Run migrations

Create the `healthcheck_results` table:

```bash
esgfng-monitor migrate
```

Re-run after pulling schema changes.

You can also use Alembic directly:

```bash
alembic upgrade head
```

## Usage

### Probe a single URL

```bash
esgfng-monitor probe --name transaction-int https://transaction-int.west.esgf.io/healthcheck
esgfng-monitor probe --name discovery-int https://discovery-int.west.esgf.io
```

- `url` — required positional argument; probed with HTTP GET
- `--name` — optional label stored in the database (defaults to the URL hostname)

The command probes the URL, writes one row to PostgreSQL, and exits. It returns exit code `0` on success and `1` if the request failed or timed out.

### Run from Python

```bash
python -m monitor probe --name transaction-int https://transaction-int.west.esgf.io/healthcheck
```

### Web dashboard

Start the dashboard (reads probe results from PostgreSQL):

```bash
esgfng-monitor serve
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). Pages:

| URL | Description |
|-----|-------------|
| `/` | Response-time charts for all targets |
| `/api/targets` | JSON summary of latest results per target |
| `/api/targets/{name}/results` | JSON time series for charts |

Bind to all interfaces with `MONITOR_WEB_HOST=0.0.0.0` in `.env` when running behind a reverse proxy.

## Cron setup

Cron does not load your shell profile, so `esgfng-monitor` will not be on `PATH`. Each job changes into the project directory first, then runs `.venv/bin/esgfng-monitor`. Database settings and other configuration are read from `.env` in the project root — do not duplicate them in the crontab.

1. Copy and edit the example crontab; set `ESGFNG_MONITOR_HOME` to your clone directory:

```bash
cp config/crontab.example /tmp/esgfng-monitor-cron
# edit ESGFNG_MONITOR_HOME=/home/ubuntu/esgfng-monitor
```

2. Ensure `.env` exists in that directory (`cp config/monitor.env.example .env`).

3. Run migrations once:

```bash
cd /path/to/esgfng-monitor && .venv/bin/esgfng-monitor migrate
```

4. Install the crontab:

```bash
crontab /tmp/esgfng-monitor-cron
```

Example crontab (also in `config/crontab.example`):

```cron
ESGFNG_MONITOR_HOME=/home/ubuntu/esgfng-monitor

* * * * * cd $ESGFNG_MONITOR_HOME && .venv/bin/esgfng-monitor probe --name transaction-int https://transaction-int.west.esgf.io/healthcheck
* * * * * cd $ESGFNG_MONITOR_HOME && .venv/bin/esgfng-monitor probe --name discovery-int https://discovery-int.west.esgf.io
```

Schedule one cron entry per target so each service is probed independently and in parallel every minute. If a probe is still running when the next minute starts, cron launches another instance — overlapping runs are expected and safe.

## Stored data

Each probe inserts a row into `healthcheck_results` with:

| Column | Description |
|--------|-------------|
| `target_name` | Label from `--name` |
| `url` | Probed URL |
| `checked_at` | UTC timestamp when the probe started |
| `http_status_code` | HTTP response status (null on failure) |
| `time_namelookup` | DNS lookup time (seconds) |
| `time_connect` | TCP connect time (seconds) |
| `time_appconnect` | TLS handshake time (seconds) |
| `time_pretransfer` | Time until transfer start (seconds) |
| `time_starttransfer` | Time to first byte (seconds) |
| `time_total` | Total request time (seconds) |
| `error` | Error message if the probe failed |

Timing fields match the values produced by `curl -w`.

Example query:

```sql
SELECT target_name, checked_at, http_status_code, time_total, error
FROM healthcheck_results
ORDER BY checked_at DESC
LIMIT 20;
```
