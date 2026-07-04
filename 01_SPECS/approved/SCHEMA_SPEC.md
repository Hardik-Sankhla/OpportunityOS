# OpportunityOS — Canonical Data Model Specification

> **Status:** ✅ APPROVED (CTO, 2026-07-04)
> **Scope:** Data architecture only. No database DDL. No Python code.
> **Principle:** Every source speaks a different dialect. The schema is the translator.

---

## Why This Document Exists First

Without a canonical schema, fetchers diverge independently:

```
github_fetcher.py   returns  → { "repo_name": ..., "star_count": ... }
arxiv_fetcher.py    returns  → { "title": ...,     "authors": ... }
devpost_fetcher.py  returns  → { "name": ...,       "prize": ... }
```

The pipeline then needs 4 different parsers downstream. Every new source
adds a new parser. The schema collapses this to one contract.

**One input contract. All sources must conform to it.**

---

## Definitions

Before the schema, define terms precisely:

| Term | Definition |
|------|-----------|
| **Opportunity** | Something a builder can act on: build with, compete in, apply for, or earn from |
| **Interesting Thing** | Information worth knowing but requiring no action (e.g., a paper proving a theorem) |
| **Source** | An external system that provides raw opportunity data |
| **Canonical Record** | A normalized representation conforming to the OpportunityRecord schema |
| **Signal** | A user action taken in response to an opportunity (saved, applied, won, etc.) |
| **Actionability** | The degree to which an opportunity requires or enables a specific human action |

> **CTO Note Applied:** Arxiv papers are "interesting" by default. They only become
> opportunities if they contain: code release, dataset, model weights, benchmark, or
> tool that builders can immediately use. This is captured in `opportunity_type` and
> `actionability_tier` below.

---

## 1. Canonical Opportunity Schema

### 1.1 OpportunityRecord

Every source must produce exactly this structure. No exceptions. No extra fields
passed downstream — extra source data goes into `raw_metadata`.

```json
{
  "id": "",
  "source": "",
  "opportunity_type": "",
  "actionability_tier": "",

  "title": "",
  "url": "",
  "canonical_url": "",
  "summary": "",

  "tags": [],
  "tech_stack": [],
  "domains": [],

  "published_at": "",
  "deadline_at": null,

  "engagement": {
    "stars": null,
    "likes": null,
    "forks": null,
    "watchers": null,
    "participants": null
  },

  "reward": {
    "type": null,
    "amount": null,
    "currency": null,
    "description": null
  },

  "score": null,
  "score_breakdown": {
    "recency": null,
    "popularity": null,
    "novelty": null,
    "relevance": null
  },

  "outcome": {
    "saved_count": 0,
    "wrong_count": 0,
    "building_count": 0,
    "applied_count": 0,
    "won_count": 0
  },

  "opportunity_strength": {
    "urgency": null,
    "difficulty": null,
    "monetization": null,
    "time_to_value": null
  },

  "url_hash": "",
  "raw_metadata": {}
}
```

### 1.2 Field-by-Field Specification

#### Identity Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID v4 | Yes | Generated at normalization time. Never from source. |
| `source` | enum | Yes | One of: `github`, `huggingface`, `arxiv`, `devpost`, `grants_gov`, `gitcoin`, `devfolio`, `mlcontests` |
| `opportunity_type` | enum | Yes | See Section 5 (Opportunity Types) |
| `actionability_tier` | enum | Yes | See Section 5.2 (Actionability Tiers) |
| `url_hash` | SHA-256 string | Yes | Hash of `canonical_url`. Primary deduplication key. |

#### Content Fields

| Field | Type | Required | Max Length | Description |
|-------|------|----------|-----------|-------------|
| `title` | string | Yes | 300 chars | Human-readable title. Normalized: stripped, no leading/trailing whitespace. |
| `url` | string | Yes | — | Original URL exactly as received from source. |
| `canonical_url` | string | Yes | — | Normalized URL: scheme lowercased, trailing slashes removed, tracking params stripped. Used for deduplication. |
| `summary` | string | No | 1000 chars | Short description. Extracted from source. Never LLM-generated in MVP. Truncated if longer. |

