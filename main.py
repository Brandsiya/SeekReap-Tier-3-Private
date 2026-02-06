from fastapi import FastAPI
from consensus_engine import ConsensusEngine
import uvicorn
from pydantic import BaseModel

app = FastAPI(title="SeekReap Tier-3 Distributed Network")
engine = ConsensusEngine([
    "http://localhost:8001",  # tier2-node1
    "http://localhost:8002",  # tier2-node2  
    "http://localhost:8003"   # tier2-node3
])

class VerifyRequest(BaseModel):
    reap_id: str

@app.post("/v3/verify")
async def distributed_verify(request: VerifyRequest):
    result = await engine.verify_distributed(request.reap_id)
    return {
        "reap_id": result.reap_id,
        "human_verified": result.consensus,
        "confidence": result.score,
        "quorum": f"{result.node_votes}/{result.total_nodes}"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
