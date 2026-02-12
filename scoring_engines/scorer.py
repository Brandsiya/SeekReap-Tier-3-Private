from tier3.contract import compute_score, derive_decision

class MonetizationScorer:

    def score(self, semantic_output: dict) -> dict:
        quality_score = semantic_output["quality_score"]
        risk_score = semantic_output["risk_score"]

        final_score = compute_score(quality_score, risk_score)
        decision = derive_decision(final_score)

        return {
            "score": final_score,
            "decision": decision,
            "risk_score": risk_score,
            "quality_score": quality_score,
        }
