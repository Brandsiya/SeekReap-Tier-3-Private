def validate_envelope(envelope: dict) -> None:
    if not isinstance(envelope, dict):
        raise TypeError("Envelope must be a dictionary")

    if "content" not in envelope:
        raise ValueError("Missing 'content' field")

    if not isinstance(envelope["content"], str):
        raise TypeError("'content' must be a string")

    if "metadata" not in envelope:
        raise ValueError("Missing 'metadata' field")

    if "context" not in envelope:
        raise ValueError("Missing 'context' field")
