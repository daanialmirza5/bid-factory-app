import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.api.knowledge_base import router as knowledge_base_router
from backend.utils.config import get_settings
from backend.utils.errors import register_exception_handlers


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()

app = FastAPI(
    title="BidFactory API",
    version="0.1.0",
    description="Backend foundation for BidFactory bid analysis workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router, prefix="/api")
app.include_router(knowledge_base_router, prefix="/api")

from backend.api.chat import router as chat_router
app.include_router(chat_router, prefix="/api")


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if (frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path.startswith("api"):
        return {"detail": "Not Found"}
    file_path = frontend_dist / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    index_html = frontend_dist / "index.html"
    if index_html.is_file():
        return FileResponse(index_html)
    return {"status": "ok", "service": settings.app_name}