"""
Tier-3 Canonical API
Defines standard entry points for processing envelopes and returning
Tier-4-ready outputs.
"""

from typing import TypedDict, Any
from tier3.validators import validate_tier2_envelope

# ----------------------------
# Tier4Output TypedDict
# ----------------------------
class Tier4Output(TypedDict):
    envelope_id: str
    score: float
    metadata: dict[str, Any]
    status: str

# =============================
# Auto-version wrapper for Tier-3
# =============================
DEFAULT_TIER2_VERSION = "v2"

def ensure_version(envelope: dict) -> dict:
    """Ensure envelope has the correct _version for Tier-3."""
    if "_version" not in envelope:
        envelope["_version"] = DEFAULT_TIER2_VERSION
    return envelope

# ----------------------------
# Original functions
# ----------------------------
def _original_process_input(envelope: dict) -> dict:
    validate_tier2_envelope(envelope)
    processed = envelope.copy()
    return processed

def _original_score_envelope(envelope: dict) -> Tier4Output:
    processed = _original_process_input(envelope)
    score = float(processed.get("value", 0))
    envelope_id = str(processed.get("id", "unknown"))
    return Tier4Output(
        envelope_id=envelope_id,
        score=score,
        metadata={"processed": True},
        status="success"
    )

def _original_process_batch(envelopes: list[dict]) -> list[Tier4Output]:
    return [_original_score_envelope(e) for e in envelopes]

# ----------------------------
# Wrapped functions with auto-version
# ----------------------------
def process_input(envelope: dict) -> dict:
    return _original_process_input(ensure_version(envelope))

def score_envelope(envelope: dict) -> Tier4Output:
    return _original_score_envelope(ensure_version(envelope))

def process_batch(envelopes: list[dict]) -> list[Tier4Output]:
    return [_original_score_envelope(ensure_version(e)) for e in envelopes]
