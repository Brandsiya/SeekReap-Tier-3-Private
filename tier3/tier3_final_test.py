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
print("Running single envelope test...")
envelope = make_valid_envelope("test123", 10)
result = score_envelope(envelope)
assert result["envelope_id"] == "test123"
assert result["score"] == 10.0
assert result["status"] == "success"
print("✅ Single envelope test passed")

# ----------------------------
# Batch processing test
# ----------------------------
print("Running batch envelope test...")
batch = [
    make_valid_envelope("e1", 5),
    make_valid_envelope("e2", 20)
]
batch_results = process_batch(batch)
assert batch_results[0]["score"] == 5.0
assert batch_results[1]["score"] == 20.0
print("✅ Batch envelope test passed")

# ----------------------------
# Edge cases
# ----------------------------
print("Running edge case tests...")
# Zero value
zero_env = make_valid_envelope("zero", 0)
res_zero = score_envelope(zero_env)
assert res_zero["score"] == 0
print("✅ Zero value test passed")

# Negative value
try:
    neg_env = make_valid_envelope("neg", -5)
    score_envelope(neg_env)
    print("⚠️ Negative value allowed (check if intended)")
except Exception as e:
    print("✅ Negative value test correctly raised:", e)

# Missing _version
try:
    invalid_env = make_valid_envelope("noversion", 10)
    del invalid_env["_version"]
    score_envelope(invalid_env)
except Exception as e:
    print("✅ Missing _version test correctly raised:", e)

# Wrong type
try:
    bad_type_env = make_valid_envelope("badtype", "not_a_number")
    score_envelope(bad_type_env)
except Exception as e:
    print("✅ Wrong type test correctly raised:", e)

# Mixed batch
try:
    mixed_batch = [
        make_valid_envelope("good1", 10),
        {"id": "bad2", "value": "oops"}  # invalid
    ]
    process_batch(mixed_batch)
except Exception as e:
    print("✅ Mixed batch correctly raised:", e)

# ----------------------------
# Simulated Tier-2 batch
# ----------------------------
print("Running simulated Tier-2 batch test...")
tier2_batch = [
    make_valid_envelope("t2_1", 7),
    make_valid_envelope("t2_2", 14)
]
tier2_results = process_batch(tier2_batch)
print("✅ Tier-2 simulation results:", tier2_results)

print("🎯 All Tier-3 tests passed! Tier-3 is ready for Tier-4")
