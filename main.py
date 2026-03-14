from fastapi import FastAPI
from typing import Dict
from pydantic import BaseModel

app = FastAPI()

def compute_risk_score(audio_similarity: float = 0.0,
                       visual_similarity: float = 0.0,
                       metadata_flags: int = 0) -> tuple[float, str]:
    meta_score = min(metadata_flags / 5.0, 1.0)
    risk_score = (
        audio_similarity * 0.5 +
        visual_similarity * 0.3 +
        meta_score * 0.2
    )
    risk_score = max(0.0, min(risk_score, 1.0))
    if risk_score >= 0.75:
        risk_level = "high"
    elif risk_score >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"
    return risk_score, risk_level

class AnalyzeRequest(BaseModel):
    content_id: str
    content_type: str
    content_data: Dict

@app.post("/api/analyze")
async def analyze_content(req: AnalyzeRequest) -> Dict:
    result = {
        "content_id": req.content_id,
        "content_type": req.content_type,
        "signals": req.content_data,
    }

    score, level = compute_risk_score(
        audio_similarity=req.content_data.get("audio_similarity", 0.0),
        visual_similarity=req.content_data.get("visual_similarity", 0.0),
        metadata_flags=len(req.content_data.get("flags", []))
    )

    result["risk_score"] = score
    result["risk_level"] = level
    return result

@app.get("/health")
async def health_check():
    return {"status": "ok"}
