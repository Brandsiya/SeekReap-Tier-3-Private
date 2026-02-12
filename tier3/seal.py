import json
import hashlib

from tier3.contract import (
    TIER3_VERSION,
    QUALITY_WEIGHT,
    RISK_WEIGHT,
    APPROVE_THRESHOLD,
    REVIEW_THRESHOLD,
    ROUND_PRECISION,
)


def contract_fingerprint() -> str:
    contract_spec = {
        "TIER3_VERSION": TIER3_VERSION,
        "QUALITY_WEIGHT": QUALITY_WEIGHT,
        "RISK_WEIGHT": RISK_WEIGHT,
        "APPROVE_THRESHOLD": APPROVE_THRESHOLD,
        "REVIEW_THRESHOLD": REVIEW_THRESHOLD,
        "ROUND_PRECISION": ROUND_PRECISION,
    }

    canonical = json.dumps(contract_spec, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
