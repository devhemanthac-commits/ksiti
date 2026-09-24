"""
KSITI Core Configuration
========================
Centralised settings for all infrastructure connections.
Reads from environment variables with sane local-dev defaults.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # ksiti_master/
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# PostgreSQL + PostGIS 
# ---------------------------------------------------------------------------
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ksiti_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ksiti_secure_2026")
POSTGRES_DB = os.getenv("POSTGRES_DB", "ksiti_cadastre")

if POSTGRES_HOST:
    DATABASE_URL = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
else:
    # Local fallback
    DATABASE_URL = "sqlite:///./ksiti_local.db"

# ---------------------------------------------------------------------------
# Redis (Celery broker + result backend + caching)
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "")

# ---------------------------------------------------------------------------
# ClamAV
# ---------------------------------------------------------------------------
CLAMAV_HOST = os.getenv("CLAMAV_HOST", "localhost")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))

# ---------------------------------------------------------------------------
# CIS Scoring Weights (from SPEC.md §5)
# ---------------------------------------------------------------------------
CIS_W1 = float(os.getenv("CIS_W1", "0.40"))   # Harmonic mean (OCR confidence)
CIS_W2 = float(os.getenv("CIS_W2", "0.40"))   # Gaussian spatial decay
CIS_W3 = float(os.getenv("CIS_W3", "0.20"))   # Layout segmentation confidence
CIS_TAU = float(os.getenv("CIS_TAU", "0.05")) # Statutory survey tolerance (acres)
CIS_GREEN_THRESHOLD = float(os.getenv("CIS_GREEN_THRESHOLD", "0.85"))
