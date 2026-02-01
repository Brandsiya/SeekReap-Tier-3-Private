from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tier3.api import score_envelope, process_batch

app = FastAPI(title="SeekReap Tier-3 API")

# Input model for a single envelope
class Envelope(BaseModel):
    id: str
    value: float
    _version: str
    _processed_by: str
    behavior_type: str
    intensity: float
    duration: int
    premium_indicator: bool

# Single envelope endpoint
@app.post("/score")
def score_single(envelope: Envelope):
    try:
        result = score_envelope(envelope.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Batch endpoint
@app.post("/score_batch")
def score_batch(batch: list[Envelope]):
    try:
        batch_results = process_batch([env.dict() for env in batch])
        return batch_results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