#### Classification Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tags` | string[] | No | Free-form keyword tags. Lowercase. Max 20 items. |
| `tech_stack` | string[] | No | Normalized tech names: `python`, `rust`, `pytorch`, `llm`, etc. Max 10. |
| `domains` | string[] | No | Domain categories: `ai`, `ml`, `web`, `infra`, `security`, `data`, `robotics`. Max 5. |

#### Time Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `published_at` | ISO 8601 UTC | Yes | When the opportunity was published. If source has no date, use fetch time and flag `date_inferred: true` in `raw_metadata`. |
| `deadline_at` | ISO 8601 UTC | No | Application or submission deadline. Null if not applicable. Critical for hackathons/grants. |

#### Engagement Fields

The `engagement` object captures source-specific popularity signals, normalized by name.
Fields not provided by the source are `null`, not `0`. This distinction matters for scoring.

| Sub-field | Sources That Provide It |
|-----------|------------------------|
| `stars` | GitHub |
| `likes` | HuggingFace, Devpost |
| `forks` | GitHub |
| `watchers` | GitHub |
| `participants` | Devpost (teams entered) |

#### Reward Fields

The `reward` object is null-safe. For non-monetary opportunities, all sub-fields are null.

| Sub-field | Type | Description |
|-----------|------|-------------|
| `type` | enum | `cash`, `equity`, `credits`, `swag`, `recognition`, `none` |
| `amount` | number | Numeric value. Null if unknown. |
| `currency` | string | ISO 4217 code. `USD` assumed if unlabeled. |
| `description` | string | Raw prize/reward text from source. Max 200 chars. |

#### Scoring Fields (populated by scorer, not fetcher)

| Field | Type | Set By | Description |
|-------|------|--------|-------------|
| `score` | integer 0–100 | Scorer | Final composite score |
| `score_breakdown.recency` | integer 0–30 | Scorer | See MVP_SPEC scoring formula |
| `score_breakdown.popularity` | integer 0–30 | Scorer | See MVP_SPEC scoring formula |
| `score_breakdown.novelty` | integer 0–10 | Scorer | **Fixed at 10** (CTO approved) |
| `score_breakdown.relevance` | integer 0–20 | Scorer | See MVP_SPEC scoring formula |

#### Outcome Fields (populated by feedback system)

Stored on the record for fast aggregation. Incremented by the feedback handler.
Do NOT query the `opportunity_feedback` table to display these — read directly from the record.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `outcome.saved_count` | integer | 0 | Number of `/save` signals received |
| `outcome.wrong_count` | integer | 0 | Number of `/wrong` signals received |
| `outcome.building_count` | integer | 0 | Reserved. 0 in MVP. |
| `outcome.applied_count` | integer | 0 | Reserved. 0 in MVP. |
| `outcome.won_count` | integer | 0 | Reserved. 0 in MVP. |

#### Opportunity Strength Fields (null in MVP — reserved for future learning system)

These fields answer a different question than `score`. Score answers: **"Is this notable?"**
Strength answers: **"Can I make money from this this month?"**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `opportunity_strength.urgency` | float or null | 0.0–1.0 | How time-sensitive is the deadline? |
| `opportunity_strength.difficulty` | float or null | 0.0–1.0 | How hard is it to participate/use? (inverse) |
| `opportunity_strength.monetization` | float or null | 0.0–1.0 | How directly does this produce income? |
| `opportunity_strength.time_to_value` | float or null | 0.0–1.0 | How quickly can a builder see ROI? |

**All four fields are null for all records in MVP.** Schema defined now so the column exists when the learning system is ready. No scoring logic uses these in MVP.

#### Raw Metadata

| Field | Type | Description |
|-------|------|-------------|
| `raw_metadata` | object | Source-specific fields that don't fit the canonical schema. Stored for debugging and future schema evolution. Never read by the pipeline logic. |

---

