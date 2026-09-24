"""
Cadastral Integrity Score (CIS) Engine — SPEC.md §5
====================================================
Implements the non-linear probabilistic-deterministic hybrid model:

    S_CIS = Ω · [ w₁·H(p) + w₂·G(ΔA) + w₃·L(c) ]

Where:
    Ω   = Boolean statutory kill-switch (0 if any rule fails)
    H(p) = Harmonic mean of OCR confidences
    G(ΔA) = Gaussian spatial decay  exp(−ΔA² / 2τ²)
    L(c)  = Arithmetic mean of layout segmentation confidences

    w₁ = 0.40,  w₂ = 0.40,  w₃ = 0.20
    τ  = statutory survey tolerance (default 0.05 acres)

Routing:
    S_CIS ≥ 0.85 → GREEN_CHANNEL
    S_CIS <  0.85 → RED_CHANNEL
"""

import math
import logging
from typing import Dict, Any, List

from app.core.config import CIS_W1, CIS_W2, CIS_W3, CIS_TAU, CIS_GREEN_THRESHOLD

logger = logging.getLogger(__name__)


def harmonic_mean(values: List[float]) -> float:
    """
    H(p) = N / Σ(1/pᵢ)

    Penalises uncertainty severely — if even one field has low confidence,
    the entire harmonic mean collapses.
    """
    if not values:
        return 0.0

    # Filter out zeros to avoid division by zero
    nonzero = [v for v in values if v > 0]
    if not nonzero:
        return 0.0

    n = len(nonzero)
    reciprocal_sum = sum(1.0 / v for v in nonzero)
    return n / reciprocal_sum


def gaussian_spatial_decay(variance_delta: float, tau: float = None) -> float:
    """
    G(ΔA) = exp(−ΔA² / 2τ²)

    Exponentially lowers the score as the text-area deviates from
    the PostGIS geographic area beyond the legal survey tolerance.
    """
    if tau is None:
        tau = CIS_TAU
    if tau == 0:
        return 0.0
    return math.exp(-(variance_delta ** 2) / (2 * tau ** 2))


def layout_confidence_mean(confidences: List[float]) -> float:
    """
    L(c) = (1/M) · Σ cⱼ

    Simple arithmetic mean of YOLOv8 bounding box confidence scores.
    """
    if not confidences:
        return 0.0
    return sum(confidences) / len(confidences)


def calculate_cis(
    ocr_confidences: List[float],
    layout_confidences: List[float],
    variance_delta: float,
    omega: float,
    fraud_detected: bool = False,
) -> Dict[str, Any]:
    """
    Compute the full Cadastral Integrity Score.

    Parameters
    ----------
    ocr_confidences : per-field OCR confidence values
    layout_confidences : per-region YOLOv8 confidence values
    variance_delta : |A_text − A_GIS| in acres
    omega : statutory kill-switch (1.0 = pass, 0.0 = fail)
    fraud_detected : if True, forces Ω = 0

    Returns
    -------
    dict with score, components, routing, and omega value.
    """
    # If fraud is detected, kill-switch fires
    if fraud_detected:
        omega = 0.0
        logger.warning("Ω forced to 0 — fraud detected")

    # Compute components
    h = harmonic_mean(ocr_confidences)
    g = gaussian_spatial_decay(variance_delta)
    l_score = layout_confidence_mean(layout_confidences)

    # Weighted combination
    raw_score = CIS_W1 * h + CIS_W2 * g + CIS_W3 * l_score

    # Apply kill-switch
    final_score = omega * raw_score

    # Routing decision
    if final_score >= CIS_GREEN_THRESHOLD:
        routing = "GREEN_CHANNEL"
    else:
        routing = "RED_CHANNEL"

    logger.info(
        "CIS: Ω=%.1f  H(p)=%.4f  G(ΔA)=%.4f  L(c)=%.4f  "
        "raw=%.4f  final=%.4f → %s",
        omega, h, g, l_score, raw_score, final_score, routing,
    )

    return {
        "score": round(final_score, 4),
        "routing": routing,
        "omega": omega,
        "components": {
            "harmonic_mean_ocr": round(h, 4),
            "gaussian_spatial_decay": round(g, 4),
            "layout_confidence_mean": round(l_score, 4),
        },
        "weights": {"w1": CIS_W1, "w2": CIS_W2, "w3": CIS_W3},
        "threshold": CIS_GREEN_THRESHOLD,
    }
