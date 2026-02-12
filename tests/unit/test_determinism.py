from tier3.api import score_envelope

def test_deterministic_output():
    envelope = {
        "content": "deterministic test",
        "metadata": {},
        "context": {}
    }

    result1 = score_envelope(envelope)
    result2 = score_envelope(envelope)