## 2. Source Mapping Tables

### 2.1 GitHub Trending

**Source API:** `GET /search/repositories?q=created:>YESTERDAY&sort=stars&order=desc`

| Canonical Field | GitHub API Field | Transformation |
|-----------------|-----------------|----------------|
| `source` | — | Hardcoded: `"github"` |
| `opportunity_type` | `topics`, `description` | Default `"tool"`. Override to `"dataset"` if topics contain `dataset`. |
| `actionability_tier` | — | Default `"use"` |
| `title` | `full_name` | Use as-is: `"owner/repo-name"` |
| `url` | `html_url` | Use as-is |
| `canonical_url` | `html_url` | Lowercase scheme, remove trailing slash |
| `summary` | `description` | Truncate to 1000 chars. Null if empty. |
| `tags` | `topics` | Use as-is array. Lowercase. |
| `tech_stack` | `language` | Single value → single-element array. Lowercase. |
| `domains` | `topics` | Map topics to domain vocabulary (see Section 3.3) |
| `published_at` | `created_at` | Parse ISO 8601. Already UTC. |
| `deadline_at` | — | Always null |
| `engagement.stars` | `stargazers_count` | Integer |
| `engagement.forks` | `forks_count` | Integer |
| `engagement.watchers` | `watchers_count` | Integer |
| `engagement.likes` | — | Always null |
| `engagement.participants` | — | Always null |
| `reward` | — | All null |
| `raw_metadata` | Entire API response object | Store full JSON |

**Missing fields:** GitHub does not provide `deadline_at`, `reward`, or `likes`. These are null, not errors.

---

### 2.2 HuggingFace Trending

**Source method:** HTML scrape of `huggingface.co/models?sort=trending` (top 20 cards)

| Canonical Field | HF HTML Element | Transformation |
|-----------------|----------------|----------------|
| `source` | — | Hardcoded: `"huggingface"` |
| `opportunity_type` | Card type (model vs. dataset) | `"tool"` for models, `"dataset"` for datasets |
| `actionability_tier` | — | `"use"` |
| `title` | Model card `<h4>` or `data-model-id` | `"owner/model-name"` format |
| `url` | `<a href>` on card | Prepend `https://huggingface.co` if relative |
| `canonical_url` | Same | Normalize |
| `summary` | Card description `<p>` | First sentence. Null if absent. |
| `tags` | Tag chips on card | Extract text. Lowercase. |
| `tech_stack` | Tags containing framework names | Filter tags for: `pytorch`, `tensorflow`, `jax`, `transformers` |
| `domains` | Task category label | Map task → domain (e.g., `text-generation` → `ai`) |
| `published_at` | "Updated X days ago" text | Parse relative time to absolute UTC. Flag `date_inferred: true`. |
| `deadline_at` | — | Always null |
| `engagement.likes` | Like count on card | Integer. Null if not visible. |
| `engagement.stars` | — | Always null |
| `reward` | — | All null |
| `raw_metadata` | Dict of all scraped fields | Store |

**Fragility note:** HuggingFace HTML structure is subject to change without notice.
Scraper must be isolated behind a try/except. Any CSS selector must be documented
in a single `SELECTORS` constant block for easy maintenance.

---

### 2.3 Arxiv

**Source API:** RSS feed — `https://export.arxiv.org/rss/cs.AI+cs.LG+cs.CL`

