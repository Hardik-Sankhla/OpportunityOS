# ADR 008: Hugging Face Scraping Strategy

## Status
✅ Accepted (2026-07-04)

## Context
For Step 7, OpportunityOS requires trending models, datasets, and spaces from Hugging Face. Hugging Face does not provide an official RSS feed for these trending categories. While some undocumented JSON endpoints exist, HTML scraping of the trending pages provides the most direct representation of what users see on the platform's front page. However, HTML scraping is inherently brittle and prone to breakage when UI structures change.

## Decision
We will use **HTML scraping** with `httpx` and `BeautifulSoup` to fetch Hugging Face trending opportunities.

### Rules for Hugging Face Fetcher:
1. **No Browser Automation**: Do not use Playwright, Selenium, or Puppeteer. This reduces memory, complexity, and test execution time.
2. **Isolation**: Selectors and extraction logic must be isolated within the fetcher file to make future repairs easy.
3. **Resilience**: The fetcher must fail gracefully. If CSS selectors drift and extraction fails, it must log the failure, return `[]`, and never crash the pipeline (Mitigating Risk R9).
4. **Scope**: Only collect Models, Datasets, and Spaces. Ignore Users, Organizations, and Collections.
5. **Mapping**: 
   - Models -> `opportunity_type = "tool"`, `actionability_tier = "use"`
   - Spaces -> `opportunity_type = "tool"`, `actionability_tier = "use"`
   - Datasets -> `opportunity_type = "dataset"`, `actionability_tier = "use"`

## Consequences
- **Positive**: Lightweight dependency footprint (only `httpx` and `beautifulsoup4`).
- **Positive**: Direct access to exactly what is trending on the platform's UI.
- **Negative**: High likelihood of selector drift requiring periodic maintenance (Risk R9).
