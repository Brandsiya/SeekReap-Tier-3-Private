# Tier-3 Versioning Policy

---

## 1. Semantic Versioning

Format: MAJOR.MINOR.PATCH

- PATCH: Internal fixes
- MINOR: Backward-compatible enhancements
- MAJOR: Contract-breaking changes

---

## 2. Compatibility Rules

Tier-3 MUST:
- Accept envelopes from previous MINOR versions
- Reject incompatible MAJOR inputs explicitly

---

## 3. Deprecation Policy

Deprecated fields:
- Must be documented
- Must remain supported for one MAJOR cycle

