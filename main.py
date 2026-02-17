import os
import aiohttp, asyncio
from fastapi import FastAPI
from pydantic import BaseModel

TIER4_URL = os.getenv("TIER4_URL", "https://seekreap-tier-4-orchestrator-nrn4.onrender.com/process")

class MonetizationScorer:
    def score(self, semantic_output: dict) -> dict:
        quality_score = semantic_output.get("quality_score", 0.8)
        risk_score = semantic_output.get("risk_score", 0.2)
        final_score = quality_score - risk_score
        decision = "approve" if final_score >= 0.5 else "reject"
        return {
            "score": final_score,
            "decision": decision,
            "risk_score": risk_score,
            "quality_score": quality_score,
        }

app = FastAPI()
scorer = MonetizationScorer()

@app.get("/")
def health():
    return {"status": "Tier-3 is running"}

class Envelope(BaseModel):
    content: str
    quality_score: float = 0.8
    risk_score: float = 0.2

@app.post("/compute")
def compute(envelope: Envelope):
    semantic_output = {"quality_score": envelope.quality_score, "risk_score": envelope.risk_score}
    return scorer.score(semantic_output)

async def call_tier4(payload: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(TIER4_URL, json=payload) as resp:
            return await resp.json()

@app.post("/verify")
async def verify(envelope: Envelope):
    payload = {
        "task_id": "t3_" + envelope.content[:6],
        "task_type": "monetization",
        "inputs": envelope.dict(),
        "context": {}
    }
    tier4_response = await call_tier4(payload)
    local_score = scorer.score({"quality_score": envelope.quality_score, "risk_score": envelope.risk_score})
    return {"tier3_score": local_score, "tier4_response": tier4_response}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10001))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
