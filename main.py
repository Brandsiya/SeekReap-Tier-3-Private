#!/usr/bin/env python3
"""
SeekReap Tier-3 Decision Engine
Enhanced with real policy checking and database integration
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import uvicorn
import asyncpg
import json
import re
from enum import Enum

# =====================================================
# Configuration
# =====================================================
app = FastAPI(title="SeekReap Tier-3 Decision Engine")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
TIER4_URL = os.getenv("TIER4_URL", "https://seekreap-tier-4-orchestrator-nrn4.onrender.com")
PORT = int(os.getenv("PORT", 10001))

# Database connection pool
db_pool = None

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
    metadata: Dict[str, Any]

class PolicyCategory(str, Enum):
    SPAM = "spam_deceptive_scams"
    SENSITIVE = "sensitive_content"
    VIOLENT = "violent_extremist"
    HARMFUL = "harmful_dangerous"
    MISINFO = "misinformation"
    COPYRIGHT = "copyright"
    PRIVACY = "privacy"
    CHILD_SAFETY = "child_safety"
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment_cyberbullying"
    ADVERTISER = "advertiser_friendly"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Recommendation(str, Enum):
    PROCEED = "proceed"
    CAUTION = "caution"
    EDIT_REQUIRED = "edit_required"
    DO_NOT_UPLOAD = "do_not_upload"

class SegmentType(str, Enum):
    TIMESTAMP = "timestamp"
    THUMBNAIL = "thumbnail_region"
    TITLE = "title"
    DESCRIPTION = "description"
    TAG = "tag"
    CARD = "card"

# =====================================================
# Database Connection
# =====================================================

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        print("✅ Database connected successfully")
        
        # Test the connection
        async with db_pool.acquire() as conn:
            await conn.execute("SELECT 1")
        print("✅ Database connection test passed")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        db_pool = None

@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

# =====================================================
# Policy Checking Functions
# =====================================================

async def check_hate_speech(text: str) -> tuple[float, List[Dict]]:
    """
    Check text for hate speech patterns
    Returns: (severity_score, list of triggered rules with segments)
    """
    severity = 0
    triggered_rules = []
    flagged_segments = []
    
    # Simple pattern matching for demonstration
    # In production, you'd use ML models or more sophisticated algorithms
    hate_patterns = {
        r'\b(hate|hater|haters?)\b': 30,
        r'\b(racial|racist|racism)\b': 50,
        r'\b(slur|offensive)\b': 40,
        r'\b(discriminat(e|ion|ory))\b': 45,
        r'\b(attack|targeting)\s+(group|minority|community)\b': 60,
    }
    
    if text:
        for pattern, weight in hate_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                severity += weight
                triggered_rules.append({
                    "rule": f"hate_speech_pattern_{pattern}",
                    "confidence": min(weight / 100, 0.95),
                    "matched_text": match.group()
                })
                
                # Add flagged segment for the matched text
                start_pos = max(0, match.start() - 20)
                end_pos = min(len(text), match.end() + 20)
                flagged_segments.append({
                    "segment_type": "description",
                    "text_excerpt": text[start_pos:end_pos],
                    "confidence": min(weight / 100, 0.95),
                    "suggested_edit": f"Remove or rephrase offensive language: '{match.group()}'"
                })
    
    return min(severity, 100), triggered_rules, flagged_segments

async def check_copyright(title: str, description: str) -> tuple[float, List[Dict], List[Dict]]:
    """
    Simple copyright check based on keywords
    In production, this would integrate with content ID systems
    """
    severity = 0
    triggered_rules = []
    flagged_segments = []
    
    copyright_patterns = {
        r'\b(copyright|(c)\b|©)\b': 20,
        r'\b(unauthorized|without permission)\b': 30,
        r'\b(plagiar(is|e|ism)|stolen)\b': 40,
        r'\b(third[-\s]party|not mine)\b': 25,
    }
    
    text = f"{title} {description}".lower()
    
    for pattern, weight in copyright_patterns.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            severity += weight
            triggered_rules.append({
                "rule": f"copyright_indicator_{pattern}",
                "confidence": min(weight / 50, 0.9),
                "matched_text": match.group()
            })
    
    return min(severity, 100), triggered_rules, flagged_segments

async def check_child_safety(title: str, description: str, tags: List[str]) -> tuple[float, List[Dict], List[Dict]]:
    """
    Check for child safety concerns
    """
    severity = 0
    triggered_rules = []
    flagged_segments = []
    
    unsafe_patterns = {
        r'\b(child|minor|kid|underage)\b.*\b(content|video|show)\b': 70,
        r'\b(age\s*restrict(ed|ion)?)\b': 30,
        r'\b(family[-\s]friendly|for\s+kids)\b': -20,  # Negative - actually good
    }
    
    text = f"{title} {description}".lower()
    
    for pattern, weight in unsafe_patterns.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            severity += weight
            if weight > 0:
                triggered_rules.append({
                    "rule": f"child_safety_{pattern}",
                    "confidence": min(abs(weight) / 100, 0.95),
                    "matched_text": match.group()
                })
    
    # Check tags for kid-related content
    if tags:
        kid_tags = ['kids', 'children', 'family', 'educational']
        if any(tag in kid_tags for tag in tags):
            severity -= 30  # Lower severity for kid-friendly tags
    
    return max(0, min(severity, 100)), triggered_rules, flagged_segments

async def check_advertiser_friendly(title: str, description: str) -> tuple[float, List[Dict], List[Dict]]:
    """
    Check if content is advertiser-friendly
    """
    severity = 0
    triggered_rules = []
    flagged_segments = []
    
    advertiser_unfriendly = {
        r'\b(controversial|offensive|graphic)\b': 40,
        r'\b(sexual|nudity|explicit)\b': 80,
        r'\b(violence|blood|gore)\b': 70,
        r'\b(profanity|swear|cuss)\b': 50,
        r'\b(drugs|alcohol|smoking)\b': 60,
    }
    
    text = f"{title} {description}".lower()
    
    for pattern, weight in advertiser_unfriendly.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            severity += weight
            triggered_rules.append({
                "rule": f"advertiser_unfriendly_{pattern}",
                "confidence": min(weight / 100, 0.9),
                "matched_text": match.group()
            })
    
    return min(severity, 100), triggered_rules, flagged_segments

def calculate_risk_level(severity: float) -> RiskLevel:
    """Convert severity score to risk level"""
    if severity >= 80:
        return RiskLevel.CRITICAL
    elif severity >= 60:
        return RiskLevel.HIGH
    elif severity >= 30:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW

def get_recommendation(severity: float, category: str) -> Recommendation:
    """Determine recommendation based on severity and category"""
    if severity >= 70:
        return Recommendation.DO_NOT_UPLOAD
    elif severity >= 50:
        return Recommendation.EDIT_REQUIRED
    elif severity >= 30:
        return Recommendation.CAUTION
    else:
        return Recommendation.PROCEED

# =====================================================
# Main Processing Function
# =====================================================

async def process_content_submission(submission_id: str, content_data: Dict):
    """
    Process a content submission through all policy checks
    """
    print(f"📊 Processing submission: {submission_id}")
    
    title = content_data.get("title", "")
    description = content_data.get("description", "")
    tags = content_data.get("tags", [])
    
    all_checks = []
    total_severity = 0
    check_count = 0
    
    # Run all policy checks
    checks = [
        ("hate_speech", await check_hate_speech(f"{title} {description}")),
        ("copyright", await check_copyright(title, description)),
        ("child_safety", await check_child_safety(title, description, tags)),
        ("advertiser_friendly", await check_advertiser_friendly(title, description)),
    ]
    
    async with db_pool.acquire() as conn:
        for category, (severity, rules, segments) in checks:
            check_count += 1
            total_severity += severity
            
            risk_level = calculate_risk_level(severity)
            recommendation = get_recommendation(severity, category)
            
            # Insert policy check
            check_id = await conn.fetchval("""
                INSERT INTO policy_checks (
                    submission_id, policy_category, severity_score,
                    risk_level, triggered_rules, recommendation
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                RETURNING check_id
            """, submission_id, category, severity, risk_level.value,
                json.dumps({"rules": rules}), recommendation.value)
            
            # Insert flagged segments
            for segment in segments:
                await conn.execute("""
                    INSERT INTO flagged_segments (
                        check_id, segment_type, text_excerpt,
                        confidence, suggested_edit
                    ) VALUES ($1, $2, $3, $4, $5)
                """, check_id, segment.get("segment_type", "description"),
                    segment.get("text_excerpt", ""),
                    segment.get("confidence", 0.5),
                    segment.get("suggested_edit", ""))
            
            all_checks.append({
                "category": category,
                "severity": severity,
                "risk_level": risk_level.value,
                "recommendation": recommendation.value,
                "rules": rules
            })
    
    # Calculate overall stats
    avg_severity = total_severity / max(check_count, 1)
    overall_risk = calculate_risk_level(avg_severity)
    
    # Determine monetization eligibility
    monetization_eligible = avg_severity < 40
    age_restriction_likely = avg_severity >= 50
    limited_views_likely = avg_severity >= 60
    
    # Determine final recommendation
    final_recommendation = get_recommendation(avg_severity, "overall")
    
    # Insert submission results
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO submission_results (
                submission_id, overall_risk, monetization_eligible,
                age_restriction_likely, limited_views_likely,
                final_recommendation, summary_notes, completed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        """, submission_id, overall_risk.value, monetization_eligible,
            age_restriction_likely, limited_views_likely,
            final_recommendation.value,
            f"Processed {check_count} policy checks")
        
        # Update submission status
        await conn.execute("""
            UPDATE content_submissions
            SET status = 'complete'
            WHERE submission_id = $1
        """, submission_id)
    
    print(f"✅ Submission {submission_id} processed. Overall risk: {overall_risk.value}")
    
    return {
        "submission_id": submission_id,
        "overall_risk": overall_risk.value,
        "monetization_eligible": monetization_eligible,
        "age_restriction_likely": age_restriction_likely,
        "limited_views_likely": limited_views_likely,
        "final_recommendation": final_recommendation.value,
        "policy_checks": all_checks
    }

