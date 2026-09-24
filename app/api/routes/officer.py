"""
KSITI — Officer Routes
======================
Endpoints for the Revenue Officer workflow:
  - Red Channel dashboard (HITL triage)
  - DSC sign-off & DigiLocker push simulation (PRD §5.3, §5.4)
"""

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db import crud

router = APIRouter(prefix="/api/v1", tags=["Officer Operations"])


# ── Request / Response schemas ───────────────────────────────────────────

class SignOffRequest(BaseModel):
    tracking_id: str
    officer_id: str
    dsc_signature: str


class SignOffResponse(BaseModel):
    tracking_id: str
    extracted_state_sha256: str
    status: str
    message: str
    digilocker_payload: dict | None = None


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/red-channel")
def red_channel_dashboard(db: Session = Depends(get_db)):
    """Return all documents routed to the Red Channel (CIS < 0.85 or Ω=0)."""
    records = crud.get_records_by_status(db, "RED_CHANNEL")
    return [
        {
            "tracking_id": r.tracking_id,
            "original_filename": r.original_filename,
            "cis_score": r.cis_score,
            "cis_omega": r.cis_omega,
            "variance_delta": r.variance_delta,
            "fraud_detected": r.fraud_detected,
            "fraud_flags": r.fraud_flags,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/green-channel")
def green_channel_dashboard(db: Session = Depends(get_db)):
    """Return all documents in the Green Channel (CIS ≥ 0.85), ready for sign-off."""
    records = crud.get_records_by_status(db, "GREEN_CHANNEL")
    return [
        {
            "tracking_id": r.tracking_id,
            "original_filename": r.original_filename,
            "cis_score": r.cis_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.post("/sign-off", response_model=SignOffResponse)
def sign_off_document(req: SignOffRequest, db: Session = Depends(get_db)):
    """
    DSC Sign-Off Endpoint (PRD §5.3)
    ---------------------------------
    Simulates the Revenue Officer's hardware DSC sign-off:
      1. Verify the document exists and is in a signable state.
      2. Compute extracted_state_sha256 from the verified data.
      3. Update DB status to DSC_APPROVED.
      4. Build and return the e-RoR payload for DigiLocker push.
    """
    record = crud.get_record(db, req.tracking_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    if record.status not in ("GREEN_CHANNEL", "RED_CHANNEL"):
        raise HTTPException(
            status_code=400,
            detail=f"Document is in '{record.status}' state — cannot sign off.",
        )

    # Compute state hash (locks the verified extracted state)
    state_payload = (
        f"{req.tracking_id}|{req.officer_id}|{req.dsc_signature}"
        f"|{record.extracted_area}|{record.gis_area}|{record.cis_score}"
    )
    extracted_state_sha256 = hashlib.sha256(state_payload.encode()).hexdigest()

    # Persist sign-off
    crud.update_dsc_signoff(
        db,
        tracking_id=req.tracking_id,
        officer_id=req.officer_id,
        dsc_signature=req.dsc_signature,
        extracted_state_sha256=extracted_state_sha256,
    )

    # Build DigiLocker e-RoR payload (PRD §5.4)
    digilocker_payload = {
        "documentType": "e-RoR",
        "trackingId": req.tracking_id,
        "officerId": req.officer_id,
        "issuedAt": datetime.now(timezone.utc).isoformat(),
        "rawDocumentHash": record.raw_document_sha256,
        "stateHash": extracted_state_sha256,
        "data": {
            "sourceArea": record.source_area_claim,
            "extractedArea": record.extracted_area,
            "gisArea": record.gis_area,
            "cisScore": record.cis_score,
            "varianceDelta": record.variance_delta,
        },
    }

    return SignOffResponse(
        tracking_id=req.tracking_id,
        extracted_state_sha256=extracted_state_sha256,
        status="DSC_APPROVED",
        message="Record certified. e-RoR payload ready for DigiLocker push.",
        digilocker_payload=digilocker_payload,
    )
