from tier3.contract import TIER3_VERSION, compute_score, derive_decision
from tier3.validators import validate_envelope


class DummyProcessor:
    def process(self, content: str) -> dict:
        # Deterministic mock processing
        return {
            "quality_score": 0.8,
            "risk_score": 0.2,
        }


processor = DummyProcessor()


def score_envelope(envelope: dict) -> dict:
    validate_envelope(envelope)

    semantic_output = processor.process(envelope["content"])

    final_score = compute_score(
        semantic_output["quality_score"],
        semantic_output["risk_score"],
    )

    decision = derive_decision(final_score)

    return {
        "score": final_score,
        "decision": decision,
        "risk_score": semantic_output["risk_score"],
        "quality_score": semantic_output["quality_score"],
        "version": TIER3_VERSION,
        "deterministic": True,
    }


def process_batch(envelopes: list[dict]) -> list[dict]:
    results = []
    for envelope in envelopes:
        results.append(score_envelope(envelope))
    return results
