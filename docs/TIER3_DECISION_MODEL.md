# Tier-3 Decision & Valuation Model

---

## 1. Inputs

Primary drivers:
- behavior_type
- intensity
- duration
- premium_indicator

---

## 2. Scoring Logic

Monetization score is derived from:
- Engagement intensity
- Sustained behavior
- Premium signals

Scores are normalized to **0.0 – 1.0**.

---

## 3. Tier Mapping

| Score Range | Tier |
|----|----|
| < 0.3 | FREE |
| 0.3 – 0.6 | STANDARD |
| 0.6 – 0.85 | PREMIUM |
| > 0.85 | PREMIUM_PLUS |

---

## 4. Determinism

No randomness  
No time-based mutation  
No adaptive learning in Tier-3

