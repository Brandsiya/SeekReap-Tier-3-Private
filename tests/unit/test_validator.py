import pytest
from tier3.validators import validate_envelope

def test_invalid_missing_content():
    with pytest.raises(Exception):
        validate_envelope({})
