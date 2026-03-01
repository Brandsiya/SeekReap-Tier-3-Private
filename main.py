import os
import json
import hashlib
import hmac
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncpg
from asyncpg import Pool
from dotenv import load_dotenv
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

# =====================================================
# Configuration
# =====================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# =====================================================
# Lifespan Manager
# =====================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Tier-3 Private Layer starting up...")
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    print("✅ Database connection pool created")
    
    yield
    
    # Shutdown
    print("🔄 Tier-3 shutting down, closing connections...")
    await app.state.pool.close()
    print("✅ Connections closed")

# =====================================================
# FastAPI App Initialization
# =====================================================
app = FastAPI(
    title="SeekReap Tier-3 Private Layer",
    description="Decision Engine for Content Moderation",
    version="3.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =====================================================
# Pydantic Models
# =====================================================
class Envelope(BaseModel):
    id: str
    timestamp: float
    payload: Dict[str, Any]
    schema_version: str
    orchestration_policy: str
    signature: str
    metadata: Optional[Dict[str, Any]] = None

class PolicyCheckRequest(BaseModel):
    content_id: str
    content_type: str
    content_data: Dict[str, Any]
    check_policies: List[str]

class PolicyCheckResponse(BaseModel):
    content_id: str
    results: Dict[str, Any]
    timestamp: float

class AppealIntelligenceRequest(BaseModel):
    content_id: str
    violation_type: str
    channel_history: Optional[Dict[str, Any]] = None

class AppealIntelligenceResponse(BaseModel):
    content_id: str
    likelihood_score: float
    defense_strength: str
    tone_guidance: str
    mitigation_arguments: List[Dict[str, Any]]

class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    failure_reason: Optional[str]

# =====================================================
# Database Helpers
# =====================================================
async def get_db() -> Pool:
    return app.state.pool

async def get_job_from_db(job_id: int, pool: Pool):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM job_queue WHERE job_id = $1",
            job_id
        )

async def update_job_status(job_id: int, status: str, result_data: Dict = None, pool: Pool = None):
    if pool is None:
        pool = app.state.pool
    
    async with pool.acquire() as conn:
        if status == "completed":
            await conn.execute(
                "UPDATE job_queue SET status = $1, completed_at = NOW(), result = $2 WHERE job_id = $3",
                status, json.dumps(result_data) if result_data else None, job_id
            )
        elif status == "failed":
            await conn.execute(
                "UPDATE job_queue SET status = $1, failure_reason = $2 WHERE job_id = $3",
                status, result_data.get("reason") if result_data else "Unknown error", job_id
            )
        else:
            await conn.execute(
                "UPDATE job_queue SET status = $1, started_at = NOW() WHERE job_id = $2",
                status, job_id
            )

# =====================================================
# Decision Engine Functions
# =====================================================
async def analyze_content(content_id: str, content_type: str, content_data: Dict) -> Dict:
    """
    Analyze content for policy violations
    This is where your actual ML models/policy checks would go
    """
    # Simulate processing time
    await asyncio.sleep(1)
    
    # Mock analysis results
    risk_score = 25  # Low risk example
    policy_matches = []
    
    if content_type == "video":
        # Check video-specific policies
        if "filename" in content_data:
            filename = content_data.get("filename", "").lower()
            if "xvideo" in filename or "porn" in filename:
                policy_matches.append({
                    "policy_id": "adult-content-001",
                    "match_confidence": 0.95,
                    "details": "Adult content detected in filename"
                })
                risk_score = 85
    
    elif content_type == "url":
        # Check URL-specific policies
        url = content_data.get("url", "").lower()
        if "youtube.com/shorts" in url:
            # Low risk for YouTube shorts
            risk_score = 15
    
    # Determine risk level
    if risk_score < 35:
        risk_level = "Low"
    elif risk_score < 70:
        risk_level = "Medium"
    else:
        risk_level = "High"
    
    return {
        "content_id": content_id,
        "overall_risk_score": risk_score,
        "risk_level": risk_level,
        "policy_matches": policy_matches,
        "recommended_actions": [
            "Monitor content for 24 hours",
            "No immediate action required"
        ] if risk_score < 70 else [
            "Flag for manual review",
            "Restrict monetization pending review"
        ]
    }

