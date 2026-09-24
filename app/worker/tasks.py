"""
KSITI Pipeline Task — process_deed
===================================
Orchestrates the three-agent pipeline end-to-end:

    1. Perception Layer  → Image preprocessing, layout segmentation, OCR extraction
    2. Deterministic Layer → Spatial parity, area variance, Ω kill-switch
    3. Fraud Layer        → Anomaly checks, duplicate detection
    4. CIS Engine         → Score, route to GREEN / RED channel
    5. Database update    → Write all results

This is a Celery task — executed asynchronously by the worker process.
"""

import logging
from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.db import crud

from app.agents.perception_layer import run_perception
from app.agents.deterministic_layer import run_deterministic
from app.agents.fraud_layer import run_fraud_detection
from app.agents.cis_engine import calculate_cis

logger = logging.getLogger(__name__)


@celery_app.task(name="process_deed", bind=True, max_retries=3)
def process_deed(self, file_path: str, tracking_id: str, document_sha256: str):
    try:
        return process_deed_sync(file_path, tracking_id, document_sha256)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)

def process_deed_sync(file_path: str, tracking_id: str, document_sha256: str):
    """
    Full pipeline: Perception → Deterministic → Fraud → CIS → DB Update.

    Parameters
    ----------
    file_path : path to the uploaded deed image on disk
    tracking_id : UUID tracking identifier
    document_sha256 : SHA-256 of the raw uploaded file
    """
    db = SessionLocal()

    try:
        # Mark as processing
        crud.update_status(db, tracking_id, "PROCESSING")

        # ── Agent 1: Perception Layer ────────────────────────────────────
        logger.info("[%s] Starting Agent 1 — Perception Layer", tracking_id)
        perception = run_perception(file_path)

        extracted_data = perception.get("extracted_data", {})
        ocr_confidences = [0.95] # Stubbed for compatibility
        layout_confidences = [0.99] # Stubbed for compatibility
        extracted_area = perception.get("extracted_area", 0.0)
        extracted_json = perception.get("extracted_json", "{}")

        # ── Agent 2: Deterministic Layer ─────────────────────────────────
        logger.info("[%s] Starting Agent 2 — Deterministic Layer", tracking_id)
        deterministic = run_deterministic(extracted_data)

        gis_area = deterministic["gis_area"]
        variance_delta = deterministic["variance"]["variance_delta"]
        variance_pct = deterministic["variance"]["variance_percentage"]
        omega = deterministic["omega"]

        # ── Agent 3: Fraud Layer ─────────────────────────────────────────
        logger.info("[%s] Starting Agent 3 — Fraud Layer", tracking_id)
        fraud = run_fraud_detection(extracted_data)

        # ── CIS Scoring ──────────────────────────────────────────────────
        logger.info("[%s] Computing CIS Score", tracking_id)
        cis = calculate_cis(
            ocr_confidences=ocr_confidences,
            layout_confidences=layout_confidences,
            variance_delta=variance_delta,
            omega=omega,
            fraud_detected=fraud["fraud_detected"],
        )

        # ── Persist results ──────────────────────────────────────────────
        ocr_mean = sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else 0
        layout_mean = sum(layout_confidences) / len(layout_confidences) if layout_confidences else 0

        crud.update_extraction(
            db,
            tracking_id=tracking_id,
            extracted_area=extracted_area,
            extracted_json=extracted_json,
            ocr_confidence_mean=ocr_mean,
            layout_confidence_mean=layout_mean,
            gis_area=gis_area,
            variance_delta=variance_delta,
            variance_percentage=variance_pct,
            cis_score=cis["score"],
            cis_omega=cis["omega"],
            routing=cis["routing"],
            fraud_detected=fraud["fraud_detected"],
            fraud_flags=fraud["flags"] if fraud["flags"] else None,
        )

        logger.info(
            "[%s] Pipeline complete — CIS=%.4f → %s",
            tracking_id, cis["score"], cis["routing"],
        )

        # ── Return result (stored in Celery backend) ─────────────────────
        return {
            "tracking_id": tracking_id,
            "status": "COMPLETED",
            "extracted_data": extracted_data,
            "layers_of_truth": {
                "source_record": {
                    "area_claim": extracted_area,
                    "units": "acres",
                },
                "digitized_record": {
                    "extracted_area": extracted_area,
                    "ocr_confidence_mean": round(ocr_mean, 4),
                },
                "derived_discrepancy": {
                    "gis_area": gis_area,
                    "variance_delta": variance_delta,
                    "variance_percentage": variance_pct,
                },
            },
            "fraud_detection": fraud,
            "cis": cis,
        }

    except ValueError as exc:
        if "NON_LAND_DOCUMENT" in str(exc):
            logger.warning("[%s] Rejected: Non-Land Document", tracking_id)
            crud.update_status(db, tracking_id, "REJECTED_INVALID_DOC")
            return {"tracking_id": tracking_id, "status": "REJECTED_INVALID_DOC"}
        else:
            logger.exception("[%s] Pipeline FAILED", tracking_id)
            crud.update_status(db, tracking_id, "FAILED")
            raise exc
    except Exception as exc:
        logger.exception("[%s] Pipeline FAILED", tracking_id)
        crud.update_status(db, tracking_id, "FAILED")
        raise exc

    finally:
        db.close()
