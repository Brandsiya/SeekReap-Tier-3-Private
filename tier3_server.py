from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tier3.contract import TIER3_VERSION, compute_score, derive_decision
from tier3.validators import validate_envelope

class DummyProcessor:
    def process(self, content: str) -> dict:
        return {"quality_score": 0.8, "risk_score": 0.2}

processor = DummyProcessor()

def score_envelope(envelope: dict) -> dict:
    validate_envelope(envelope)
    semantic_output = processor.process(envelope["content"])
    final_score = compute_score(semantic_output["quality_score"], semantic_output["risk_score"])
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
    return [score_envelope(e) for e in envelopes]

app = FastAPI()

class Envelope(BaseModel):
    content: str

@app.post("/compute")
def compute(envelope: Envelope):
    try:
        return score_envelope(envelope.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/compute-batch")
def compute_batch(envelopes: list[Envelope]):
    try:
        return process_batch([e.dict() for e in envelopes])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
