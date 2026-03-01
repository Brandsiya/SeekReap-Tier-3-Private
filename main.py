import os
import json
import asyncio
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

class Envelope(BaseModel):
    id: str
    payload: Dict[str, Any]

async def get_db_conn():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

@app.post("/process-envelope")
async def process_envelope(request: Request, envelope: Envelope):
    payload = envelope.payload
    content_url = payload.get("params", {}).get("url", "unknown")
    
    conn = await get_db_conn()
    try:
        # 1. INSERT into DB first to get the REAL serial ID
        # We ignore the job_id sent by Tier-4 and create a fresh one
        real_job_id = await conn.fetchval("""
            INSERT INTO job_queue (status, url, created_at) 
            VALUES ('processing', $1, NOW()) 
            RETURNING job_id
        """, content_url)

        # 2. Run Analysis
        # Simulated analysis
        analysis = {
            "overall_risk_score": 25,
            "risk_level": "Low",
            "content_id": content_url,
            "recommended_actions": ["Monitor"]
        }

        # 3. Update with results
        await conn.execute("""
            UPDATE job_queue 
            SET status = 'completed', result = $1, completed_at = NOW() 
            WHERE job_id = $2
        """, json.dumps(analysis), real_job_id)

        return {
            "job_id": real_job_id,  # Return the REAL DB ID (e.g. 115)
            "decision": analysis["risk_level"],
            "details": analysis
        }
    finally:
        await conn.close()

@app.get("/api/job/{job_id}")
async def get_job(job_id: int):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM job_queue WHERE job_id = $1", job_id)
        if not row: return {"error": "Job not found in DB"}
        data = dict(row)
        if data.get('result'): data['result'] = json.loads(data['result'])
        return data
    finally:
        await conn.close()