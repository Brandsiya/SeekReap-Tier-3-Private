import pytest
from tier3.validators import validate_envelope


def valid_envelope():
    return {
        "content": "Valid content",
        "metadata": {
            "author": "tester",
            "timestamp": "2026-02-12T00:00:00Z"
        },
        "context": {
            "source": "unit_test",
            "version": 1
        }
    }


def test_valid_envelope():
    validate_envelope(valid_envelope())  # should not raise


def test_missing_content():
    envelope = valid_envelope()
    del envelope["content"]
    with pytest.raises(ValueError):
        validate_envelope(envelope)


def test_invalid_content_type():
    envelope = valid_envelope()
    envelope["content"] = 123
    with pytest.raises(TypeError):
        validate_envelope(envelope)


def test_missing_metadata():
    envelope = valid_envelope()
    del envelope["metadata"]
    with pytest.raises(ValueError):
        validate_envelope(envelope)


def test_missing_context():
    envelope = valid_envelope()
    del envelope["context"]
    with pytest.raises(ValueError):
        validate_envelope(envelope)

def test_envelope_must_be_dict():
    with pytest.raises(TypeError):
        validate_envelope("not a dict")
