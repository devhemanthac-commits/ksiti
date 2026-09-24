"""
KSITI CRUD Operations
=====================
All database read/write helpers for CadastralRecord.
Each function takes an explicit SQLAlchemy Session — no global state.
"""

from typing import Optional, List
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import CadastralRecord


# ── CREATE ───────────────────────────────────────────────────────────────

def create_record(
    db: Session,
    tracking_id: str,
    raw_document_sha256: str,
    stored_filepath: str,
    original_filename: str,
    source_area_claim: Optional[float] = None,
) -> CadastralRecord:
    """Insert a new intake record at the UPLOADED stage."""
    record = CadastralRecord(
        tracking_id=tracking_id,
        raw_document_sha256=raw_document_sha256,
        stored_filepath=stored_filepath,
        original_filename=original_filename,
        source_area_claim=source_area_claim,
        status="UPLOADED",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── READ ─────────────────────────────────────────────────────────────────

def get_record(db: Session, tracking_id: str) -> Optional[CadastralRecord]:
    """Fetch a single record by tracking_id."""
    return (
        db.query(CadastralRecord)
        .filter(CadastralRecord.tracking_id == tracking_id)
        .first()
    )


def get_all_records(db: Session, limit: int = 100) -> List[CadastralRecord]:
    """Fetch all records, most recent first."""
    return (
        db.query(CadastralRecord)
        .order_by(CadastralRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def get_records_by_status(db: Session, status: str) -> List[CadastralRecord]:
    """Fetch records filtered by a specific status (e.g. RED_CHANNEL)."""
    return (
        db.query(CadastralRecord)
        .filter(CadastralRecord.status == status)
        .order_by(CadastralRecord.created_at.desc())
        .all()
    )


# ── UPDATE — Pipeline stages ────────────────────────────────────────────

def update_status(db: Session, tracking_id: str, status: str) -> None:
    """Update just the status field."""
    db.query(CadastralRecord).filter(
        CadastralRecord.tracking_id == tracking_id
    ).update({"status": status, "updated_at": datetime.now(timezone.utc)})
    db.commit()


def update_extraction(
    db: Session,
    tracking_id: str,
    extracted_area: float,
    extracted_json: str,
    ocr_confidence_mean: float,
    layout_confidence_mean: float,
    gis_area: float,
    variance_delta: float,
    variance_percentage: float,
    cis_score: float,
    cis_omega: float,
    routing: str,
    fraud_detected: bool,
    fraud_flags: Optional[list] = None,
) -> None:
    """Write all extraction + scoring results after the pipeline completes."""
    updates = {
        "extracted_area": extracted_area,
        "extracted_json": extracted_json,
        "ocr_confidence_mean": ocr_confidence_mean,
        "layout_confidence_mean": layout_confidence_mean,
        "gis_area": gis_area,
        "variance_delta": variance_delta,
        "variance_percentage": variance_percentage,
        "cis_score": cis_score,
        "cis_omega": cis_omega,
        "routing": routing,
        "fraud_detected": str(fraud_detected).lower(),
        "fraud_flags": json.dumps(fraud_flags) if fraud_flags else None,
        "status": routing,  # GREEN_CHANNEL or RED_CHANNEL
        "updated_at": datetime.now(timezone.utc),
    }
    db.query(CadastralRecord).filter(
        CadastralRecord.tracking_id == tracking_id
    ).update(updates)
    db.commit()


def update_dsc_signoff(
    db: Session,
    tracking_id: str,
    officer_id: str,
    dsc_signature: str,
    extracted_state_sha256: str,
) -> None:
    """Record the officer's DSC sign-off."""
    db.query(CadastralRecord).filter(
        CadastralRecord.tracking_id == tracking_id
    ).update({
        "officer_id": officer_id,
        "dsc_signature": dsc_signature,
        "extracted_state_sha256": extracted_state_sha256,
        "status": "DSC_APPROVED",
        "updated_at": datetime.now(timezone.utc),
    })
    db.commit()
