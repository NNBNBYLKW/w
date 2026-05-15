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

def create_app() -> FastAPI:
    initialize_database()
    with SessionLocal() as startup_session:
        tools_service.mark_stale_runs_failed(startup_session)
        organize_service.mark_stale_executing_plans_failed(startup_session)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
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
