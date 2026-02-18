import os
import json
import requests
from datetime import datetime

# ------------------------------
# CONFIGURATION
# ------------------------------
TIER3_URL = "http://127.0.0.1:10001/verify"  # Tier-3 local endpoint
OUTPUT_FILE = "tier3_tier4_results.json"      # Where we save results

# ------------------------------
# SAMPLE PLATFORM CONTENT
# Replace this with your real content loader if needed
# Each dict needs: id, text, quality_score, risk_score
# ------------------------------
platform_content = [
    {"id": "post001", "text": "Example post 1", "quality": 0.9, "risk": 0.1},
    {"id": "post002", "text": "Example post 2", "quality": 0.7, "risk": 0.2},
    # Add more items here
]

# ------------------------------
# FUNCTION TO SEND CONTENT TO TIER-3
# ------------------------------
def send_to_tier3(task_id, content, quality, risk):
    payload = {
        "task_id": task_id,
        "task_type": "moderation",
        "inputs": {
            "content": content,
            "quality_score": quality,
            "risk_score": risk
        },
        "context": {}
    }
    try:
        response = requests.post(TIER3_URL, json=payload, timeout=15)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ------------------------------
# MAIN LOOP
# ------------------------------
results = []

for item in platform_content:
    print(f"Processing {item['id']}...")
    result = send_to_tier3(item["id"], item["text"], item["quality"], item["risk"])
    timestamp = datetime.utcnow().isoformat()
    results.append({
        "task_id": item["id"],
        "content": item["text"],
        "tier3_score": result.get("tier3_score"),
        "tier4_response": result.get("tier4_response"),
        "timestamp": timestamp
    })

# ------------------------------
# SAVE RESULTS
# ------------------------------
with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"Results saved to {OUTPUT_FILE}")
