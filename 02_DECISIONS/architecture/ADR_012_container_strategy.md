# ADR 012: Container Strategy

## Status
Accepted

## Context
OpportunityOS is entering the deployment phase (Steps 12-14). Unconstrained containerization often leads to operational complexity, massive attack surfaces, and difficult local environments (e.g., introducing Redis, Celery, multiple web servers, Grafana, etc.).

## Decision
1. **Three Containers Only**: The entire system will consist of exactly three containers: `db`, `scheduler`, and `bot`. This architecture is frozen until at least 2026-09-04.
2. **Same Base Image**: Both Python containers (`scheduler` and `bot`) must use `python:3.13-slim` to minimize image size and ensure a consistent runtime without the bulk of Ubuntu or Debian. Alpine is avoided for Python to prevent binary compilation headaches.
3. **Single-Stage Builds**: Multi-stage builds are forbidden for the MVP to prioritize debugging simplicity and maintainability over extreme optimization.
4. **Non-Root Execution**: Every custom container must create and run as a non-root user (`appuser`) to mitigate the impact of potential container escapes.
5. **No Baked Secrets**: Secrets must NEVER be injected via `ENV` in Dockerfiles. They must only be passed at runtime using an `env_file: .env` block in `docker-compose.yml`.
6. **One Process Per Container**: We will not use Supervisord, Systemd, or Nginx inside these containers. 
    - The `scheduler` container runs `supercronic` exclusively.
    - The `bot` container runs `python bot.py` exclusively.

## Consequences
- **Positive**: Very simple `docker-compose up` experience.
- **Positive**: Low memory footprint and tight security boundaries.
- **Negative**: The `bot` and `scheduler` containers share some source code (like schemas and DB clients). They must both be built from the monorepo root context to allow `bot.py` to import `scheduler` modules.
- **Risk**: Container startup ordering issues (R14). The `db` might not be fully ready when `bot` or `scheduler` starts. Connection retry logic is required in the application code rather than relying solely on Docker's `depends_on`.
