from __future__ import annotations

import uvicorn

from .app import create_app
from .config import get_settings
from .log import setup_logging


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    app = create_app(settings)
    print(f"museai listening on http://{settings.host}:{settings.port}  (driver={settings.driver})")
    if settings.key_file.is_file():
        print(f"auto-generated API key is stored in {settings.key_file}")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
