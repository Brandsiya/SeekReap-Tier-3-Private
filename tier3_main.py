from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
import uuid
import json
import hashlib
import time

app = Flask(__name__)
CORS(app)

# Database connection
def get_db():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(db_url)

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.post("/test/insert-job")
def insert_test_job():
    try:
        conn = get_db()
        cur = conn.cursor()

        submission_id = str(uuid.uuid4())
        creator_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "test-creator-001"))

        unique_content = f"test_audio_{int(time.time())}.wav"
        content_id = hashlib.sha256(unique_content.encode()).hexdigest()

        params = json.dumps({
            "file_path": f"/tmp/{unique_content}",
            "filename": unique_content,
            "media_type": "audio"
        })

        unique_email = f"test-{creator_id[:8]}@example.com"

        cur.execute("""
            INSERT INTO creators (id, firebase_uid, email, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (id) DO NOTHING
        """, (creator_id, "test-firebase-uid-001", unique_email))

        cur.execute("""
            INSERT INTO submissions (id, creator_id, content_hash, content_type, status, submitted_at)
            VALUES (%s, %s, %s, 'audio', 'pending', NOW())
            ON CONFLICT (id) DO NOTHING
        """, (submission_id, creator_id, content_id))

        cur.execute("""
            INSERT INTO job_queue (submission_id, creator_id, content_id, job_type, params, status, attempts, created_at)
            VALUES (%s, %s, %s, 'file_processing', %s, 'pending', 0, NOW())
        """, (submission_id, creator_id, content_id, params))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "ok", "submission_id": submission_id, "content": unique_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Analyze endpoint (called by Tier-5 workers) ──
@app.post("/api/analyze")
def analyze():
    """Analyze content for risk assessment (called by Tier-5 workers)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Extract fields with safe defaults
        submission_id = data.get("submission_id")
        content_id = data.get("contentid") or data.get("content_id") or "unknown"
        content_hash = data.get("contenthash") or data.get("content_hash") or ""
        content_type = data.get("contenttype") or data.get("content_type") or "audio"
        
        # Extract contentdata safely
        contentdata = data.get("contentdata")
        if contentdata is None:
            contentdata = {}
        
        # Extract similarity scores with safe defaults
        audio_similarity = contentdata.get("audio_similarity")
        if audio_similarity is None:
            audio_similarity = contentdata.get("audiosimilarity", 0.0)
        try:
            audio_similarity = float(audio_similarity)
        except (TypeError, ValueError):
            audio_similarity = 0.0
            
        visual_similarity = contentdata.get("visual_similarity")
        if visual_similarity is None:
            visual_similarity = contentdata.get("visualsimilarity", 0.0)
        try:
            visual_similarity = float(visual_similarity)
        except (TypeError, ValueError):
            visual_similarity = 0.0
        
        duplicate_content = contentdata.get("duplicate_content", False)
        if duplicate_content is None:
            duplicate_content = False
        try:
            duplicate_content = bool(duplicate_content)
        except:
            duplicate_content = False
            
        flags = contentdata.get("flags", [])
        if flags is None:
            flags = []
        
        # Calculate overall risk score
        # High similarity = high risk
        max_similarity = max(audio_similarity, visual_similarity)
        
        # Base risk on similarity
        risk_score = max_similarity
        
        # Boost risk if duplicate content flagged
        if duplicate_content:
            risk_score = min(1.0, risk_score + 0.3)
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "critical"
        elif risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Store analysis results in database
        conn = get_db()
        cur = conn.cursor()
        
        # Update submission with analysis results
        cur.execute("""
            UPDATE submissions
            SET status = 'analyzed',
                overall_risk_score = %s,
                risk_level = %s,
                analysis_details = %s::jsonb,
                analyzed_at = NOW()
            WHERE id = %s::uuid
            RETURNING id
        """, (risk_score, risk_level, json.dumps({
            "audio_similarity": audio_similarity,
            "visual_similarity": visual_similarity,
            "duplicate_content": duplicate_content,
            "flags": flags
        }), submission_id))
        
        updated = cur.fetchone()
        
        if updated:
            # Update job queue
            cur.execute("""
                UPDATE job_queue
                SET status = 'completed',
                    completed_at = NOW()
                WHERE submission_id = %s::uuid
                AND job_type = 'risk_analysis'
            """, (submission_id,))
            
            conn.commit()
            
            # Call Tier-4 finalize endpoint
            try:
                import requests
                finalize_payload = {
                    "submission_id": submission_id,
                    "analysis": {
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "details": {
                            "audio_similarity": audio_similarity,
                            "visual_similarity": visual_similarity,
                            "duplicate_content": duplicate_content,
                            "flags": flags
                        }
                    }
                }
                
                tier4_url = os.environ.get('TIER4_URL', 'https://seekreap-tier-4-dev.fly.dev')
                response = requests.post(
                    f"{tier4_url}/api/finalize",
                    json=finalize_payload,
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"Warning: Failed to call Tier-4 finalize: {response.status_code}")
                    
            except Exception as e:
                print(f"Warning: Error calling Tier-4 finalize: {e}")
                # Don't fail the whole analysis if finalize call fails
                # The analysis is already stored in DB
            
            return jsonify({
                "status": "analyzed",
                "submission_id": submission_id,
                "risk_score": risk_score,
                "risk_level": risk_level
            })
        else:
            return jsonify({"error": "submission not found"}), 404
            
    except Exception as e:
        # Log the full error for debugging
        print(f"Error in analyze endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
