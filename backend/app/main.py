import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import analysis, audit, auth, comparisons, documents, export, stats

log = logging.getLogger("api")

app = FastAPI(
    title="Legal AI Contract Intelligence",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exc_handler(request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(comparisons.router)
app.include_router(stats.router)
app.include_router(audit.router)
app.include_router(export.router)

# SPA static (built by frontend CI into backend/app/static/dist)
_STATIC = os.path.join(os.path.dirname(__file__), "static", "dist")
_INDEX = os.path.join(_STATIC, "index.html")
if os.path.isdir(_STATIC):
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = os.path.join(_STATIC, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        if os.path.isfile(_INDEX):
            return FileResponse(_INDEX)
        raise HTTPException(status_code=404, detail="Not found")
else:  # dev fallback — no SPA built yet
    @app.get("/", include_in_schema=False)
    async def root():
        return {"app": "Legal AI Contract Intelligence", "docs": "/api/docs"}
