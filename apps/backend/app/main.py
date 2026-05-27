import logging
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.collections import router as collections_router
from app.api.routes.files import router as files_router
from app.api.routes.importing import router as importing_router
from app.api.routes.library import router as library_router
from app.api.routes.library_objects import router as library_objects_router
from app.api.routes.library_organize import router as library_organize_router
from app.api.routes.library_roots import router as library_roots_router
from app.api.routes.recent import router as recent_router
from app.api.routes.search import router as search_router
from app.api.routes.sources import router as sources_router
from app.api.routes.system import router as system_router
from app.api.routes.tags import router as tags_router
from app.services.library.organize import organize_service
from app.api.routes.tools import router as tools_router, tools_service
from app.core.config.settings import settings
from app.core.errors.handlers import register_exception_handlers
from app.db.session.engine import initialize_database
from app.db.session.session import SessionLocal


def _setup_logging() -> None:
    log_path = settings.data_dir / "backend.log"
    handler = RotatingFileHandler(
        str(log_path), maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def _backup_database() -> None:
    db_path = Path(settings.database_path)
    if not db_path.exists():
        return
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups = sorted(backup_dir.glob("workbench_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) >= 3:
        backups.pop(0).unlink(missing_ok=True)
    from datetime import UTC, datetime
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(str(db_path), str(backup_dir / f"workbench_{ts}.db"))

    # VACUUM every 5th startup
    import sqlite3 as _sqlite3
    vacuum_file = backup_dir / ".vacuum_count"
    try:
        count = int(vacuum_file.read_text().strip())
    except Exception:
        count = 0
    count += 1
    vacuum_file.write_text(str(count))
    if count >= 5:
        with _sqlite3.connect(settings.database_path) as vconn:
            vconn.execute("VACUUM")
        vacuum_file.write_text("0")
        logging.getLogger(__name__).info("Database VACUUM completed")


def create_app() -> FastAPI:
    _setup_logging()
    _backup_database()
    initialize_database()
    with SessionLocal() as startup_session:
        tools_service.mark_stale_runs_failed(startup_session)
        organize_service.mark_stale_executing_plans_failed(startup_session)
    app = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(system_router)
    app.include_router(collections_router)
    app.include_router(files_router)
    app.include_router(importing_router)
    app.include_router(library_router)
    app.include_router(library_objects_router)
    app.include_router(library_organize_router)
    app.include_router(library_roots_router)
    app.include_router(recent_router)
    app.include_router(search_router)
    app.include_router(sources_router)
    app.include_router(tags_router)
    app.include_router(tools_router)

    return app


app = create_app()
