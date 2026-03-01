import os
import json
import asyncio
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

app = FastAPI()

class Envelope(BaseModel):
    id: str
    timestamp: float
    payload: Dict[str, Any]
    schema_version: str
    orchestration_policy: str
    signature: str
    metadata: Dict[str, Any]

# --- Database Logic ---
async def get_db_conn():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return await asyncpg.connect(DATABASE_URL)

async def update_job_status(job_id: int, status: str, result: dict = None):
    conn = await get_db_conn()
    try:
        if result:
            # Store result as JSONB string
            await conn.execute("""
                UPDATE job_queue 
                SET status = $1, result = $2, completed_at = NOW() 
                WHERE job_id = $3
            """, status, json.dumps(result), job_id)
        else:
            await conn.execute("""
                UPDATE job_queue 
                SET status = $1, started_at = NOW() 
                WHERE job_id = $2
            """, status, job_id)
    finally:
        await conn.close()

async def analyze_content(content_id, content_type, params):
    # Simulated analysis engine
    await asyncio.sleep(0.5) 
    return {
        "overall_risk_score": 25,
        "risk_level": "Low",
        "content_id": content_id,
        "policy_matches": [],
        "recommended_actions": ["Monitor content for 24 hours"]
    }

# --- Main Endpoint ---
@app.post("/process-envelope")
async def process_envelope(request: Request, envelope: Envelope):
    print(f"📦 Processing Envelope: {envelope.id}")
    
    payload = envelope.payload
    job_id = payload.get("job_id")
    
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id")

    try:
        # 1. Update DB to Processing
        await update_job_status(job_id, "processing")

        # 2. Run Analysis
        content_url = payload.get("params", {}).get("url", "unknown")
        analysis = await analyze_content(content_url, "url", {})

        # 3. Save Result to JSONB column and mark Completed
        await update_job_status(job_id, "completed", analysis)
        
        return {
            "job_id": job_id,
            "decision": analysis["risk_level"],
            "risk_score": analysis["overall_risk_score"],
            "details": analysis
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        try:
            await update_job_status(job_id, "failed", {"error": str(e)})
        except: pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job/{job_id}")
async def get_job(job_id: int):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM job_queue WHERE job_id = $1", job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert record to dict, parsing 'result' JSONB back to dict
        data = dict(row)
        if data.get('result'):
            data['result'] = json.loads(data['result'])
        return data
    finally:
        await conn.close()

@app.get("/health")
async def health_check():
    try:
        # Quick DB check
        conn = await get_db_conn()
        await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
    finally:
        if 'conn' in locals():
            await conn.close()
