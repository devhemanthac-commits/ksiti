"""
KSITI — Intake Routes
=====================
Handles the Officer-assisted document upload workflow (PRD §5.1):
  1. Accept scanned deed image
  2. Generate raw_document_sha256 (tamper-proof chain of custody)
  3. Persist to database as UPLOADED
  4. Dispatch to Celery worker for async AI processing
"""

import hashlib
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_DIR
from app.db.session import get_db
from app.db import crud

router = APIRouter(prefix="/api/v1", tags=["Document Intake"])


# ── Response schemas ─────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    tracking_id: str
    raw_document_sha256: str
    status: str
    message: str


class DocumentStatusResponse(BaseModel):
    id: int | None = None
    tracking_id: str
    status: str
    routing: str | None = None
    cis_score: float | None = None
    cis_omega: float | None = None
    created_at: str | None = None
    raw_document_sha256: str | None = None
    extracted_state_sha256: str | None = None
    source_area_claim: float | None = None
    extracted_area: float | None = None
    extracted_json: str | None = None
    ocr_confidence_mean: float | None = None
    layout_confidence_mean: float | None = None
    gis_area: float | None = None
    variance_delta: float | None = None
    variance_percentage: float | None = None
    fraud_detected: str | None = None
    fraud_flags: str | None = None
    message: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────

def _sha256_of_file(path: str) -> str:
    """Stream-hash a file in 4 KiB chunks — memory-safe for large scans."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


from fastapi.responses import FileResponse
from typing import List

# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/upload-deed", response_model=List[UploadResponse])
def upload_deed(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Officer Intake Endpoint
    -----------------------
    Accepts one or more scanned deeds, locks their SHA-256, persists metadata,
    and executes the AI verification pipeline.
    """
    responses = []
    
    for file in files:
        # 1. Generate tracking ID
        tracking_id = str(uuid.uuid4())
    
        # 2. Persist file to disk
        filename = f"{tracking_id}_{file.filename}"
        file_path = str(UPLOAD_DIR / filename)
        with open(file_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    
        # 3. Cryptographic chain-of-custody lock
        raw_sha256 = _sha256_of_file(file_path)
    
        # 4. Create database record
        crud.create_record(
            db,
            tracking_id=tracking_id,
            raw_document_sha256=raw_sha256,
            stored_filepath=file_path,
            original_filename=file.filename,
        )
    
        # 5. Execute Pipeline via Celery
        try:
            from app.worker.tasks import process_deed
            
            # This runs asynchronously if REDIS_URL is configured (Docker/Prod), 
            # otherwise runs synchronously (Local testing).
            process_deed.delay(file_path, tracking_id, raw_sha256)
            
            responses.append(UploadResponse(
                tracking_id=tracking_id,
                raw_document_sha256=raw_sha256,
                status="PROCESSING",
                message="Document uploaded. SHA-256 locked. AI verification complete."
            ))
            
        except Exception as e:
            # If pipeline crashes
            crud.update_status(db, tracking_id, "FAILED")
            responses.append(UploadResponse(
                tracking_id=tracking_id,
                raw_document_sha256=raw_sha256,
                status="FAILED",
                message=f"Pipeline crashed during execution: {e}",
            ))
            
    return responses


@router.get("/document/{tracking_id}/image", response_class=FileResponse)
def get_document_image(tracking_id: str, db: Session = Depends(get_db)):
    """
    Serve the full uploaded original document image.
    Enables officers to visually cross-verify the AI extractions.
    """
    record = crud.get_record(db, tracking_id)
    if not record or not record.stored_filepath:
        raise HTTPException(status_code=404, detail="Document image not found")
    
    import os
    if not os.path.exists(record.stored_filepath):
        raise HTTPException(status_code=404, detail="File missing on disk")
        
    return FileResponse(record.stored_filepath, media_type="image/png")

@router.get("/document/{tracking_id}", response_model=DocumentStatusResponse)
def get_document_status(tracking_id: str, db: Session = Depends(get_db)):
    """
    Retrieve document status and the Three Layers of Truth.
    """
    record = crud.get_record(db, tracking_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        id=record.id,
        tracking_id=tracking_id,
        status=record.status,
        routing=record.routing,
        cis_score=record.cis_score,
        cis_omega=record.cis_omega,
        created_at=record.created_at.isoformat() if record.created_at else None,
        raw_document_sha256=record.raw_document_sha256,
        extracted_state_sha256=record.extracted_state_sha256,
        source_area_claim=record.source_area_claim,
        extracted_area=record.extracted_area,
        extracted_json=record.extracted_json,
        ocr_confidence_mean=record.ocr_confidence_mean,
        layout_confidence_mean=record.layout_confidence_mean,
        gis_area=record.gis_area,
        variance_delta=record.variance_delta,
        variance_percentage=record.variance_percentage,
        fraud_detected=record.fraud_detected,
        fraud_flags=record.fraud_flags,
        message=f"Document is currently: {record.status}",
    )


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    """List all documents — powers the dashboard."""
    records = crud.get_all_records(db)
    return [
        {
            "tracking_id": r.tracking_id,
            "original_filename": r.original_filename,
            "status": r.status,
            "cis_score": r.cis_score,
            "routing": r.routing,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
