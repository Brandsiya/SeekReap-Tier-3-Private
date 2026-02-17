import json
import requests
from sqlalchemy import create_engine, text
import os

# -----------------------------
# 1. Configure DB & Tier-3 URL
# -----------------------------
# Replace with your Neon database credentials
DATABASE_URL = "postgresql+psycopg2://neondb_owner:npg_vX1ntyHVQN6x@ep-rapid-base-ai27r1sa-pooler.c-4.us-east-1.aws.neon.tech:5432/seekreap_neon_db?sslmode=require"

# Tier-3 verification URL (local)
TIER3_URL = "https://seekreap-tier-3-private.onrender.com/verify"

# Create SQLAlchemy engine for Neon
engine = create_engine(DATABASE_URL)


# -----------------------------
# 2. Fetch unverified content
# -----------------------------
def fetch_unverified_snapshots(limit=10):
    """Fetch snapshots that have not been verified yet."""
    query = text("""
        SELECT id, raw_data
        FROM analytics_snapshots
        WHERE verified_score IS NULL
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"limit": limit}).fetchall()
        return [dict(row._mapping) for row in rows]


# -----------------------------
# 3. Send to Tier-3 (which forwards to Tier-4)
# -----------------------------
def send_to_tier3(snapshot_id, content):
    """Send a piece of content to Tier-3 and get combined results from Tier-3 and Tier-4."""
    payload = {
        "content": content,
        "quality_score": 0.8,
        "risk_score": 0.2
    }
    try:
        response = requests.post(TIER3_URL, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Tier-3 request failed for {snapshot_id}: {e}")
        return {"tier3_score": None, "tier4_response": None}


# -----------------------------
# 4. Update database with results
# -----------------------------
def update_snapshot(snapshot_id, tier3_score, tier4_response):
    """Update the snapshot in the DB with Tier-3 score and Tier-4 response."""
    query = text("""
        UPDATE analytics_snapshots
        SET verified_score = :score,
            raw_data = raw_data || :tier4
        WHERE id = :sid
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "score": tier3_score.get("score") if tier3_score else None,
            "tier4": json.dumps({"tier4_response": tier4_response}),
            "sid": snapshot_id
        })

def main():
    """Update the snapshot in the DB with Tier-3 score and Tier-4 response."""
    query = text("""
        UPDATE analytics_snapshots
        SET verified_score = :score,
            raw_data = raw_data || :tier4
        WHERE id = :sid
    """)
    with engine.connect() as conn:
        conn.execute(query, {
            "score": tier3_score.get("score") if tier3_score else None,
            "tier4": json.dumps({"tier4_response": tier4_response}),
            "sid": snapshot_id
        })


# -----------------------------
# 5. Main processing loop
# -----------------------------
def main():
    snapshots = fetch_unverified_snapshots(limit=50)
    results_log = []

    for snap in snapshots:
        content = snap['raw_data'].get('content', '')
        print(f"[INFO] Processing {snap['id']}...")
        
        result = send_to_tier3(snap['id'], content)
        
        update_snapshot(
            snap['id'],
            result.get('tier3_score'),
            result.get('tier4_response')
        )

        # Save results locally for logging/debugging
        results_log.append({
            "task_id": snap['id'],
            "content": content,
            "tier3_score": result.get('tier3_score'),
            "tier4_response": result.get('tier4_response')
        })

    # Save all results locally
    with open("tier3_tier4_results_db.json", "w") as f:
        json.dump(results_log, f, indent=2, default=str)

    print(f"[INFO] Processing complete. {len(results_log)} items processed.")


if __name__ == "__main__":
    main()
