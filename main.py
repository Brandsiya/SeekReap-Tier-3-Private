import os
import json
import asyncio
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

# Simplified to match Tier-4's actual output
class Envelope(BaseModel):
    id: str
    payload: Dict[str, Any]
    # Make other fields optional so it doesn't crash if they are missing
    timestamp: Optional[float] = None
    schema_version: Optional[str] = None
    signature: Optional[str] = None

async def get_db_conn():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

@app.post("/process-envelope")
async def process_envelope(request: Request, envelope: Envelope):
    print(f"📦 Received Envelope: {envelope.id}")
    payload = envelope.payload
    
    # Tier-4 sends the URL inside 'params'
    content_url = payload.get("params", {}).get("url", "unknown")
    
    conn = await get_db_conn()
    try:
        # INSERT and get the REAL SERIAL ID
        real_job_id = await conn.fetchval("""
            INSERT INTO job_queue (status, url, created_at) 
            VALUES ('processing', $1, NOW()) 
            RETURNING job_id
        """, content_url)

        # Simulated Analysis
        analysis = {
            "overall_risk_score": 25,
            "risk_level": "Low",
            "content_id": content_url
        }

        await conn.execute("""
            UPDATE job_queue 
            SET status = 'completed', result = $1, completed_at = NOW() 
            WHERE job_id = $2
        """, json.dumps(analysis), real_job_id)

        return {
            "job_id": real_job_id,
            "decision": analysis["risk_level"],
            "details": analysis
        }
    except Exception as e:
        print(f"❌ Tier-3 Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/job/{job_id}")
async def get_job(job_id: int):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM job_queue WHERE job_id = $1", row_id)
        return dict(row) if row else {"error": "not found"}
    finally:
        await conn.close()