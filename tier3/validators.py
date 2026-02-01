class EnvelopeValidationError(Exception):
    """Custom exception for invalid envelopes."""
    pass

def validate_tier2_envelope(envelope: dict):
    """
    Validates a Tier-2 envelope against the Tier-3 contract.
    Raises EnvelopeValidationError if validation fails.
    """
    version = envelope.get("_version")
    if not isinstance(version, str) or version.count(".") != 2:
        raise EnvelopeValidationError(f"Invalid _version: {version}")

    if envelope.get("_processed_by") != "tier2":
        raise EnvelopeValidationError(f"Envelope not processed by tier2: {envelope.get('_processed_by')}")

    if not isinstance(envelope.get("behavior_type"), str) or not envelope["behavior_type"]:
        raise EnvelopeValidationError("Invalid behavior_type")
    if not isinstance(envelope.get("intensity"), (float, int)) or envelope["intensity"] < 0:
        raise EnvelopeValidationError("Invalid intensity")
    if not isinstance(envelope.get("duration"), int) or envelope["duration"] < 0:
        raise EnvelopeValidationError("Invalid duration")
    if not isinstance(envelope.get("premium_indicator"), bool):
        raise EnvelopeValidationError("Invalid premium_indicator")

    return True
