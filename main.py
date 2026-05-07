"""
SeekReap Tier-3 - Analysis Service
Perceptual fingerprinting and similarity detection
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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

# Startup DB verification — fails fast on schema drift
def verify_database():
    import psycopg2
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("WARNING: DATABASE_URL not set, skipping DB verification")
        return
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        required_tables = [
            "public.content_registry",
            "public.content_matches",
            "public.submissions",
            "public.fingerprints",
        ]
        for table in required_tables:
            cur.execute(f"SELECT to_regclass('{table}')")
            result = cur.fetchone()[0]
            if result is None:
                raise Exception(f"Missing required table: {table}")

        # Verify critical indexes exist
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname IN (
                'idx_matches_source_content',
                'idx_matches_similarity',
                'idx_fingerprints_submission',
                'idx_registry_visual_phash'
            )
        """)
        found_indexes = {row[0] for row in cur.fetchall()}
        expected_indexes = {
            'idx_matches_source_content',
            'idx_matches_similarity',
            'idx_fingerprints_submission',
            'idx_registry_visual_phash'
        }
        missing_indexes = expected_indexes - found_indexes
        if missing_indexes:
            print(f"WARNING: Missing indexes: {missing_indexes}")

        # Verify extensions
        cur.execute("""
            SELECT extname FROM pg_extension
            WHERE extname IN ('pgcrypto', 'uuid-ossp')
        """)
        extensions = {row[0] for row in cur.fetchall()}
        print(f"Active extensions: {extensions}")

        cur.close()
        conn.close()
        print("DB verification passed: all required tables present")
    except Exception as e:
        print(f"DB verification failed: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_database()
    yield

# Create FastAPI app
app = FastAPI(
    title="SeekReap Tier-3",
    description="Content Analysis Service",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    import psycopg2
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return None
    return psycopg2.connect(db_url)


@app.get("/health")
def health():
    return {"status": "ok", "service": "tier-3", "version": "2.1"}


@app.post("/api/fingerprint")
async def generate_content_fingerprint(request: Request):
    """Generate perceptual fingerprint for content"""
    try:
        data = await request.json()
        content_type = data.get("content_type", "text")
        content_path = data.get("content_path")
        content_text = data.get("content_text")
        fingerprint = generate_fingerprint(content_type, content_path, content_text)
        return {"status": "success", "fingerprint": fingerprint}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/similarity/search")
async def search_similar(request: Request):
    """Search for similar submissions and materialize graph edges"""
    try:
        data = await request.json()
        fingerprint          = data.get("fingerprint")
        threshold            = data.get("threshold", 0.85)
        limit                = data.get("limit", 50)
        source_submission_id = data.get("submission_id")
        source_registry_id   = data.get("registry_id")

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

        edges_created = 0
        if source_submission_id and matches:
            edge_cur = conn.cursor()
            for match in matches:
                if match["submission_id"] == source_submission_id:
                    continue
                score = match["similarity_score"]
                if score >= 0.98:
                    severity = "critical"
                elif score >= 0.85:
                    severity = "high"
                elif score >= 0.70:
                    severity = "medium"
                else:
                    severity = "low"

                # Satisfy the registry_link_check constraint:
                # at least one of source_content_id / matched_content_id must be non-null
                src_reg  = source_registry_id
                mat_reg  = match.get("registry_id")
                # If both are None the constraint would reject — skip
                if not src_reg and not mat_reg:
                    continue

                try:
                    edge_cur.execute("""
                        INSERT INTO public.content_matches (
                            id, submission_id, matched_submission_id,
                            similarity_score, match_type, fingerprint_version,
                            detected_at, severity,
                            source_content_id, matched_content_id,
                            match_scope, match_source
                        ) VALUES (
                            gen_random_uuid(), %s, %s, %s,
                            'perceptual', 'phash-v1', NOW(),
                            %s, %s, %s, 'canonical', 'internal'
                        ) ON CONFLICT DO NOTHING
                    """, (
                        source_submission_id,
                        match["submission_id"],
                        score,
                        severity,
                        src_reg,
                        mat_reg
                    ))
                    edges_created += 1
                except Exception as edge_err:
                    print(f"Edge insert failed: {edge_err}")
                    conn.rollback()
                    continue

            conn.commit()
            edge_cur.close()

        conn.close()

        return {
            "status": "success",
            "matches": matches[:limit],
            "threshold": threshold,
            "total": len(matches),
            "edges_created": edges_created
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_content(request: Request):
    """Legacy analyze endpoint - maintained for Tier-5 compatibility"""
    try:
        data = await request.json()
        submission_id = data.get("submission_id", "unknown")
        content_type  = data.get("content_type", data.get("contentType", "audio"))
        contentdata   = data.get("contentdata", {})

        audio_sim  = contentdata.get("audio_similarity", 0.0)
        visual_sim = contentdata.get("visual_similarity", 0.0)
        duplicate  = contentdata.get("duplicate_content", False)

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
