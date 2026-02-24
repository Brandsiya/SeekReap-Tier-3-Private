import requests
import json

# Test with a sample envelope (simulating what Tier-2 would send)
sample_envelope = {
    "id": "test-envelope-123",
    "timestamp": 1234567890.123,
    "payload": {
        "status": "verified",
        "score": 0.85,
        "behaviors": ["b1", "b2", "b3"]
    },
    "schema_version": "tier2-envelope-v1",
    "orchestration_policy": "reap_verification",
    "signature": "tier2-semantic-reap_verification-1234567890123-abc123",
    "metadata": {"source": "test"}
}

response = requests.post("http://localhost:10001/process-envelope", json=sample_envelope)
print("Response:", response.json())
