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
