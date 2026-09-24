"""
KSITI FastAPI Application
=========================
Entry point that wires together all routers and middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import intake, officer

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.session import engine, Base
    from app.db import models
    from sqlalchemy import text
    try:
        # Create PostGIS extension if using postgres
        if engine.url.drivername.startswith("postgres"):
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()
    except Exception as e:
        print(f"Skipping PostGIS extension creation: {e}")
        
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="KSITI: Tripartite Cadastral Reconciliation Engine",
    description=(
        "Intelligent Land Record Digitization & Validation Engine — "
        "deterministically gated, multi-agent architecture for "
        "bridging legacy paper deeds with PostGIS spatial topologies."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS (allow local development and future frontend) ───────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register route modules ──────────────────────────────────────────────
app.include_router(intake.router)
app.include_router(officer.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "KSITI API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Advanced health probe for deep diagnostics."""
    import psutil
    from app.db.session import engine
    from sqlalchemy import text
    
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"failed: {str(e)}"
        
    return {
        "status": "ok",
        "database": db_status,
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
        },
        "engine": "Tripartite Validation Engine v2.0 Active",
        "models": {
            "perception": "loaded_on_demand",
            "fraud": "isolation_forest"
        }
    }