async def generate_appeal_intelligence(content_id: str, violation_type: str, channel_history: Dict = None) -> Dict:
    """
    Generate appeal intelligence for a content violation
    """
    # Simulate processing
    await asyncio.sleep(0.5)
    
    likelihood_score = 72
    defense_strength = "Medium"
    
    if violation_type == "adult-content":
        defense_strength = "Weak"
        likelihood_score = 35
    elif violation_type == "copyright":
        defense_strength = "Strong"
        likelihood_score = 85
    
    return {
        "content_id": content_id,
        "likelihood_score": likelihood_score,
        "defense_strength": defense_strength,
        "tone_guidance": "Professional and factual",
        "mitigation_arguments": [
            {
                "argument_text": "Content was misclassified by automated system",
                "supporting_evidence": ["Similar content was approved", "Context of content"]
            },
            {
                "argument_text": "We have taken steps to improve our content",
                "supporting_evidence": ["Channel history shows compliance"]
            }
        ]
    }

# =====================================================
# Health Check Endpoint
# =====================================================
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        pool = app.state.pool
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "tier": 3,
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "tier": 3,
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# =====================================================
# Root Endpoint
# =====================================================
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "SeekReap Tier-3 Private Layer",
        "version": "3.0.0",
        "description": "Decision Engine for Content Moderation",
        "features": [
            "Content Policy Checking",
            "Appeal Intelligence Generation",
            "Job Status Tracking"
        ]
    }

# =====================================================
# Job Status Endpoint
# =====================================================
@app.get("/api/job/{job_id}", response_model=JobStatusResponse)
@limiter.limit("100 per minute")
async def get_job_status(request: Request, job_id: int):
    """Get the status of a specific job"""
    pool = app.state.pool
    job = await get_job_from_db(job_id, pool)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        failure_reason=job["failure_reason"]
    )

