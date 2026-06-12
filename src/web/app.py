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
        settings = get_settings()
        with get_session() as session:
            targets = []
            for chart_id, name in enumerate(queries.list_target_names(session)):
                results = queries.recent_results(
                    session,
                    name,
                    hours=settings.web_results_hours,
                )
                latest = results[0] if results else None
                targets.append(
                    {
                        "chart_id": chart_id,
                        "name": name,
                        "url": queries.get_target_url(session, name),
                        "chart_points": [
                            queries.result_to_chart_point(result)
                            for result in reversed(results)
                        ],
                        "status": queries.result_status(latest) if latest else "error",
                        "http_status_code": latest.http_status_code if latest else None,
                        "error": latest.error if latest else None,
                    }
                )

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "targets": targets,
                "hours": settings.web_results_hours,
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
