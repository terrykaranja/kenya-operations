"""AMEX Healthcare Hackathon starter API.

Run locally with:
    uvicorn app.main:app --reload

All static/reference data your track needs (CSVs, JSON, sample docs, etc.)
should live in the top-level `/resources` folder and be loaded through
`app.resources.resource_path()` so the whole team uses one consistent location.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, auth, exports, imports, ledger

app = FastAPI(
    title="SEZ Ledger Automation API",
    description="Kenya Operations SEZ stock ledger automation backend.",
    version="0.1.0",
)

# Cookie-based auth needs an explicit origin list (not "*") so the browser
# will actually send/accept the session cookie cross-origin in dev.
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

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