# =====================================================
# Process Envelope Endpoint
# =====================================================
@app.post("/process-envelope")
@limiter.limit("50 per minute")
async def process_envelope(request: Request, envelope: Envelope):
    """Process an incoming envelope from Tier-2/Tier-4"""
    print(f"📦 Received envelope: {envelope.id}")
    
    try:
        # Extract job information from payload
        job_data = envelope.payload
        job_id = job_data.get("job_id")
        content_id = job_data.get("content_id")
        content_type = job_data.get("job_type", "video")
        params = job_data.get("params", {})
        
        if not job_id:
            raise HTTPException(status_code=400, detail="Missing job_id in payload")
        
        print(f"   Processing job {job_id}: {content_id} ({content_type})")
        
        # Update job status to processing
        await update_job_status(job_id, "processing")
        
        # Analyze content first
        analysis_result = await analyze_content(content_id, content_type, params)
        
        # Store result in database
        await update_job_status(job_id, "completed", analysis_result)
        
        print(f"   ✅ Job {job_id} completed. Risk score: {analysis_result['overall_risk_score']}")
        
        return {
            "job_id": job_id,
            "decision": analysis_result["risk_level"],
            "risk_score": analysis_result["overall_risk_score"],
            "details": analysis_result
        }
        
    except Exception as e:
        print(f"   ❌ Error processing envelope: {str(e)}")
        # Update job status to failed
        if 'job_id' in locals():
            await update_job_status(job_id, "failed", {"reason": str(e)})
        
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# API Process Submission Endpoint
# =====================================================
@app.post("/api/process-submission")
@limiter.limit("50 per minute")
async def api_process_submission(request: Request):
    """API endpoint to process a submission directly"""
    print("📝 Received API process submission request")
    
    try:
        body = await request.json()
        job_id = body.get("job_id")
        content_id = body.get("content_id")
        content_type = body.get("job_type", "video")
        params = body.get("params", {})
        
        if not job_id or not content_id:
            raise HTTPException(status_code=400, detail="Missing job_id or content_id")
        
        print(f"   Processing job {job_id}: {content_id} ({content_type})")
        
        # Update job status to processing
        await update_job_status(job_id, "processing")
        
        # Analyze content
        analysis_result = await analyze_content(content_id, content_type, params)
        
        # Store result in database
        await update_job_status(job_id, "completed", analysis_result)
        
        print(f"   ✅ Job {job_id} completed. Risk score: {analysis_result['overall_risk_score']}")
        
        return {
            "success": True,
            "job_id": job_id,
            "decision": analysis_result["risk_level"],
            "risk_score": analysis_result["overall_risk_score"],
            "analysis": analysis_result
        }
        
    except Exception as e:
        print(f"   ❌ Error processing submission: {str(e)}")
        if 'job_id' in locals():
            await update_job_status(job_id, "failed", {"reason": str(e)})
        
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# Policy Check Endpoint
# =====================================================
@app.post("/api/policy-check", response_model=PolicyCheckResponse)
@limiter.limit("50 per minute")
async def policy_check(request: Request, check_request: PolicyCheckRequest):
    """Check content against specific policies"""
    print(f"🔍 Policy check requested for {check_request.content_id}")
    
    try:
        # Analyze content (reusing the analysis function)
        analysis_result = await analyze_content(
            check_request.content_id,
            check_request.content_type,
            check_request.content_data
        )
        
        # Filter results to requested policies if specified
        if check_request.check_policies and check_request.check_policies != ["all"]:
            filtered_matches = [
                match for match in analysis_result.get("policy_matches", [])
                if match["policy_id"] in check_request.check_policies
            ]
            analysis_result["policy_matches"] = filtered_matches
        
        return PolicyCheckResponse(
            content_id=check_request.content_id,
            results=analysis_result,
            timestamp=time.time()
        )
        
    except Exception as e:
        print(f"   ❌ Policy check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# Appeal Intelligence Endpoint
# =====================================================
@app.post("/api/appeal-intelligence", response_model=AppealIntelligenceResponse)
@limiter.limit("30 per minute")
async def appeal_intelligence(request: Request, appeal_request: AppealIntelligenceRequest):
    """Generate appeal intelligence for a content violation"""
    print(f"⚖️ Appeal intelligence requested for {appeal_request.content_id}")
    
    try:
        intelligence = await generate_appeal_intelligence(
            appeal_request.content_id,
            appeal_request.violation_type,
            appeal_request.channel_history
        )
        
        return AppealIntelligenceResponse(
            content_id=intelligence["content_id"],
            likelihood_score=intelligence["likelihood_score"],
            defense_strength=intelligence["defense_strength"],
            tone_guidance=intelligence["tone_guidance"],
            mitigation_arguments=intelligence["mitigation_arguments"]
        )
        
    except Exception as e:
        print(f"   ❌ Appeal intelligence generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# Batch Process Endpoint
# =====================================================
@app.post("/api/batch-process")
@limiter.limit("20 per minute")
async def batch_process(request: Request):
    """Process multiple jobs in batch"""
    print("📚 Batch process request received")
    
    try:
        body = await request.json()
        jobs = body.get("jobs", [])
        
        if not jobs:
            raise HTTPException(status_code=400, detail="No jobs provided")
        
        results = []
        for job in jobs:
            job_id = job.get("job_id")
            content_id = job.get("content_id")
            content_type = job.get("job_type", "video")
            params = job.get("params", {})
            
            if not job_id or not content_id:
                results.append({
                    "job_id": job_id,
                    "success": False,
                    "error": "Missing job_id or content_id"
                })
                continue
            
            try:
                # Analyze content
                analysis_result = await analyze_content(content_id, content_type, params)
                
                # Update job status
                await update_job_status(job_id, "completed", analysis_result)
                
                results.append({
                    "job_id": job_id,
                    "success": True,
                    "decision": analysis_result["risk_level"],
                    "risk_score": analysis_result["overall_risk_score"]
                })
                
            except Exception as e:
                results.append({
                    "job_id": job_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "batch_id": f"batch-{int(time.time())}",
            "total": len(jobs),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results
        }
        
    except Exception as e:
        print(f"   ❌ Batch processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# Database Status Endpoint
# =====================================================
@app.get("/api/db-status")
@limiter.limit("10 per minute")
async def db_status(request: Request):
    """Check database connection and stats"""
    try:
        pool = app.state.pool
        async with pool.acquire() as conn:
            # Get connection stats
            version = await conn.fetchval("SELECT version()")
            job_count = await conn.fetchval("SELECT COUNT(*) FROM job_queue")
            pending_count = await conn.fetchval("SELECT COUNT(*) FROM job_queue WHERE status = 'pending'")
            completed_count = await conn.fetchval("SELECT COUNT(*) FROM job_queue WHERE status = 'completed'")
            failed_count = await conn.fetchval("SELECT COUNT(*) FROM job_queue WHERE status = 'failed'")
        
        return {
            "status": "connected",
            "database": "PostgreSQL",
            "version": version.split()[0] if version else "unknown",
            "stats": {
                "total_jobs": job_count,
                "pending": pending_count,
                "completed": completed_count,
                "failed": failed_count
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "disconnected",
                "error": str(e)
            }
        )

# =====================================================
# Run the application (for development)
# =====================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

# Add debug endpoint to test analyze_content directly
@app.post("/debug/test-analyze")
async def debug_analyze(request: Request):
    """Test the analyze_content function directly"""
    try:
        body = await request.json()
        content_id = body.get("content_id", "test-123")
        content_type = body.get("content_type", "video")
        params = body.get("params", {})
        
        print(f"🔍 Debug: Calling analyze_content with: content_id={content_id}, content_type={content_type}")
        print(f"🔍 Debug: params={params}")
        
        result = await analyze_content(content_id, content_type, params)
        
        print(f"🔍 Debug: analyze_content returned: {result}")
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        print(f"🔍 Debug: analyze_content error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }, 500

# Also add better error handling in process_envelope
# Let's modify the existing process_envelope function to catch and log errors better

# Improved process_envelope with better error handling
@app.post("/process-envelope-v2")
@limiter.limit("50 per minute")
async def process_envelope_v2(request: Request, envelope: Envelope):
    """Process an incoming envelope with better error handling"""
    print(f"📦 Received envelope: {envelope.id}")
    
    try:
        # Extract data from envelope
        payload = envelope.payload
        job_id = payload.get("job_id")
        content_id = payload.get("content_id", f"content-{job_id}")
        content_type = payload.get("job_type", "video")
        params = payload.get("params", {})
        
        if not job_id:
            raise HTTPException(status_code=400, detail="Missing job_id in payload")
        
        print(f"   Processing job {job_id}: {content_id} ({content_type})")
        
        # Update job status to processing
        await update_job_status(job_id, "processing")
        
        # Analyze content with try/catch
        try:
            print(f"   Calling analyze_content...")
            analysis_result = await analyze_content(content_id, content_type, params)
            print(f"   analyze_content succeeded: {analysis_result}")
        except Exception as e:
            print(f"   ❌ analyze_content failed: {str(e)}")
            import traceback
            traceback.print_exc()
            await update_job_status(job_id, "failed", {"reason": str(e)})
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
        # Store result in database
        await update_job_status(job_id, "completed", analysis_result)
        
        print(f"   ✅ Job {job_id} completed. Risk score: {analysis_result['overall_risk_score']}")
        
        return {
            "job_id": job_id,
            "decision": analysis_result["risk_level"],
            "risk_score": analysis_result["overall_risk_score"],
            "details": analysis_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
