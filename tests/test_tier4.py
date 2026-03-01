import requests

# Tier-4 URL (your new live URL)
TIER4_URL = "https://seekreap-tier-4-orchestrator-nrn4.onrender.com"

# Example endpoint on Tier-4 (adjust if your API path is different)
endpoint = f"{TIER4_URL}/v4/process"

# Example payload (match what Tier-4 expects)
payload = {
    "task_id": "test123",
    "pipeline": "demo_pipeline",
    "inputs": {"param": 42},
    "context": {"source": "tier3_test"}
}

try:
    response = requests.post(endpoint, json=payload, timeout=10)
    response.raise_for_status()
    print("Tier-4 Response:", response.json())
except requests.exceptions.RequestException as e:
    print("Error communicating with Tier-4:", e)
