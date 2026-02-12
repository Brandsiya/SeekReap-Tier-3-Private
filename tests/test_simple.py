import pytest
from tier3.api import score_envelope
from tier3 import validators

def test_score_envelope_basic():
    envelope = {
        "content": "Hello world",
        "metadata": {"author": "tester", "timestamp": "2026-02-12T00:00:00Z"},
        "context": {"source": "unit_test", "version": 1}
    }
    result = score_envelope(envelope)
    assert isinstance(result, dict)
    assert "score" in result

def test_validate_envelope_accepts_correct_type():
    envelope = {
        "content": "Valid string",
        "metadata": {"author": "tester", "timestamp": "2026-02-12T00:00:00Z"},
        "context": {"source": "unit_test", "version": 1}
    }
    validators.validate_envelope(envelope)  # should not raise
