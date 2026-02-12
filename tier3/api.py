from tier3.contract import TIER3_VERSION

def score_envelope(envelope: dict) -> dict:
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
