from tier3.validators import validate_envelope

def score_envelope(envelope: dict) -> dict:
    validate_envelope(envelope)

    semantic_output = processor.process(envelope["content"])
    result = scorer.score(semantic_output)

    return {
        "score": result["score"],
        "decision": result["decision"],
        "risk_score": result["risk_score"],
        "quality_score": result["quality_score"],
        "version": TIER3_VERSION,
        "deterministic": True,
    }
