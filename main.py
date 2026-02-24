from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import os
import json

app = FastAPI(title="SeekReap Tier-3 Private Semantic Layer")

# Define the envelope structure from Tier-2
class Tier2Envelope(BaseModel):
    id: str
    timestamp: float
    payload: Any
    schema_version: str
    orchestration_policy: str
    signature: str
    metadata: Optional[Dict[str, Any]] = None

class DecisionResponse(BaseModel):
    envelope_id: str
    decision: str
    confidence: float
    risk_factors: List[str] = []
    appeal_text: Optional[str] = None
    version: str = "3.0.0"

class MonetizationScorer:
    def score_reap(self, reap_data: Any) -> Dict[str, Any]:
        """Score a verified reap object"""
        # Extract data from reap object
        try:
            # Handle different possible formats
            if hasattr(reap_data, 'status'):
                # It's a Reap object from Tier-1
                status = reap_data.status
                score = getattr(reap_data, 'score', 0.0)
                behaviors = getattr(reap_data, 'behaviors', [])
                behavior_count = len(behaviors) if behaviors else 0
            elif isinstance(reap_data, dict):
                # It's a dictionary representation
                status = reap_data.get('status', 'unknown')
                score = reap_data.get('score', 0.0)
                behaviors = reap_data.get('behaviors', [])
                behavior_count = len(behaviors) if behaviors else 0
            else:
                status = 'unknown'
                score = 0.0
                behavior_count = 0
            
            # Make decision based on verification status
            if status == 'verified' and score >= 0.7:
                decision = "APPROVE"
                confidence = min(score, 1.0)
                risk_factors = []
                appeal_text = "Content meets all guidelines."
            elif status == 'verified' and score < 0.7:
                decision = "REVIEW"
                confidence = score
                risk_factors = ["Low verification score"]
                appeal_text = "Additional verification needed."
            elif status == 'rejected':
                decision = "REJECT"
                confidence = score
                risk_factors = ["Failed verification", f"Only {behavior_count} behaviors recorded (need 3)"]
                appeal_text = "Insufficient attention evidence. Please try again."
            else:
                decision = "PENDING"
                confidence = 0.0
                risk_factors = ["Verification not completed"]
                appeal_text = "Processing..."
            
            return {
                "decision": decision,
                "confidence": round(confidence, 4),
                "risk_factors": risk_factors,
                "appeal_text": appeal_text
            }
        except Exception as e:
            return {
                "decision": "ERROR",
                "confidence": 0.0,
                "risk_factors": [f"Processing error: {str(e)}"],
                "appeal_text": "Error processing verification result."
            }
    
    def score_behavior(self, behavior_data: Any) -> Dict[str, Any]:
        """Score a behavior object"""
        try:
            if hasattr(behavior_data, 'type'):
                behavior_type = behavior_data.type
                intensity = behavior_data.intensity
            elif isinstance(behavior_data, dict):
                behavior_type = behavior_data.get('type', 'unknown')
                intensity = behavior_data.get('intensity', 0.0)
            else:
                behavior_type = 'unknown'
                intensity = 0.0
            
            # Analyze behavior quality
            quality_score = intensity
            
            return {
                "decision": "RECORDED",
                "confidence": quality_score,
                "risk_factors": [] if quality_score > 0.5 else ["Low quality behavior"],
                "appeal_text": None
            }
        except Exception as e:
            return {
                "decision": "ERROR",
                "confidence": 0.0,
                "risk_factors": [f"Behavior processing error: {str(e)}"],
                "appeal_text": None
            }

scorer = MonetizationScorer()

@app.get("/")
def health():
    return {"status": "Tier-3 Private Layer running", "version": "3.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "tier": 3}

@app.post("/process-envelope", response_model=DecisionResponse)
async def process_envelope(envelope: Tier2Envelope):
    """Process a Tier-2 semantic envelope and return a decision"""
    try:
        print(f"Processing envelope: {envelope.id}")
        print(f"Policy: {envelope.orchestration_policy}")
        
        # Process based on the policy
        if envelope.orchestration_policy == "reap_verification":
            result = scorer.score_reap(envelope.payload)
        elif envelope.orchestration_policy == "behavior_recording":
            result = scorer.score_behavior(envelope.payload)
        elif envelope.orchestration_policy == "seeker_creation":
            result = {
                "decision": "ACCEPTED",
                "confidence": 1.0,
                "risk_factors": [],
                "appeal_text": "Seeker created successfully."
            }
        elif envelope.orchestration_policy == "reap_creation":
            result = {
                "decision": "ACCEPTED",
                "confidence": 1.0,
                "risk_factors": [],
                "appeal_text": "Reap created successfully."
            }
        else:
            result = {
                "decision": "UNKNOWN_POLICY",
                "confidence": 0.0,
                "risk_factors": [f"Unknown policy: {envelope.orchestration_policy}"],
                "appeal_text": None
            }
        
        return DecisionResponse(
            envelope_id=envelope.id,
            **result
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/process-batch")
async def process_batch(envelopes: List[Tier2Envelope]):
    """Process multiple envelopes in batch"""
    results = []
    for envelope in envelopes:
        try:
            result = await process_envelope(envelope)
            results.append(result)
        except Exception as e:
            results.append({
                "envelope_id": envelope.id,
                "decision": "ERROR",
                "confidence": 0.0,
                "risk_factors": [str(e)],
                "appeal_text": None
            })
    return {"results": results}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10001))
    uvicorn.run(app, host="0.0.0.0", port=port)
