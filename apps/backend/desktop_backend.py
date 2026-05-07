import logging
import os
from multiprocessing import freeze_support
from pathlib import Path
import sys

import uvicorn


def configure_logging() -> None:
    data_dir = os.environ.get("WORKBENCH_DATA_DIR")
    if not data_dir:
        logging.basicConfig(level=logging.INFO)
        return

    log_dir = Path(data_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "backend-startup.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    configure_logging()
    from app.core.config.settings import settings
    from app.main import app

    logging.info("Starting Workbench backend on %s:%s", settings.api_host, settings.api_port)
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] == "--pdf-render-worker":
        from app.workers.thumbnails.pdf_render_cli import main as pdf_render_main

        raise SystemExit(pdf_render_main(sys.argv[2:]))
    main()
