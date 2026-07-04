# ADR 007: GitHub Source Strategy

## Status
✅ Accepted (2026-07-04)

## Context
For Step 6, OpportunityOS requires trending repositories from GitHub. We could either scrape the GitHub Trending page (HTML parsing) or use the official GitHub REST Search API. Web scraping is prone to breakages when GitHub updates their UI, whereas the Search API provides structured, schema-bound JSON.

## Decision
We will use the **GitHub Search API** instead of web scraping.

### Rules for GitHub Fetcher:
1. **API Usage**: Must hit the Search API (`/search/repositories`) looking for repositories created recently with high star velocity.
2. **Authentication**: Must use `GITHUB_TOKEN` if present in the environment to avoid strict rate limits.
3. **Fallback**: Must continue to function in unauthenticated mode (without crashing) if the token is missing.
4. **Resilience**: Must gracefully handle Rate Limit errors (HTTP 403) and return `[]` to prevent pipeline crashes.
5. **Quality Filter**: Repositories must meet the MVP bar:
   - `stars >= 100`
   - Created within the last 90 days.
   - Must have a description.
   - Must have a detected programming language.

## Consequences
- **Positive**: Structured data extraction without fragility. Guaranteed access to exact star counts, language metadata, and creation dates.
- **Positive**: Low maintenance.
- **Negative**: Subject to GitHub API rate limits (10 requests/minute unauthenticated, 30/minute authenticated). Since the fetcher runs once per day, this is a non-issue.
