"""
SeekReap Tier-3 - Analysis Service
Perceptual fingerprinting and similarity detection
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import hashlib
from typing import Dict, Any, List, Optional

# Import fingerprint engine
from fingerprint_engine import (
    generate_fingerprint,
    find_similar_submissions,
    compare_fingerprints
)

# Create FastAPI app
app = FastAPI(title="SeekReap Tier-3", description="Content Analysis Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection (optional - for similarity search)
def get_db():
    import psycopg2
    import psycopg2.extras
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return None
    return psycopg2.connect(db_url)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "tier-3", "version": "2.0"}


@app.post("/api/fingerprint")
async def generate_content_fingerprint(request: Request):
    """Generate perceptual fingerprint for content"""
    try:
        data = await request.json()
        content_type = data.get("content_type", "text")
        content_path = data.get("content_path")
        content_text = data.get("content_text")
        content_hash = data.get("content_hash")
        
        fingerprint = generate_fingerprint(content_type, content_path, content_text)
        
        return {
            "status": "success",
            "fingerprint": fingerprint
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/similarity/search")
async def search_similar(request: Request):
    """Search for similar submissions"""
    try:
        data = await request.json()
        fingerprint = data.get("fingerprint")
        threshold = data.get("threshold", 0.85)
        limit = data.get("limit", 50)
        
        conn = get_db()
        if not conn:
            return {
                "status": "error",
                "message": "Database not configured",
                "matches": []
            }
        
        cur = conn.cursor()
        matches = find_similar_submissions(cur, fingerprint, threshold)
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "matches": matches[:limit],
            "threshold": threshold,
            "total": len(matches)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_content(request: Request):
    """Legacy analyze endpoint - maintained for Tier-5 compatibility"""
    try:
        data = await request.json()
        
        # Extract values with defaults
        submission_id = data.get("submission_id", "unknown")
        content_type = data.get("content_type", data.get("contentType", "audio"))
        contentdata = data.get("contentdata", {})
        
        # Calculate risk score from provided data
        audio_sim = contentdata.get("audio_similarity", 0.0)
        visual_sim = contentdata.get("visual_similarity", 0.0)
        duplicate = contentdata.get("duplicate_content", False)
        
        risk_score = max(audio_sim, visual_sim)
        if duplicate:
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
            "status": "analyzed",
            "submission_id": submission_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "overall_risk_score": risk_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