# =====================================================
# API Endpoints
# =====================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "connected" if db_pool else "disconnected"
    return {
        "status": "healthy",
        "tier": 3,
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "Tier-3 Private Layer running",
        "version": "3.0.0",
        "features": [
            "Hate Speech Detection",
            "Copyright Checking",
            "Child Safety Analysis",
            "Advertiser-Friendly Scoring"
        ]
    }

@app.post("/process-envelope")
async def process_envelope(envelope: Envelope):
    """
    Process an envelope containing content for policy checking
    """
    print(f"\n📦 Processing envelope: {envelope.id}")
    print(f"   Policy: {envelope.orchestration_policy}")
    
    try:
        # Extract submission_id from payload if present
        submission_id = envelope.payload.get("submission_id")
        content_data = envelope.payload.get("content_data", {})
        
        if not submission_id:
            return {
                "decision": "ERROR",
                "confidence": 0,
                "risk_factors": ["No submission_id provided"],
                "appeal_text": None
            }
        
        # Process the submission
        result = await process_content_submission(submission_id, content_data)
        
        # Format response for Tier-4
        return {
            "decision": result["final_recommendation"].upper(),
            "confidence": 1 - (result.get("overall_risk_score", 50) / 100),
            "risk_factors": [
                f"{check['category']}: {check['risk_level']} ({check['severity']:.0f})"
                for check in result["policy_checks"][:3]  # Top 3 risk factors
            ],
            "appeal_text": None,
            "details": result
        }
        
    except Exception as e:
        print(f"❌ Error processing envelope: {e}")
        return {
            "decision": "ERROR",
            "confidence": 0,
            "risk_factors": [str(e)],
            "appeal_text": None
        }

