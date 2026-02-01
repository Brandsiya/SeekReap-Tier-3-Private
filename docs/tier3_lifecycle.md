# Tier‑3 Lifecycle

This document describes the lifecycle of data through Tier‑3 and its output
contract for Tier‑4 consumers.

## 1️⃣ Input: Tier‑2 Envelope
- Validated by tier3.validators.validate_tier2_envelope
- Example keys: id, value

## 2️⃣ Processing
- Function: process_input(envelope)
- Normalizes envelope

## 3️⃣ Scoring
- Function: score_envelope(envelope)
- Returns Tier4Output TypedDict:
  envelope_id, score, metadata, status

## 4️⃣ Batch Processing
- Function: process_batch(envelopes)
- Processes multiple envelopes

## 5️⃣ Example Usage
```python
from tier3.api import score_envelope

envelope = {"id": "abc123", "value": 42}
tier4_result = score_envelope(envelope)
print(tier4_result)