| Canonical Field | RSS/Atom Field | Transformation |
|-----------------|---------------|----------------|
| `source` | — | Hardcoded: `"arxiv"` |
| `opportunity_type` | `summary` content analysis | Default `"paper"`. Override to `"tool"` if summary mentions: "we release", "open source", "available at github", "code available". Override to `"dataset"` if mentions "dataset", "benchmark". |
| `actionability_tier` | Derived from `opportunity_type` | `"learn"` for paper. `"use"` for tool/dataset. |
| `title` | `<title>` | Strip trailing period. Remove newlines. |
| `url` | `<link>` | Use abstract URL: `arxiv.org/abs/XXXX.XXXXX` |
| `canonical_url` | `<link>` | Normalize. Strip `v1`, `v2` version suffixes for deduplication. |
| `summary` | `<summary>` | First 1000 chars of abstract. |
| `tags` | `<category>` | Subject codes: `cs.AI`, `cs.LG`, etc. |
| `tech_stack` | `<summary>` text | Keyword extract: `pytorch`, `jax`, `transformer`, etc. |
| `domains` | `<category>` | Map subject codes to domain vocab |
| `published_at` | `<published>` | Parse to UTC |
| `deadline_at` | — | Always null |
| `engagement` | — | All null (no engagement signals in RSS) |
| `reward` | — | All null |
| `raw_metadata` | Full RSS entry dict | Store |

**Opportunity type promotion logic** (determines if a paper is "interesting" vs "actionable"):

```
if any of ["we release", "open-source", "code at", "available at github",
           "open source", "our code is available"] in summary.lower():
    opportunity_type = "tool"
    actionability_tier = "use"

elif any of ["dataset", "benchmark", "we introduce X dataset"] in summary.lower():
    opportunity_type = "dataset"
    actionability_tier = "use"

else:
    opportunity_type = "paper"
    actionability_tier = "learn"
```

Papers with `actionability_tier = "learn"` receive a **-10 score penalty** applied after
the base scoring formula, because they are "interesting" not "actionable."

> **Quota override:** Even with a low score, one `paper` slot is always reserved in
> the daily digest. See Section 8 (Digest Quota System).

---

### 2.4 Devpost

**Source API:** RSS feed — `https://devpost.com/hackathons.rss`

| Canonical Field | RSS Field | Transformation |
|-----------------|----------|----------------|
| `source` | — | Hardcoded: `"devpost"` |
| `opportunity_type` | — | Always `"hackathon"` |
| `actionability_tier` | — | Always `"compete"` |
| `title` | `<title>` | Use as-is |
| `url` | `<link>` | Use as-is |
| `canonical_url` | `<link>` | Normalize |
| `summary` | `<description>` | Strip HTML tags. First 1000 chars. |
| `tags` | `<description>` keywords | Keyword extract: `blockchain`, `ai`, `web3`, etc. |
| `tech_stack` | `<description>` | Keyword extract |
| `domains` | `<description>` | Map keywords to domain vocab |
| `published_at` | `<pubDate>` | Parse to UTC |
| `deadline_at` | `<description>` | Attempt regex parse for deadline date. Null if not found. Flag `deadline_parsed: false` in raw_metadata. |
| `engagement.participants` | `<description>` | Attempt regex parse for participant count. Null if not found. |
| `reward.type` | `<description>` | `"cash"` if prize amount found. `"recognition"` otherwise. |
| `reward.amount` | `<description>` | Regex for dollar amounts. Null if not found. |
| `reward.currency` | `<description>` | `"USD"` if amount found and no currency specified. |
| `reward.description` | `<description>` prize section | Max 200 chars. |
| `raw_metadata` | Full RSS entry | Store |

---

## 3. Validation Rules

Validation runs after normalization, before the record enters the scoring pipeline.
Invalid records are **rejected** (not scored, not stored, logged to `pipeline_runs.error_log`).
Warning records are **stored with a flag** but still processed.

### 3.1 Hard Validation (Reject if Fails)

| Rule ID | Field | Rule | Error Message |
|---------|-------|------|---------------|
| V01 | `id` | Must be valid UUID v4 | "Missing or invalid record ID" |
| V02 | `source` | Must be in allowed source enum | "Unknown source: {value}" |
| V03 | `opportunity_type` | Must be in type enum (Section 5) | "Unknown opportunity type: {value}" |
| V04 | `title` | Must be non-empty string, ≤ 300 chars | "Title missing or too long" |
| V05 | `url` | Must match `^https?://` | "URL missing or malformed" |
| V06 | `canonical_url` | Must be non-empty, must match `^https?://` | "Canonical URL invalid" |
| V07 | `url_hash` | Must be 64-char hex string | "URL hash missing or malformed" |
| V08 | `published_at` | Must be parseable ISO 8601 UTC datetime | "published_at missing or invalid" |
| V09 | `actionability_tier` | Must be in tier enum (Section 5.2) | "Unknown actionability tier" |

### 3.2 Soft Validation (Warn, Do Not Reject)

| Rule ID | Field | Rule | Warning Message |
|---------|-------|------|-----------------|
| W01 | `summary` | Empty or null | "No summary — scoring relevance will be lower" |
| W02 | `tags` | Empty array | "No tags provided — domain mapping may fail" |
| W03 | `published_at` | Older than 7 days | "Stale item — recency score will be 0" |
| W04 | `deadline_at` | Non-null but in the past | "Deadline already passed — opportunity expired" |
| W05 | `engagement` | All sub-fields null | "No engagement signals — popularity score will be 0" |
| W06 | `title` | Duplicate of existing title in DB (fuzzy) | "Possible duplicate — different URL, same title" |

### 3.3 Domain Vocabulary Mapping

The normalizer uses this lookup table to populate `domains` from source-specific tags:

```
"ai" ←  cs.AI, machine-learning, deep-learning, llm, gpt, transformers, nlp
"ml" ←  cs.LG, scikit-learn, xgboost, pytorch, tensorflow, jax
"data" ← dataset, data-science, pandas, spark, bigquery, etl
"infra" ← devops, docker, kubernetes, cloud, mlops, infrastructure
"web" ← react, nextjs, javascript, typescript, web3, frontend
"security" ← security, cryptography, privacy, blockchain
"robotics" ← robotics, ros, reinforcement-learning, simulation
```

---

## 4. Deduplication Strategy

### Layer 1: URL Hash (Primary — Always Active)

**Method:** SHA-256 of `canonical_url`
**When:** Before inserting into DB. Check `url_hash` uniqueness.
**Effect:** Exact duplicate URLs never stored twice.
**Cost:** O(1) — single index lookup.

**URL Canonicalization Rules (applied before hashing):**
1. Lowercase scheme and host: `HTTPS://GitHub.com` → `https://github.com`
2. Remove trailing slashes: `github.com/user/repo/` → `github.com/user/repo`
3. Remove common tracking parameters: `utm_source`, `utm_medium`, `utm_campaign`, `ref`
4. For Arxiv: strip version suffix: `arxiv.org/abs/2401.00001v2` → `arxiv.org/abs/2401.00001`
5. For GitHub: normalize to `github.com/{owner}/{repo}` (strip `/tree/main`, `/blob/`, etc.)

**Example:**
```
Input:   https://GITHUB.COM/user/repo/tree/main?utm_source=trending
Output:  https://github.com/user/repo
Hash:    sha256("https://github.com/user/repo") = "3f4a..."
```

### Layer 2: Title Collision Detection (Secondary — Warning Only in MVP)

**Method:** Normalized title comparison within a 7-day window
**When:** After URL hash check passes
**Normalization:** Lowercase, remove punctuation, collapse whitespace
**Effect:** If a near-identical title already exists in DB with a different URL → emit W06 warning. **Do not reject.** Store both. Human reviews.
**Rationale:** Cross-posting is real (same paper on Arxiv + a GitHub release). Both URLs have value.

**Future (Post-MVP):** Promote to hard deduplication with configurable Levenshtein distance threshold.

### Layer 3: Source-Specific ID Deduplication (Future)

When sources provide stable IDs (e.g., Arxiv paper ID, GitHub repo ID), store these in `raw_metadata` and use them for cross-session deduplication even if the URL changes.

**Not implemented in MVP.** URL hash is sufficient.

---

## 5. Opportunity Types

### 5.1 Opportunity Type Enum

| Type | Code | Description | Primary Sources |
|------|------|-------------|-----------------|
| Tool | `tool` | Open-source library, SDK, CLI, or model that builders can use immediately | GitHub, HuggingFace |
| Paper | `paper` | Research paper — interesting but not directly actionable | Arxiv |
| Hackathon | `hackathon` | Time-boxed competition with submission and judging | Devpost |
| Dataset | `dataset` | A publicly available dataset for training, evaluation, or research | Arxiv, HuggingFace |
| Grant | `grant` | Non-dilutive funding requiring application | *Future: grants.gov, Gitcoin* |
| Bounty | `bounty` | Paid task for completing a specific technical deliverable | *Future: Gitcoin, IssueHunt* |
| Fellowship | `fellowship` | Structured program with application, cohort, and stipend | *Future: MLCommons, AI2* |
| Competition | `competition` | Non-hackathon competition with prizes (Kaggle, etc.) | *Future: Kaggle, DrivenData* |
| Funding | `funding` | Accelerator, grant program, or investment call | *Future: YC, a16z crypto* |

### 5.2 Actionability Tiers

Actionability answers: "What can I DO with this right now?"

| Tier | Code | Meaning | Types That Use It |
|------|------|---------|-------------------|
| Compete | `compete` | Enter and build something for judgment | hackathon, competition |
| Apply | `apply` | Submit an application for consideration | grant, fellowship, funding |
| Earn | `earn` | Complete a task for direct payment | bounty |
| Use | `use` | Integrate into a project today | tool, dataset |
| Learn | `learn` | Informational — no immediate action | paper |

**Scoring implication:**
- `compete`, `apply`, `earn` → no score penalty
- `use` → no score penalty
- `learn` → **-10 score penalty** (still stored, rarely sent in digest)

### 5.3 Actionability Decision Tree for Arxiv Papers

```
Is "code available" mentioned?       → tool     → use
Is "dataset released" mentioned?     → dataset  → use
Is "benchmark introduced" mentioned? → dataset  → use
Does title contain "survey of"?      → paper    → learn (-10 penalty)
Everything else?                     → paper    → learn (-10 penalty)
```

---

## 6. Future Source Compatibility

The canonical schema is designed to accommodate future opportunity sources without modification.
New sources only need a new fetcher that maps to the existing schema.

### 6.1 Future Sources Roadmap

| Source | Type | URL | Integration Complexity |
|--------|------|-----|----------------------|
| Gitcoin | bounty | `gitcoin.co` | API available. Medium. |
| IssueHunt | bounty | `issuehunt.io` | RSS available. Low. |
| Grants.gov | grant | `grants.gov` | RSS + API. Medium. |
| Devfolio | hackathon | `devfolio.co` | RSS available. Low. |
| MLContests | competition | `mlcontests.com` | Scrape. Low. |
| Kaggle | competition | `kaggle.com` | API available (free). Low. |
| AI2 Grants | grant | `allenai.org` | Scrape. Medium. |
| Pioneer.app | fellowship | `pioneer.app` | Scrape. Medium. |
| HumanLoop | bounty | Various | No API — Low priority |
| YC W25 | funding | `ycombinator.com` | Scrape. Medium. |

### 6.2 Schema Fields Required for Future Sources

These canonical fields are defined NOW but populated with null for current MVP sources:

| Field | Why Defined Now | Used By Future |
|-------|----------------|----------------|
| `deadline_at` | Hackathons need deadlines | grant, fellowship, competition |
| `reward.amount` | Prize tracking | bounty, hackathon, competition |
| `reward.type` | Cash vs. equity vs. credits | grant, bounty, funding |
| `actionability_tier` | Sorting by urgency | All future types |
| `opportunity_type` | Type-specific rendering in bot | All future types |

### 6.3 Schema Evolution Contract

**Rule:** The canonical schema may ADD new fields. It may NOT rename or remove existing fields without a migration plan documented in a new spec.

**Backward compatibility:** `raw_metadata` is the escape hatch. Any source-specific field that has no canonical mapping goes there. If a field appears in `raw_metadata` for 3+ sources, it's a candidate for promotion to the canonical schema.

---

## 7. Opportunity Feedback Schema

> **CTO Mandate (Change #2):** Add this table immediately. This is the moat.

### 7.1 OpportunityFeedback Record

```json
{
  "id": "",
  "opportunity_id": "",
  "user_id": "",
  "signal": "",
  "note": null,
  "created_at": ""
}
```

### 7.2 Signal Vocabulary

| Signal | Code | Meaning | Score Implication (Future) |
|--------|------|---------|---------------------------|
| Saved | `saved` | Bookmarked for later | Mild positive |
| Building | `building` | Actively using/building with this | Strong positive |
| Applied | `applied` | Submitted application (grants/hackathons) | Strong positive |
| Won | `won` | Won or succeeded with this opportunity | Very strong positive |
| Ignored | `ignored` | Explicitly not interested | Mild negative |
| Wrong | `wrong` | Misclassified or irrelevant | Strong negative (training signal) |

### 7.3 Feedback Loop Design (Post-MVP Path)

```
Current (MVP):
  score = recency + popularity + novelty(10) + relevance

Future (after N=30 feedback records):
  score = recency + popularity + novelty(10) + relevance + feedback_signal_bonus

Where:
  feedback_signal_bonus = weighted_average(
    signals for similar tags and types in last 90 days
  )
```

The `wrong` signal additionally triggers:
- Keyword list review (was a relevance keyword false-positive?)
- Source review (is this source consistently wrong-typed?)

**This is the system's memory. Start recording it on Day 1.**

### 7.4 Telegram Bot Feedback Interface — MVP Commands

**MVP ships two commands only (CTO Decision #2):**

```
/save <id>    — Mark as saved. Increments outcome.saved_count.
/wrong <id>   — Mark as wrong/irrelevant. Increments outcome.wrong_count.
```

All other signals (`/building`, `/applied`, `/won`, `/ignored`) are **deferred to post-MVP.**
The rationale: `save` and `wrong` are the highest-signal actions on Day 1.
`save` = this is real. `wrong` = your classifier is broken. Both are immediately actionable.

**Post-MVP planned interface (inline keyboard):**
```
[💾 Save]  [🔨 Building]  [📝 Applied]  [✗ Wrong]
```

---

## 8. Digest Quota System

> **CTO Decision #1 on pure theory papers:** Do not hard-exclude. Use a quota.

### 8.1 Daily Digest Slot Allocation (10 items)

| Slot | Count | Allowed Types | Selection Rule |
|------|-------|---------------|---------------|
| Tools | 4 | `tool` | Top 4 by score |
| Opportunities | 3 | `hackathon`, `bounty`, `grant`, `competition`, `fellowship` | Top 3 by score |
| Datasets | 2 | `dataset` | Top 2 by score |
| Research | 1 | `paper` | Top 1 by score (regardless of score floor) |

### 8.2 Quota Fallback Rules

If insufficient items exist in a category:

```
If Tools < 4:      fill remaining slots from Opportunities (highest score)
If Opportunities < 3: fill remaining slots from Tools or Datasets
If Datasets < 2:   fill remaining slots from Tools
If Research < 1:   slot is empty — do not backfill with another category
```

**The Research slot is never backfilled.** An empty research slot is preferable to
sending a low-quality tool that should have been excluded.

### 8.3 Why This Matters

Attention Is All You Need, LoRA, and FlashAttention would all score below 50
under pure deterministic scoring (no stars on day 1, no engagement signals).
The quota system ensures landmark research always gets one slot in the digest,
even when it can't compete with trending tools on popularity signals.

---

## 9. The Canonical Schema as Contract

### 8.1 Fetcher Contract

Every fetcher MUST:
- Return a list of `OpportunityRecord` dicts
- Populate all Required fields
- Set null (not omit) for Optional fields it cannot provide
- Put all extra source data into `raw_metadata`
- NOT call the database
- NOT call the scorer
- NOT send Telegram messages

Every fetcher MUST NOT:
- Return partially constructed records
- Raise exceptions for individual item parse failures (log and skip)
- Make assumptions about how its data will be used

### 8.2 Scorer Contract

The scorer MUST:
- Accept an `OpportunityRecord` dict
- Read only: `published_at`, `engagement`, `tags`, `title`, `summary`, `actionability_tier`
- Write only: `score`, `score_breakdown`
- Return the modified record
- Apply the `-10 penalty` for `actionability_tier = "learn"`

### 8.3 Notifier Contract

The notifier MUST:
- Accept a list of scored `OpportunityRecord` dicts
- Use only: `title`, `url`, `summary`, `tags`, `score`, `source`, `opportunity_type`, `reward`
- Format using the Telegram template defined in MVP_SPEC Section 6

---

## Appendix A: Revised Scoring Formula (CTO Approved)

```
score = min(100, recency + popularity + novelty + relevance + actionability_penalty)

Where:
  recency    = 0–30  (unchanged from MVP_SPEC)
  popularity = 0–30  (unchanged from MVP_SPEC)
  novelty    = 10    (CHANGED: fixed floor, not 20)
  relevance  = 0–20  (unchanged from MVP_SPEC)
  actionability_penalty = -10 if actionability_tier == "learn" else 0

Max possible score:
  30 + 30 + 10 + 20 + 0  = 90  (for tool/hackathon/etc.)
  30 + 30 + 10 + 20 - 10 = 80  (for paper with actionable release)
  30 + 0  + 10 + 20 - 10 = 50  (for pure theory paper)
```

**Why 10 not 20 for novelty:** Every item is new by definition (deduplication enforced).
A fixed 20 was free points for everything equally. 10 is a smaller floor that lets
recency and popularity differentiate items more meaningfully.

---

## Appendix B: Repository Structure (CTO Decision #3)

```
OpportunityOS/
├── 01_SPECS/
│   ├── draft/             ← Specs awaiting CTO review
│   ├── approved/          ← Antigravity can only build from here
│   └── rejected/          ← Rejected specs with reason documented
├── 02_DECISIONS/          ← CTO decision records (ADRs)
├── 03_MEMORY/             ← System state: what was sent, what worked
├── 04_EVALS/              ← Scoring evaluations and calibration logs
└── 05_CODE/               ← All implementation code
    ├── db/
    ├── scheduler/
    └── bot/
```

**Rule:** Antigravity reads only from `01_SPECS/approved/`. No exceptions.
A spec file physically moves from `draft/` to `approved/` only after CTO sign-off.
The act of moving the file IS the approval.

**This document moves to: `01_SPECS/approved/SCHEMA_SPEC.md`** upon CTO merge.

---

## Appendix C: Quick Reference — Field Requirement Matrix

| Field | GitHub | HuggingFace | Arxiv | Devpost | Grant (Future) | Bounty (Future) |
|-------|--------|-------------|-------|---------|----------------|-----------------|
| `id` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `source` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `opportunity_type` | tool | tool/dataset | paper/tool/dataset | hackathon | grant | bounty |
| `title` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `url` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `summary` | ⚠️ optional | ⚠️ optional | ✅ (abstract) | ⚠️ optional | ✅ | ✅ |
| `tags` | ✅ (topics) | ✅ | ✅ (subject) | ⚠️ extracted | ✅ | ✅ |
| `published_at` | ✅ | ⚠️ inferred | ✅ | ✅ | ✅ | ✅ |
| `deadline_at` | null | null | null | ⚠️ extracted | ✅ | ✅ |
| `engagement.stars` | ✅ | null | null | null | null | null |
| `engagement.likes` | null | ✅ | null | null | null | null |
| `engagement.participants` | null | null | null | ⚠️ extracted | null | null |
| `reward.amount` | null | null | null | ⚠️ extracted | ✅ | ✅ |
| `raw_metadata` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Legend: ✅ = always present | ⚠️ = best-effort | null = always null

---

*Document status: ✅ APPROVED*
*Location: `01_SPECS/approved/SCHEMA_SPEC.md`*
*Next documents: FEEDBACK_SPEC.md · ANTIGRAVITY_PROTOCOL.md*
