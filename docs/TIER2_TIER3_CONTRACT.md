# Tier-2 → Tier-3 Contract Enforcement

## Status
Mandatory

## Direction
Tier-2 → Tier-3 (One-way authority)

---

## 1. Required Envelope Shape

Tier-3 SHALL ONLY accept envelopes matching:

```json
{
  "behavior_type": "string",
  "intensity": 0.0,
  "duration": 0,
  "premium_indicator": false,
  "_version": "x.y.z",
  "_processed_by": "tier2"
}
```
## 2. Envelope Version Enforcement

Tier-3 SHALL validate the `_version` field in the envelope:

- Must match the semantic version of Tier‑2 outputs, e.g., "1.0.0" or "1.2.3".
- If `_version` is missing or invalid, Tier-3 SHALL reject the envelope with an explicit error.

## 3. Processed-By Check

Tier-3 SHALL verify `_processed_by`:

- Must equal "tier2".
- Any other value, missing, or null SHALL result in envelope rejection.

## 4. Field Validation Rules

Each envelope field SHALL be validated as follows:

| Field               | Type      | Constraint                                                |
|--------------------|-----------|----------------------------------------------------------|
| `behavior_type`     | string    | Must be a non-empty string                                |
| `intensity`         | float     | Must be >= 0.0                                           |
| `duration`          | int       | Must be >= 0                                             |
| `premium_indicator` | bool      | True or False                                            |
| `_version`          | string    | Must follow semantic versioning pattern x.y.z           |
| `_processed_by`     | string    | Must equal "tier2"                                     |

Tier-3 SHALL raise an error if any field violates the rules.

## 5. Error Handling & Logging

- Tier-3 SHALL raise a `ValueError` or a custom `EnvelopeValidationError` when a violation occurs.
- Error messages SHALL clearly indicate which field failed and why.
- Optionally, Tier-3 SHALL log invalid envelopes for audit purposes.

## 6. Forward Compatibility

- Tier-3 SHALL ignore extra fields added by Tier‑2 in future versions.
- This ensures Tier‑3 remains compatible with newer Tier‑2 envelopes.

## 7. Mandatory Enforcement

- No envelope SHALL be processed by Tier‑3 if it fails any of the above rules.
- Tier-3 SHALL provide clear feedback to upstream systems about rejections.

---
