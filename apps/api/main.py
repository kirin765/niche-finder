from fastapi import FastAPI

from micro_niche_finder.api.routes import router
from micro_niche_finder.config.settings import get_settings


settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.app_debug)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
