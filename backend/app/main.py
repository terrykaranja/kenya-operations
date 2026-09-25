"""AMEX Healthcare Hackathon starter API.

Run locally with:
    uvicorn app.main:app --reload

All static/reference data your track needs (CSVs, JSON, sample docs, etc.)
should live in the top-level `/resources` folder and be loaded through
`app.resources.resource_path()` so the whole team uses one consistent location.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import admin, auth, exports, imports, ledger

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="SEZ Ledger Automation API",
    description="Kenya Operations SEZ stock ledger automation backend.",
    version="0.1.0",
)

# Cookie-based auth needs an explicit origin list (not "*") so the browser
# will actually send/accept the session cookie cross-origin in dev.
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(imports.router)
app.include_router(exports.router)
app.include_router(ledger.router)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Simple liveness check used by the frontend and CI."""
    return {"status": "ok"}


# Serve the frontend SPA at root
@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve the standalone HTML frontend."""
    return FileResponse(STATIC_DIR / "index.html")


# Mount static assets (images, etc.) at /static
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
