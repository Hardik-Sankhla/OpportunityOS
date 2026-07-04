# ADR_003: Set Novelty Score to Fixed Value of 10

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Scoring
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

The scoring formula assigns a novelty sub-score to every opportunity that passes
deduplication. Since deduplication is enforced before scoring (only new URLs enter
the pipeline), every scored item is technically novel. The original proposal set
novelty to 20, treating it as a meaningful differentiator. The CTO identified this
as a flaw: a fixed 20 is free points for everything equally, blunting the
differentiation provided by recency and popularity.

The formula is:
```
score = min(100, recency(0-30) + popularity(0-30) + novelty + relevance(0-20)
```

## Decision

Set `novelty` to a fixed value of **10** for all records. It is not a variable.
It does not change based on item properties. It is a baseline floor that ensures
every new item starts with a minimum presence in the score space, without
overshadowing the signals that actually differentiate items (recency and popularity).

The value 10 was chosen because:
1. It is small enough that recency (30) and popularity (30) remain the dominant signals
2. It is large enough to ensure items with zero popularity signals (Arxiv papers)
   can still reach the digest eligibility threshold (40) if they have strong recency and relevance

**Future path:** After 30+ days of feedback history, novelty may be replaced by:
```
novelty = 10 + trend_bonus
```
where `trend_bonus` is derived from feedback signal patterns for similar tags.
This requires a superseding ADR and supporting experiment log entries.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Novelty = 20 (original proposal) | Free points for everything equally. Inflates all scores uniformly, making the formula less discriminating. CTO rejected this explicitly. |
| Novelty = 0 (remove entirely) | Arxiv papers with no engagement signals would score 0 on popularity, making them permanently ineligible. The quota system needs them to be reachable. |
| Variable novelty based on age (e.g., decreases over 48h) | Redundant — recency already handles time decay. Adding time-based novelty creates a double-penalty for older items. |
| LLM-based novelty (semantic uniqueness score) | Explicitly banned. Adds cost, latency, inconsistency. Deterministic scoring is the project's core principle. |

## Consequences

**Positive:**
- Max score for a tool/hackathon: 90 (30+30+10+20) — intentionally below 100 to preserve headroom
- Max score for an actionable paper: 80 (30+30+10+20-10 penalty = 80)
- Max score for a pure theory paper: 50 (30+0+10+20-10 = 50 at best)
- Score distribution creates clear separation between types without manual thresholds

**Negative / Trade-offs:**
- All items get the same novelty score regardless of how novel they actually are
- The "trend_bonus" future path requires a new ADR before implementation

**Neutral changes:**
- Database constraint enforces: `CHECK (score_novelty IS NULL OR score_novelty = 10)`
- Any future change to novelty = 10 requires: (1) this ADR superseded, (2) DB migration, (3) experiment log entry

## Rollback Plan

**Trigger condition:** Experiment log (EXP_001 or later) demonstrates that novelty = 10
produces worse digest quality than an alternative value, supported by ≥14 days of data.
**Rollback steps:**
1. Write superseding ADR with new value and evidence
2. Update `scorer/score.py` (one constant change)
3. Write migration to update historical `score_novelty` values (or leave historical as-is)
4. Update DB CHECK constraint via migration
**Estimated rollback time:** 2 hours including migration
**Irreversible aspects:** Historical scores in the `opportunities` table will reflect the old value. This is acceptable — scores are not used for trend analysis in MVP.

## References

- `01_SPECS/approved/SCHEMA_SPEC.md`, Appendix A (Revised Scoring Formula)
- `01_SPECS/approved/MVP_SPEC.md`, Section 7 (Opportunity Scoring Formula)
