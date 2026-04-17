from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.collections import router as collections_router
from app.api.routes.files import router as files_router
from app.api.routes.library import router as library_router
from app.api.routes.recent import router as recent_router
from app.api.routes.search import router as search_router
from app.api.routes.sources import router as sources_router
from app.api.routes.system import router as system_router
from app.api.routes.tags import router as tags_router
from app.core.config.settings import settings
from app.core.errors.handlers import register_exception_handlers
from app.db.session.engine import initialize_database

def create_app() -> FastAPI:
    initialize_database()
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
    app.include_router(library_router)
    app.include_router(recent_router)
    app.include_router(search_router)
    app.include_router(sources_router)
    app.include_router(tags_router)

    return app


app = create_app()
