# SeekReap Tier-3 Public API Contract

**Status:** Stable  
**Audience:** Tier-2 (Semantic Layer)  
**Visibility:** Public (within SeekReap architecture)

---

## 1. Purpose

Tier-3 is the **Monetization & Valuation Layer** of SeekReap.

Its responsibilities:
- Consume **semantic envelopes** produced by Tier-2
- Generate **business and monetization insights**
- Produce **deterministic valuation outputs**

Tier-3 explicitly does **not**:
- Track users
- Store raw identifiers
- Perform semantic interpretation (Tier-2 responsibility)

---

## 2. Ingress Contract (What Tier-2 May Send)

Tier-3 accepts a **decoded semantic envelope** as a Python dictionary
(or JSON-equivalent structure).

### 2.1 Required Fields

```json
{
  "behavior_type": "string",
  "intensity": 0.0,
  "duration": 0,
  "premium_indicator": false
}
