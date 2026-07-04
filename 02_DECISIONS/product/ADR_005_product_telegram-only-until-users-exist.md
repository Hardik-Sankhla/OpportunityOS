# ADR_005: Use Telegram as the Only User Interface Until Real Users Exist

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Product
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

OpportunityOS is a zero-user system on Day 1. Before any user has interacted with
the product, building a web dashboard, mobile app, or email delivery system is pure
speculation about what users need. The cost of building the wrong interface is high:
frontend frameworks, hosting, authentication, and maintenance create permanent
complexity. The project has a zero-cost constraint and a single operator.

Telegram was selected because: the Bot API is free with no rate-limit tiers,
the bot runs in polling mode requiring no open ports or TLS certificates, message
formatting is sufficient for a text-based digest, and one-command bot creation via
@BotFather requires no approval process.

## Decision

Telegram is the only user interface for OpportunityOS until at least one real user
is actively using the `/today` command daily for 30 consecutive days.

"Real user" is defined as: a human who discovered the bot independently or through
word-of-mouth, not the operator themselves. The 30-day threshold ensures the usage
is habitual, not experimental.

No web UI, no email delivery, no mobile app, and no Slack/Discord integration will
be built before this threshold is crossed.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Email digest | Requires SMTP configuration, bounce handling, unsubscribe compliance (CAN-SPAM), and deliverability management. Solves no problem Telegram doesn't already solve for a single operator. |
| Web dashboard (Next.js / React) | Requires frontend build pipeline, static hosting or a server, authentication, and ongoing maintenance. We have zero evidence users want a web interface. |
| Slack | Adding a second integration multiplies maintenance burden with no differentiated value. Slack bots require workspace admin approval in many organizations. |
| Discord | Same issues as Slack. Also requires a server with appropriate channels, adding setup friction. |
| RSS output | Passive — no interaction, no feedback signals. Cannot support `/save` or `/wrong` commands that are core to the learning system. |

## Consequences

**Positive:**
- Zero frontend development time in the first 60+ days
- Bot polling requires no open ports, no reverse proxy, no TLS certificate management
- `/save` and `/wrong` feedback commands work natively in Telegram with no additional tooling
- Telegram handles message delivery, retry, and read receipts automatically
- One-command deployment: `docker compose up bot`

**Negative / Trade-offs:**
- Not accessible to users who don't have or use Telegram
- Digest formatting is constrained to Telegram's Markdown subset (4096 char limit per message)
- No persistent UI — users cannot browse historical opportunities without `/today`

**Neutral changes:**
- All UX decisions in MVP are bounded by Telegram's message format constraints
- The 30-day threshold is a CTO decision, not a product metric — it exists to force discipline

## Rollback Plan

**Trigger condition:** The 30-day threshold is met. This ADR is then not "rolled back"
but "graduated" — a new interface is added alongside Telegram, not replacing it.
**Rollback steps:** N/A — this ADR expires naturally when its threshold condition is met.
A new ADR will be written for the next interface decision.
**Estimated rollback time:** N/A
**Irreversible aspects:** None. Every day using Telegram-only produces feedback data
that would not exist if time had been spent building a dashboard instead.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 4 (MVP Scope — What Will NOT Be Built)
- `01_SPECS/approved/MVP_SPEC.md`, Section 6 (Telegram Design)
- `01_SPECS/approved/SCHEMA_SPEC.md`, Section 7.4 (Telegram Bot Feedback Interface)
