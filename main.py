from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
from typing import Optional, Dict, Any, List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


class ContentData(BaseModel):
    audio_similarity: Optional[float] = 0.0
    visual_similarity: Optional[float] = 0.0
    duplicate_content: Optional[bool] = False
    flags: Optional[List[str]] = []


class AnalyzeRequest(BaseModel):
    submission_id: Optional[str] = None
    contentid: Optional[str] = None
    content_id: Optional[str] = None
    contenthash: Optional[str] = None
    content_hash: Optional[str] = None
    contenttype: Optional[str] = None
    content_type: Optional[str] = None
    contentdata: Optional[Dict[str, Any]] = None


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    """
    Stateless risk analysis — called by Tier-5.
    DOES NOT write to DB. Returns risk_score + risk_level only.
    Tier-5 is the single authority for all DB state changes.
    """
    try:
        data = request.dict()

        submission_id = data.get("submission_id") or str(uuid.uuid4())
        content_type  = (
            data.get("contenttype") or data.get("content_type") or "audio"
        )
        contentdata = data.get("contentdata") or {}

        def safe_float(val, default=0.0):
            try:
                return float(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        audio_sim  = safe_float(contentdata.get("audio_similarity"))
        visual_sim = safe_float(contentdata.get("visual_similarity"))
        dup        = bool(contentdata.get("duplicate_content") or False)
        flags      = contentdata.get("flags") or []

        print(
            f"ANALYZE submission={submission_id} type={content_type} "
            f"audio={audio_sim} visual={visual_sim}"
        )

        risk_score = max(audio_sim, visual_sim)
        if dup:
            risk_score = min(1.0, risk_score + 0.3)

        if risk_score >= 0.8:
            risk_level = "critical"
        elif risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "status":        "analyzed",
            "submission_id": submission_id,
            "risk_score":    risk_score,
            "risk_level":    risk_level,
            "details": {
                "audio_similarity":  audio_sim,
                "visual_similarity": visual_sim,
                "duplicate_content": dup,
                "flags":             flags,
            },
        }

    except Exception as e:
        import traceback
        print(f"Analyze error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