@app.post("/api/process-submission")
async def api_process_submission(request: Request):
    """
    Direct API endpoint for processing submissions
    """
    try:
        data = await request.json()
        submission_id = data.get("submission_id")
        content_data = data.get("content_data", {})
        
        if not submission_id:
            raise HTTPException(status_code=400, detail="submission_id required")
        
        result = await process_content_submission(submission_id, content_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/policy-categories")
async def get_policy_categories():
    """Get list of all policy categories"""
    return {
        "categories": [category.value for category in PolicyCategory]
    }

# =====================================================
# Main
# =====================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

# Add after the process_content_submission function
@app.get("/debug/check-submission/{submission_id}")
async def debug_check_submission(submission_id: str):
    """Debug why a submission isn't getting policy checks"""
    try:
        # Check if submission exists
        submission = await pool.fetchrow(
            "SELECT * FROM content_submissions WHERE submission_id = $1",
            submission_id
        )
        
        if not submission:
            return {"error": "Submission not found"}
        
        # Check if there's a job for this submission
        job = await pool.fetchrow(
            "SELECT * FROM job_queue WHERE submission_id::text = $1",
            submission_id
        )
        
        # Try to manually trigger processing
        from datetime import datetime
        content_data = {
            "title": submission['title'],
            "description": submission['description'],
            "tags": submission['tags']
        }
        
        # This will attempt to create policy checks
        result = await process_content_submission(submission_id, content_data)
        
        return {
            "submission": dict(submission),
            "job": dict(job) if job else None,
            "processing_result": result,
            "message": "Manual processing attempted"
        }
    except Exception as e:
        return {"error": str(e)}

# Replace the debug endpoint with corrected version
@app.get("/debug/check-submission/{submission_id}")
async def debug_check_submission(submission_id: str):
    """Debug why a submission isn't getting policy checks"""
    try:
        # Check if submission exists - use db_pool, not pool!
        submission = await db_pool.fetchrow(
            "SELECT * FROM content_submissions WHERE submission_id = $1",
            submission_id
        )
        
        if not submission:
            return {"error": "Submission not found"}
        
        # Check if there's a job for this submission
        job = await db_pool.fetchrow(
            "SELECT * FROM job_queue WHERE submission_id::text = $1",
            submission_id
        )
        
        # Try to manually trigger processing
        content_data = {
            "title": submission['title'],
            "description": submission['description'],
            "tags": submission['tags']
        }
        
        # This will attempt to create policy checks
        result = await process_content_submission(submission_id, content_data)
        
        return {
            "submission": dict(submission),
            "job": dict(job) if job else None,
            "processing_result": result,
            "message": "Manual processing attempted",
            "db_pool_status": "connected"
        }
    except Exception as e:
        return {"error": str(e), "type": str(type(e).__name__)}
