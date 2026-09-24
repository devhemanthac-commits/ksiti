"""
KSITI Database Models
=====================
Implements the "Three Layers of Truth" data model (SPEC.md §6)
with PostGIS geometry support via GeoAlchemy2.

Tables
------
CadastralRecord  — one row per uploaded deed, tracks the full lifecycle
                   from intake → AI extraction → CIS scoring → DSC sign-off.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Text, DateTime, Enum as SAEnum, Integer
)
# from geoalchemy2 import Geometry
from app.db.session import Base


class CadastralRecord(Base):
    """
    Master table for every land-record deed processed by KSITI.

    Lifecycle statuses:
        UPLOADED → SCANNING → PROCESSING → SCORED → GREEN_CHANNEL
                                                   → RED_CHANNEL (HITL)
                                                   → DSC_APPROVED
                                                   → FAILED
    """
    __tablename__ = "cadastral_records"

    # ── Primary identifiers ──────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)
    tracking_id = Column(
        String(36), unique=True, nullable=False, index=True,
        default=lambda: str(uuid.uuid4()),
    )
    ulpin = Column(String(64), nullable=True, index=True, comment="Bhu-Aadhaar / ULPIN")

    # ── Chain-of-custody hashes (SPEC.md §5, PRD §5.1) ──────────────────
    raw_document_sha256 = Column(String(64), nullable=False)
    extracted_state_sha256 = Column(String(64), nullable=True)

    # ── Original file metadata ───────────────────────────────────────────
    original_filename = Column(String(255), nullable=True)
    stored_filepath = Column(Text, nullable=False)

    # ── Layer 1: Source Record (verbatim paper claim) ────────────────────
    source_area_claim = Column(Float, nullable=True, comment="Area from paper deed (acres)")

    # ── Layer 2: Digitized Record (AI extraction) ────────────────────────
    extracted_area = Column(Float, nullable=True, comment="OCR-extracted area (acres)")
    extracted_json = Column(Text, nullable=True, comment="Full structured extraction JSON")
    ocr_confidence_mean = Column(Float, nullable=True)
    layout_confidence_mean = Column(Float, nullable=True)

    # ── Layer 3: Derived Discrepancy (PostGIS reality) ───────────────────
    gis_area = Column(Float, nullable=True, comment="PostGIS-calculated area (acres)")
    variance_delta = Column(Float, nullable=True, comment="|extracted - GIS|")
    variance_percentage = Column(Float, nullable=True)
    parcel_geometry = Column(
        Text, nullable=True,
        comment="Authoritative cadastral polygon (WKT for SQLite)"
    )

    # ── CIS Scoring (SPEC.md §5) ────────────────────────────────────────
    cis_score = Column(Float, nullable=True)
    cis_omega = Column(Float, nullable=True, comment="Boolean kill-switch value (0 or 1)")
    routing = Column(String(20), nullable=True, comment="GREEN_CHANNEL or RED_CHANNEL")

    # ── Fraud layer ──────────────────────────────────────────────────────
    fraud_detected = Column(String(5), default="false")
    fraud_flags = Column(Text, nullable=True, comment="JSON array of fraud flag descriptions")

    # ── Officer sign-off (PRD §5.3) ──────────────────────────────────────
    officer_id = Column(String(64), nullable=True)
    dsc_signature = Column(Text, nullable=True)

    # ── Status & timestamps ──────────────────────────────────────────────
    status = Column(String(30), default="UPLOADED", nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
