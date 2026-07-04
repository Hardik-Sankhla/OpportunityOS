# ADR 011: Bot Interface Strategy

## Status
Accepted

## Context
OpportunityOS is entering Step 11: Telegram Bot implementation. As the primary user interface, there is a strong temptation to push application logic (ranking, filtering, complex queries) into the bot itself. Additionally, the bot must be resilient against unauthorized usage and duplicate feedback that could pollute the scoring engine.

## Decision
1. **Bot is a Thin Transport Layer**: The bot shall contain NO scoring logic, NO ranking logic, NO fetch logic, and NO standalone business logic. It acts purely as a transport layer between Telegram and the database client.
2. **Strict MVP Command Set**: Only 5 commands are authorized: `/today`, `/sources`, `/save <id>`, `/wrong <id>`, and `/help`. All other commands (e.g., `/search`, `/analytics`) are forbidden in MVP.
3. **Authorization-First**: Every command must validate the Telegram User ID against the `ALLOWED_USER_IDS` environment variable before ANY database interaction occurs.
4. **Idempotent Feedback**: Feedback commands (`/save`, `/wrong`) must be idempotent. The bot must verify that a user hasn't already provided the specific signal for a specific opportunity ID before inserting a new record. (Since `init.sql` lacks a UNIQUE constraint for this in MVP, the check will be handled in Python).
5. **Graceful Degradation**: The bot must fail gracefully if the database is unreachable, replying with a user-friendly error instead of crashing.

## Consequences
- **Positive**: Complete separation of concerns. The bot can be rewritten or replaced (e.g., with a web UI) without losing any core OpportunityOS logic.
- **Positive**: Strict auth and idempotency ensure clean analytics and feedback signals.
- **Negative**: The idempotency check requires a read before every write, adding slight latency (acceptable at this scale).
- **Technical Debt**: A UNIQUE constraint `(telegram_user_id, opportunity_id, signal)` should eventually be added to the `opportunity_feedback` table in a future migration.
