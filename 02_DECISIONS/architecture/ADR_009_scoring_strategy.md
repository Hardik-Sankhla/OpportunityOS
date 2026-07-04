# ADR 009: Deterministic Scoring Strategy

## Status
✅ Accepted (2026-07-04)

## Context
For Step 8, OpportunityOS requires a scoring engine to rank opportunities fetched by the Data Acquisition Layer. A common pitfall in agent-based systems is jumping immediately to AI-based semantic scoring (LLM evals, embeddings, vector search). While powerful, AI scoring at this stage is expensive, non-deterministic, slow, and hard to debug. For the MVP, we need a fully explainable, cheap, and auditable scoring formula based purely on metadata.

## Decision
We will implement a **Deterministic Scoring Engine** in `scheduler/scorer/score.py` with the following strict rules:

### 1. Allowed Inputs
The scoring engine may ONLY use fields that are natively populated on the `OpportunityRecord`. 
Allowed fields: `published_at`, `engagement_stars`, `engagement_likes`, `engagement_forks`, `engagement_watchers`, `engagement_participants`, `opportunity_type`, `actionability_tier`, `tags`, `title`, `summary`.

### 2. Forbidden Inputs & Technologies
The following are **strictly forbidden** in v1:
- LLM outputs / prompts
- Embeddings / Semantic similarity
- Vector search (e.g., Pinecone, Qdrant)
- External API calls for enrichment
- Feedback signals (until post-MVP)

### 3. The Deterministic Formula
The final score must be calculated exactly as:
`Score = Recency (0-30) + Popularity (0-30) + Novelty (10) + Relevance (0-20) + Penalty (0 or -10)`

- **Recency**: Based on `published_at`. Newer items score higher.
- **Popularity**: Based on `engagement_*` fields. Normalized log-scale to fit 0-30.
- **Novelty**: Fixed at 10 (per ADR 003).
- **Relevance**: Basic keyword matching on `tags`, `title`, and `summary` against a predefined set of high-value builder keywords (e.g., "llm", "agent", "rust", "open-source").
- **Penalty**: Negative points for low-quality signals (e.g., missing description, keyword spam).

### 4. Explainability
For every opportunity, the scorer must return a breakdown of the score:
```json
{
  "score": 72,
  "score_recency": 28,
  "score_popularity": 20,
  "score_novelty": 10,
  "score_relevance": 14,
  "penalty": 0
}
```

### 5. Delivery Constraints
- **Digest Floor**: Only opportunities with `score >= 40` are eligible for delivery.
- **Tie Breaker**: In the event of a tie, rank by: `Score (Desc) -> published_at (Desc) -> id (Asc)`. This guarantees stability.

## Consequences
- **Positive**: Blazing fast, 0 API costs, 100% deterministic, easy to unit test.
- **Negative**: Keyword relevance can be "gamed" and lacks true semantic understanding (Risk R10). We will mitigate this through careful keyword selection and weighting, eventually upgrading to AI scoring post-MVP when a feedback moat exists.
