from tier3.api import score_envelope, process_batch

# ----------------------------
# Helper to create a valid Tier-2 envelope
# ----------------------------
def make_valid_envelope(envelope_id: str, value: float) -> dict:
    return {
        "id": envelope_id,
        "value": value,
        "_version": "0.2.0",        # Must include for Tier-3 validation
        "_processed_by": "tier2",
        "behavior_type": "click",
        "intensity": 1.0,
        "duration": 5,
        "premium_indicator": False
    }

# ----------------------------
# Single envelope test
# ----------------------------
envelope = make_valid_envelope("test123", 10)
result = score_envelope(envelope)

assert result["envelope_id"] == "test123"
assert result["score"] == 10.0
assert result["status"] == "success"

# ----------------------------
# Batch processing test
# ----------------------------
batch = [
    make_valid_envelope("e1", 5),
    make_valid_envelope("e2", 20)
]

batch_results = process_batch(batch)

assert batch_results[0]["score"] == 5.0
assert batch_results[1]["score"] == 20.0

print("🎯 Tier-3 end-to-end test passed with auto-version and full validation!")
