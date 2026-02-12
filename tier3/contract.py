from typing import Literal

TIER3_VERSION = "3.0"

QUALITY_WEIGHT = 0.7
RISK_WEIGHT = 0.3

APPROVE_THRESHOLD = 0.75
REVIEW_THRESHOLD = 0.45

ROUND_PRECISION = 4


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(value, max_value))


def compute_score(quality_score: float, risk_score: float) -> float:
    raw_score = (QUALITY_WEIGHT * quality_score) - (RISK_WEIGHT * risk_score)
    final_score = clamp(raw_score)
    return round(final_score, ROUND_PRECISION)


def derive_decision(score: float) -> Literal["approve", "review", "reject"]:
    if score >= APPROVE_THRESHOLD:
        return "approve"
    elif score >= REVIEW_THRESHOLD:
        return "review"
    else:
        return "reject"
