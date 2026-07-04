# ADR_001: Use Three-Container Docker Architecture

**Date:** 2026-07-04
**Status:** Accepted
**Category:** Architecture
**Decided By:** CTO
**Supersedes:** N/A
**Superseded By:** N/A

---

## Context

OpportunityOS requires three distinct runtime responsibilities: persistent data storage,
a scheduled daily pipeline, and an always-on Telegram bot. Each has different uptime
requirements and failure characteristics. The system runs locally on Ubuntu Linux
under Docker Compose with zero cloud dependency. The architecture must be deployable
with a single command and operable by one person.

## Decision

Run exactly three containers orchestrated by Docker Compose: `db` (PostgreSQL 16),
`scheduler` (daily pipeline + cron), and `bot` (Telegram polling). Each container
has a single responsibility. No additional containers will be introduced for at least
60 days from project start (until 2026-09-04).

The 60-day constraint explicitly excludes: Redis, Celery, RabbitMQ, Kafka, and any
additional database or message queue. These are banned by name, not by category,
because they represent the most common premature complexity additions in agent projects.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Monolithic single container | No isolation between concerns. A crashing bot kills the pipeline. A runaway pipeline starves the DB. |
| Five containers (separate fetcher, scorer, notifier) | Each pipeline stage as a container is microservices religion applied to a sequential batch job. The pipeline runs once daily. Separation provides zero benefit. |
| Systemd services (no Docker) | Less reproducible. Docker Compose provides one-command startup, built-in networking, volume management, and restart policies with zero additional tooling. |
| Docker Swarm / Kubernetes | Dramatically overengineered for a single-machine, single-user system. Explicitly banned by project constraints. |

## Consequences

**Positive:**
- `docker compose up` is the complete deployment command
- Container restart policies handle process crashes automatically
- Network isolation: only outbound HTTP calls; no inbound ports needed (polling mode)
- Each container can be restarted independently without affecting others
- Clear ownership: one container = one responsibility

**Negative / Trade-offs:**
- The scheduler and bot share the same DB container; a DB failure affects both simultaneously
- No horizontal scaling (acceptable: this is a single-user system)
- Pipeline and bot share the same psycopg2 connection pool configurations

**Neutral changes:**
- All three containers share one Docker network defined in `docker-compose.yml`
- PostgreSQL data persists via a named Docker volume (must be defined explicitly)
- The 60-day constraint requires an ADR to supersede before any new container is added

## Rollback Plan

**Trigger condition:** A fundamental architectural problem requires a fourth container
(e.g., async job queue for real-time processing becomes necessary).
**Rollback steps:**
1. Write a superseding ADR documenting the new container and its justification
2. Add the new service to `docker-compose.yml`
3. Update `ANTIGRAVITY_PROTOCOL.md` Rule 10.2 build order accordingly
**Estimated rollback time:** 1–2 hours for the container addition itself
**Irreversible aspects:** None. Containers can always be added or removed.

## References

- `01_SPECS/approved/MVP_SPEC.md`, Section 1 (System Architecture)
- `01_SPECS/approved/ANTIGRAVITY_PROTOCOL.md`, Preamble
