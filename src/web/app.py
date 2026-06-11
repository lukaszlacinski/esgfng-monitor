from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import get_settings
from db import get_session
from web import queries

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    app = FastAPI(title="ESGF-NG Monitor", docs_url="/api/docs", redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        with get_session() as session:
            latest = queries.latest_results(session)
            targets = [
                {
                    "name": result.target_name,
                    "url": result.url,
                    "checked_at": result.checked_at,
                    "http_status_code": result.http_status_code,
                    "time_total": queries.as_float(result.time_total),
                    "error": result.error,
                    "status": queries.result_status(result),
                }
                for result in latest
            ]

        return templates.TemplateResponse(
            request,
            "index.html",
            {"targets": targets},
        )

    @app.get("/targets/{target_name}", response_class=HTMLResponse)
    def target_detail(request: Request, target_name: str) -> HTMLResponse:
        settings = get_settings()
        with get_session() as session:
            if target_name not in queries.list_target_names(session):
                raise HTTPException(status_code=404, detail="Target not found")

            url = queries.get_target_url(session, target_name)
            results = queries.recent_results(
                session,
                target_name,
                hours=settings.web_results_hours,
            )
            chart_points = [
                queries.result_to_chart_point(result) for result in reversed(results)
            ]
            table_rows = [
                {
                    "checked_at": result.checked_at,
                    "http_status_code": result.http_status_code,
                    "segments": queries.timing_segments(result),
                    "time_total": queries.as_float(result.time_total),
                    "error": result.error,
                    "status": queries.result_status(result),
                }
                for result in results[:200]
            ]

        return templates.TemplateResponse(
            request,
            "target.html",
            {
                "target_name": target_name,
                "url": url,
                "hours": settings.web_results_hours,
                "chart_points": chart_points,
                "results": table_rows,
            },
        )

    @app.get("/api/targets")
    def api_targets() -> JSONResponse:
        with get_session() as session:
            latest = queries.latest_results(session)
            payload = [
                {
                    "name": result.target_name,
                    "url": result.url,
                    "checked_at": result.checked_at.isoformat(),
                    "http_status_code": result.http_status_code,
                    "time_total": queries.as_float(result.time_total),
                    "error": result.error,
                    "status": queries.result_status(result),
                }
                for result in latest
            ]
        return JSONResponse(payload)

    @app.get("/api/targets/{target_name}/results")
    def api_target_results(target_name: str) -> JSONResponse:
        settings = get_settings()
        with get_session() as session:
            if target_name not in queries.list_target_names(session):
                raise HTTPException(status_code=404, detail="Target not found")
            results = queries.recent_results(
                session,
                target_name,
                hours=settings.web_results_hours,
            )
            payload = [queries.result_to_chart_point(result) for result in reversed(results)]
        return JSONResponse(payload)

    return app


def run_server() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "web.app:create_app",
        factory=True,
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )
