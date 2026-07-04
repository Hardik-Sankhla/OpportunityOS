-- =============================================================================
-- OpportunityOS — Database Initialization
-- =============================================================================
-- Authorized by:
--   MVP_SPEC.md, Section 5 (Database Design)
--   SCHEMA_SPEC.md, Section 1.1–1.2 (OpportunityRecord — all fields)
--   SCHEMA_SPEC.md, Section 7 (Opportunity Feedback Schema — Day 1 requirement)
--   ANTIGRAVITY_PROTOCOL.md, Rule 10.2, Round 1, Step [1]
--
-- Rules observed:
--   - Tables only. No application code.
--   - No migrations (this is the bootstrap file only).
--   - Indexes only where required for correctness or MVP query performance.
--   - CHECK constraints enforce schema enums at DB level.
--   - File stays under 500 lines (ANTIGRAVITY_PROTOCOL.md Rule 2.1).
--
-- Tables created (in dependency order):
--   1. opportunities         — canonical record store
--   2. opportunity_feedback  — /save and /wrong signals (Day 1 per SCHEMA_SPEC Section 7)
--   3. pipeline_runs         — execution history
--   4. source_status         — per-source health (used by /sources command)
--
-- Do NOT run this file on a live database.
-- For changes after initial deployment, use numbered migration files:
--   05_CODE/db/migrations/001_description.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- TABLE: opportunities
-- Core record store for all normalized opportunity records.
-- Schema authority: SCHEMA_SPEC.md, Section 1.1 (OpportunityRecord)
-- ---------------------------------------------------------------------------
CREATE TABLE opportunities (

    -- Identity (SCHEMA_SPEC.md Section 1.2 — Identity Fields)
    id                      SERIAL          PRIMARY KEY,
    url_hash                CHAR(64)        NOT NULL,
        -- SHA-256 of canonical_url. Deduplication key. See SCHEMA_SPEC Section 4.
        -- UNIQUE index created separately below.
    source                  VARCHAR(32)     NOT NULL
        CHECK (source IN (
            'github', 'huggingface', 'arxiv', 'devpost',
            -- Future sources pre-registered per SCHEMA_SPEC Section 6.1:
            'grants_gov', 'gitcoin', 'devfolio', 'mlcontests'
        )),
    opportunity_type        VARCHAR(32)     NOT NULL
        CHECK (opportunity_type IN (
            -- MVP types:
            'tool', 'paper', 'hackathon', 'dataset',
            -- Future types (SCHEMA_SPEC Section 5.1):
            'grant', 'bounty', 'fellowship', 'competition', 'funding'
        )),
    actionability_tier      VARCHAR(16)     NOT NULL
        CHECK (actionability_tier IN (
            'compete', 'apply', 'earn', 'use', 'learn'
            -- See SCHEMA_SPEC Section 5.2 for tier definitions
        )),

    -- Content (SCHEMA_SPEC.md Section 1.2 — Content Fields)
    title                   TEXT            NOT NULL
        CHECK (char_length(title) <= 300),
    url                     TEXT            NOT NULL,
    canonical_url           TEXT            NOT NULL,
    summary                 TEXT
        CHECK (summary IS NULL OR char_length(summary) <= 1000),

    -- Classification (SCHEMA_SPEC.md Section 1.2 — Classification Fields)
    tags                    TEXT[]          NOT NULL DEFAULT '{}',
    tech_stack              TEXT[]          NOT NULL DEFAULT '{}',
    domains                 TEXT[]          NOT NULL DEFAULT '{}',

    -- Time (SCHEMA_SPEC.md Section 1.2 — Time Fields)
    published_at            TIMESTAMPTZ     NOT NULL,
    deadline_at             TIMESTAMPTZ,
        -- Null for sources that have no deadline (GitHub, HF, Arxiv in MVP).
        -- Required for future: grant, bounty, fellowship, competition.

    -- Engagement (SCHEMA_SPEC.md Section 1.2 — Engagement Fields)
    -- NULL means the signal is not available from this source. NOT zero.
    -- See SCHEMA_SPEC Appendix C for which sources provide which signals.
    engagement_stars        INTEGER,        -- GitHub only
    engagement_likes        INTEGER,        -- HuggingFace only
    engagement_forks        INTEGER,        -- GitHub only
    engagement_watchers     INTEGER,        -- GitHub only
    engagement_participants INTEGER,        -- Devpost only

    -- Reward (SCHEMA_SPEC.md Section 1.2 — Reward Fields)
    -- All null for GitHub, HuggingFace, Arxiv in MVP.
    -- Populated for Devpost (best-effort from description regex).
    reward_type             VARCHAR(16)
        CHECK (reward_type IS NULL OR reward_type IN (
            'cash', 'equity', 'credits', 'swag', 'recognition', 'none'
        )),
    reward_amount           NUMERIC(12, 2),
    reward_currency         CHAR(3),        -- ISO 4217, e.g. 'USD'
    reward_description      TEXT
        CHECK (reward_description IS NULL OR char_length(reward_description) <= 200),

    -- Scoring (SCHEMA_SPEC.md Section 1.2 — Scoring Fields)
    -- Populated by scorer after fetcher runs. NULL until scored.
    score                   SMALLINT
        CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
    score_recency           SMALLINT
        CHECK (score_recency IS NULL OR (score_recency >= 0 AND score_recency <= 30)),
    score_popularity        SMALLINT
        CHECK (score_popularity IS NULL OR (score_popularity >= 0 AND score_popularity <= 30)),
    score_novelty           SMALLINT
        CHECK (score_novelty IS NULL OR score_novelty = 10),
        -- Fixed at exactly 10. Any other value is a protocol violation.
        -- See ADR_003 for rationale. Change requires: ADR superseding + migration.
    score_relevance         SMALLINT
        CHECK (score_relevance IS NULL OR (score_relevance >= 0 AND score_relevance <= 20)),

    -- Outcome (SCHEMA_SPEC.md Section 1.2 — Outcome Fields)
    -- Denormalized from opportunity_feedback for O(1) count reads.
    -- Read from this table. Write to opportunity_feedback AND increment here.
    outcome_saved_count     INTEGER         NOT NULL DEFAULT 0,
    outcome_wrong_count     INTEGER         NOT NULL DEFAULT 0,
    outcome_building_count  INTEGER         NOT NULL DEFAULT 0,  -- reserved, MVP = 0
    outcome_applied_count   INTEGER         NOT NULL DEFAULT 0,  -- reserved, MVP = 0
    outcome_won_count       INTEGER         NOT NULL DEFAULT 0,  -- reserved, MVP = 0

    -- Opportunity Strength (SCHEMA_SPEC.md Section 1.2 — Opportunity Strength Fields)
    -- ALL null in MVP. Schema defined now for future "make money this month" ranking.
    -- See SCHEMA_SPEC Section 1.2 for field definitions.
    -- No scoring logic reads these in MVP.
    strength_urgency        REAL,           -- 0.0–1.0, null in MVP
    strength_difficulty     REAL,           -- 0.0–1.0, null in MVP
    strength_monetization   REAL,           -- 0.0–1.0, null in MVP
    strength_time_to_value  REAL,           -- 0.0–1.0, null in MVP

    -- Pipeline metadata
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    sent_at                 TIMESTAMPTZ,    -- NULL = not yet included in a digest

    -- Raw source data (SCHEMA_SPEC.md Section 1.2 — Raw Metadata)
    -- Never read by pipeline logic. Used for debugging and future schema evolution.
    raw_metadata            JSONB           NOT NULL DEFAULT '{}'::jsonb
);

-- ---------------------------------------------------------------------------
-- TABLE: opportunity_feedback
-- User feedback signals from /save and /wrong Telegram commands.
-- Schema authority: SCHEMA_SPEC.md, Section 7 (Opportunity Feedback Schema)
--
-- Day 1 requirement: "You cannot recover lost feedback history." — CTO
-- MVP signals: 'saved' (/save command), 'wrong' (/wrong command)
-- Post-MVP signals: 'building', 'applied', 'won', 'ignored'
-- ---------------------------------------------------------------------------
CREATE TABLE opportunity_feedback (
    id                      SERIAL          PRIMARY KEY,
    opportunity_id          INTEGER         NOT NULL
        REFERENCES opportunities(id) ON DELETE CASCADE,
    telegram_user_id        BIGINT          NOT NULL,
        -- Telegram user ID (integer, not username — usernames can change)
    signal                  VARCHAR(16)     NOT NULL
        CHECK (signal IN (
            'saved',    -- /save command — MVP
            'wrong',    -- /wrong command — MVP
            'building', -- post-MVP
            'applied',  -- post-MVP
            'won',      -- post-MVP
            'ignored'   -- post-MVP
        )),
    note                    TEXT,           -- optional free-text, post-MVP only
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- TABLE: pipeline_runs
-- Execution record for every pipeline run.
-- Schema authority: MVP_SPEC.md, Section 5
-- ---------------------------------------------------------------------------
CREATE TABLE pipeline_runs (
    id                      SERIAL          PRIMARY KEY,
    started_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    finished_at             TIMESTAMPTZ,
    status                  VARCHAR(16)     NOT NULL DEFAULT 'running'
        CHECK (status IN (
            'running',  -- pipeline is executing
            'success',  -- all sources fetched, digest sent
            'partial',  -- one or more sources failed, digest still sent
            'failed'    -- pipeline crashed entirely (ANTIGRAVITY_PROTOCOL Rule 6.1 Class 6)
        )),
    items_fetched           INTEGER         NOT NULL DEFAULT 0,
    items_new               INTEGER         NOT NULL DEFAULT 0,
    items_sent              INTEGER         NOT NULL DEFAULT 0,
    error_log               TEXT            -- NULL on success, populated on partial/failed
);

-- ---------------------------------------------------------------------------
-- TABLE: source_status
-- Per-source health tracking. Powers the /sources Telegram command.
-- Schema authority: MVP_SPEC.md, Section 5
-- Seeded with all MVP sources (see INSERT below).
-- ---------------------------------------------------------------------------
CREATE TABLE source_status (
    source                  VARCHAR(32)     PRIMARY KEY
        CHECK (source IN (
            'github', 'huggingface', 'arxiv', 'devpost',
            'grants_gov', 'gitcoin', 'devfolio', 'mlcontests'
        )),
    last_success_at         TIMESTAMPTZ,
    last_error_at           TIMESTAMPTZ,
    last_error_msg          TEXT,
    consecutive_failures    INTEGER         NOT NULL DEFAULT 0
);

-- =============================================================================
-- INDEXES
-- =============================================================================
-- Rule: "Do not generate indexes unless required."
-- — CTO instruction, ANTIGRAVITY_PROTOCOL.md
--
-- Only 3 indexes created. Justification for each is required.
-- =============================================================================

-- REQUIRED — Deduplication.
-- Every pipeline run checks this before inserting any record.
-- Without UNIQUE enforcement here, a race condition between scheduler
-- and any future concurrent writer could insert duplicates.
-- SCHEMA_SPEC.md Section 4 (Deduplication Strategy, Layer 1).
CREATE UNIQUE INDEX idx_opportunities_url_hash
    ON opportunities (url_hash);

-- REQUIRED — Digest selection.
-- The notifier runs: SELECT ... ORDER BY score DESC LIMIT N
-- on every pipeline run. Without this index, that is a full table scan
-- that grows daily. This index makes it O(log n).
CREATE INDEX idx_opportunities_score_desc
    ON opportunities (score DESC NULLS LAST);

-- REQUIRED — Unsent item query.
-- The notifier selects items where sent_at IS NULL to find what to send today.
-- Partial index covers only unsent rows — a small, stable fraction of the table.
-- Prevents re-sending already-delivered items (ANTIGRAVITY_PROTOCOL Rule 6.1).
CREATE INDEX idx_opportunities_unsent
    ON opportunities (fetched_at DESC)
    WHERE sent_at IS NULL;

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Seed source_status so /sources command works on Day 1 without requiring
-- a successful pipeline run first. All fields null except source name.
INSERT INTO source_status (source) VALUES
    ('github'),
    ('huggingface'),
    ('arxiv'),
    ('devpost');

-- =============================================================================
COMMIT;
-- =============================================================================
-- END OF FILE
-- Line count: < 200. Well within 500-line limit (ANTIGRAVITY_PROTOCOL Rule 2.1).
--
-- Next step per Rule 10.2, Round 1:
--   [2] 05_CODE/scheduler/db/client.py  (imports: psycopg2 only)
-- =============================================================================
