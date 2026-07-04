# ADR 010: Telegram Delivery Strategy

## Status
✅ Accepted (2026-07-04)

## Context
OpportunityOS is a push-based system (per MVP Spec). In Round 1, Step [9], we are implementing the `scheduler/notifier/telegram.py` module to format and deliver daily digests to the CTO via Telegram. Telegram's Bot API is rich, but integrating complex features (like Webhooks or Inline Keyboards) introduces unnecessary failure modes, state management, and deployment complexity that we want to avoid during the MVP phase.

Additionally, Telegram has a strict `4096` character limit per message (Risk R11). If a digest exceeds this limit, the API returns an error, and silent truncation results in dropped opportunities.

## Decision
We will lock down the Telegram delivery implementation in `scheduler/notifier/telegram.py` to a highly constrained feature set.

### 1. Allowed Features
- **Polling (getUpdates)**: For the bot container (Step 11). Webhooks require HTTPS endpoints and external routing, which violates our simple 3-container architecture.
- **`sendMessage`**: The only API endpoint the notifier is allowed to call for delivery.
- **HTML Formatting**: Telegram's HTML parser is more forgiving than MarkdownV2, which requires aggressive escaping of special characters. We will use HTML for bolding (`<b>`), italicizing (`<i>`), and links (`<a href="...">`).

### 2. Forbidden Features (for MVP)
- **Webhooks**: Forbidden. Polling only.
- **Inline Keyboards**: Forbidden. The user interacts via simple slash commands (e.g., `/save`), not buttons.
- **MarkdownV2**: Forbidden. Escaping rules are brittle and often lead to `HTTP 400 Bad Request` on unescaped hyphens or periods.
- **Media Groups / Photo Sending**: Forbidden. Text only.

### 3. Handling Message Length Overflow (R11)
Telegram enforces a maximum message length of 4096 characters. The notifier must implement a deterministic `split_message(text: str) -> list[str]` function.
- If a formatted digest exceeds 4096 characters, it must be split across multiple `sendMessage` API calls.
- The split must happen safely at a logical boundary (e.g., double newline `\n\n` between opportunities).
- **Silent truncation is forbidden.**

## Consequences
- **Positive**: Delivery is robust, stateless, and simple to test. The HTML formatting avoids formatting-related API errors. The splitter prevents dropped opportunities.
- **Negative**: No rich UI interactions (buttons). Polling is slightly less efficient than webhooks but perfectly acceptable for a single-user system.
