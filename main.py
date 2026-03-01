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
    metadata: Optional[Dict[str, Any]] = None

async def get_db_conn():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    return await asyncpg.connect(DATABASE_URL)

async def update_job_status(job_id: int, status: str, result: dict = None):
    """Update job status - assumes job already exists"""
    conn = await get_db_conn()
    try:
        if result:
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

async def analyze_content(content_id: str, content_type: str, params: dict):
    """Simulated content analysis"""
    await asyncio.sleep(0.5)
    return {
        "overall_risk_score": 25,
        "risk_level": "Low",
        "content_id": content_id,
        "policy_matches": [],
        "recommended_actions": ["Monitor content for 24 hours"]
    }

@app.post("/process-envelope")
async def process_envelope(request: Request, envelope: Envelope):
    print(f"📦 Processing Envelope: {envelope.id}")
    
    payload = envelope.payload
    temp_job_id = payload.get("job_id")  # This is the timestamp from Tier-4
    
    if not temp_job_id:
        raise HTTPException(status_code=400, detail="Missing job_id")
    
    # Extract content info
    params = payload.get("params", {})
    content_url = params.get("url", "unknown")
    creator_id = params.get("creator_id", 1)
    
    conn = await get_db_conn()
    try:
        # STEP 1: Create the job record FIRST and get the REAL database ID
        real_job_id = await conn.fetchval("""
            INSERT INTO job_queue (
                status, 
                params, 
                job_type, 
                content_id,
                creator_id,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING job_id
        """, 
            "processing", 
            json.dumps({"url": content_url, "creator_id": creator_id}), 
            payload.get("job_type", "url"),
            content_url,
            creator_id
        )
        
        print(f"   ✅ Created job with real ID: {real_job_id} (temp ID was: {temp_job_id})")
        
        # STEP 2: Analyze the content
        analysis = await analyze_content(content_url, "url", {})
        
        # STEP 3: Update the job with results
        await conn.execute("""
            UPDATE job_queue 
            SET status = 'completed', 
                result = $1, 
                completed_at = NOW() 
            WHERE job_id = $2
        """, json.dumps(analysis), real_job_id)
        
        # STEP 4: Return the REAL database ID to Tier-4
        return {
            "job_id": real_job_id,  # This is what the frontend needs!
            "decision": analysis["risk_level"],
            "risk_score": analysis["overall_risk_score"],
            "details": analysis
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        # Try to mark as failed if we have a real_job_id
        if 'real_job_id' in locals():
            try:
                await conn.execute("""
                    UPDATE job_queue 
                    SET status = 'failed', 
                        failure_reason = $1 
                    WHERE job_id = $2
                """, str(e), real_job_id)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

@app.get("/api/job/{job_id}")
async def get_job(job_id: int):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM job_queue WHERE job_id = $1", job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        
        data = dict(row)
        if data.get('result'):
            data['result'] = json.loads(data['result'])
        if data.get('params'):
            data['params'] = json.loads(data['params'])
        return data
    finally:
        await conn.close()

@app.get("/health")
async def health_check():
    try:
        conn = await get_db_conn()
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
