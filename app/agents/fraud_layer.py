"""
Agent 3 — Fraud & Anomaly Layer (SPEC.md §4, Agent 3)
======================================================
Identifies suspicious patterns and metadata conflicts:
  • Duplicate Khata numbers
  • Conflicting registration / mutation dates
  • Missing mandatory encumbrance documents
  • Statistical anomaly detection (Isolation Forest / XGBoost stub)

Pure analysis — no DB mutations.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def detect_duplicate_khata(khata_number: str, existing_khatas: List[str] = None) -> bool:
    """
    Check if this Khata number already exists in the registry.
    MVP stub — in production queries the DB.
    """
    if existing_khatas is None:
        existing_khatas = []  # No data available in MVP
    return khata_number in existing_khatas


def detect_date_conflicts(mutation_date: str) -> bool:
    """
    Flag if the mutation date is in the future or suspiciously old.
    """
    from datetime import datetime
    try:
        dt = datetime.strptime(mutation_date, "%Y-%m-%d")
        if dt > datetime.now():
            logger.warning("Future mutation date detected: %s", mutation_date)
            return True
    except (ValueError, TypeError):
        logger.warning("Invalid mutation date format: %s", mutation_date)
        return True
    return False


def detect_encumbrance_anomaly(encumbrance_status: str) -> bool:
    """Flag missing or suspicious encumbrance declarations."""
    if not encumbrance_status or encumbrance_status.strip().lower() in ("", "unknown", "n/a"):
        logger.warning("Missing or invalid encumbrance status")
        return True
    return False


def run_anomaly_model(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Statistical anomaly detection using scikit-learn IsolationForest.
    Builds a robust evaluation of tabular features.
    """
    try:
        from sklearn.ensemble import IsolationForest
        import numpy as np
        
        # Fit a model on standard synthetic "healthy" cadastral data profile
        # In production, this is loaded from a pre-trained .pkl file
        healthy_samples = np.array([
            [1.0, 0.95, 0.0], [1.02, 0.92, 0.0], [0.99, 0.98, 0.0],
            [1.05, 0.90, 0.0], [0.98, 0.96, 0.0], [1.0, 0.99, 0.0]
        ])
        
        clf = IsolationForest(random_state=42, contamination=0.1)
        clf.fit(healthy_samples)
        
        # Extract features for prediction
        x_pred = np.array([[
            features.get("area_ratio", 1.0),
            features.get("ocr_confidence_mean", 1.0),
            features.get("subdivision_excess", 0.0)
        ]])
        
        prediction = clf.predict(x_pred)[0]  # 1 for normal, -1 for anomaly
        decision_score = clf.decision_function(x_pred)[0] # Lower is more anomalous
        
        is_anomaly = bool(prediction == -1)
        # Normalize score to 0.0 - 1.0 range representing anomaly intensity
        anomaly_score = max(0.0, float(-decision_score)) 
        
        logger.info(f"IsolationForest evaluated features. Score: {anomaly_score:.4f}, Anomaly: {is_anomaly}")
        
    except ImportError:
        logger.warning("scikit-learn not installed, falling back to heuristic MVP anomaly model")
        anomaly_score = 0.0
        area_ratio = features.get("area_ratio", 1.0)
        if area_ratio < 0.8 or area_ratio > 1.2: anomaly_score += 0.4
        if features.get("ocr_confidence_mean", 1.0) < 0.7: anomaly_score += 0.3
        if features.get("subdivision_excess", 0) > 0: anomaly_score += 0.5
        is_anomaly = anomaly_score > 0.5

    return {
        "anomaly_score": round(anomaly_score, 4),
        "is_anomaly": is_anomaly,
    }



def run_fraud_detection(extracted_data: dict) -> Dict[str, Any]:
    """
    Execute the full Agent 3 pipeline.

    Returns:
        {
            "fraud_detected": bool,
            "flags": list[str],   # human-readable flag descriptions
        }
    """
    flags: List[str] = []

    khata = extracted_data.get("khata_number", "")
    if detect_duplicate_khata(khata):
        flags.append(f"DUPLICATE_KHATA: Khata {khata} already exists in registry")

    mutation_date = extracted_data.get("mutation_date", "")
    if detect_date_conflicts(mutation_date):
        flags.append(f"DATE_CONFLICT: Mutation date '{mutation_date}' is invalid or future-dated")

    encumbrance = extracted_data.get("encumbrance_status", "")
    if detect_encumbrance_anomaly(encumbrance):
        flags.append("MISSING_ENCUMBRANCE: Encumbrance status not declared")

    # Statistical model
    features = {
        "area_ratio": 1.0,  # Would be computed from actual GIS vs extracted
        "ocr_confidence_mean": 0.95,
        "subdivision_excess": 0,
    }
    model_result = run_anomaly_model(features)
    if model_result["is_anomaly"]:
        flags.append(f"STATISTICAL_ANOMALY: Score {model_result['anomaly_score']}")

    fraud_detected = len(flags) > 0

    if fraud_detected:
        logger.warning("Fraud flags raised: %s", flags)
    else:
        logger.info("No fraud indicators detected")

    return {
        "fraud_detected": fraud_detected,
        "flags": flags,
    }
