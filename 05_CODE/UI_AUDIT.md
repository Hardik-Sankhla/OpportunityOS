# UI Audit & Design System Plan: OpportunityOS Terminal

This audit analyzes the provided HTML design patterns as a UI/UX reference and defines how to translate this high-impact, neo-brutalist visual language into the OpportunityOS interface, evolving it into an **Opportunity Terminal**.

---

## 1. Design System

The reference page implements a **cyber-brutalist / neo-brutalist** design language adapted for modern web interfaces. It combines clean typography with high-contrast layouts, structural borders, and flat shadow effects.

### Color Palette
*   **Base Background**: Dark charcoal/black (`#0A0A0A`) providing deep contrast and minimizing eye strain during long terminal usage.
*   **Surface Color**: Matte grey (`#171717`) for cards and panels, creating distinct separation from the base canvas.
*   **Border Color**: Slate grey (`#333333`) used as standard outlines instead of soft shadows.
*   **Accents (Status & Categorization)**:
    *   `#8B5CF6` (Purple): Secondary branding / navigation focus.
    *   `#10B981` (Emerald): Success / Active status / High-value scoring.
    *   `#F59E0B` (Amber): Warning / Caution / Moderate-value scoring.
    *   `#E11D48` (Rose): Critical error / Failed status / Irrelevant items.
    *   `#06B6D4` (Cyan): Informational status / Metadata.

### Typography
*   **Headings**: `Space Grotesk` (Geometric, wide aperture, high-impact). Designed for strong tracking and all-caps titles.
*   **Body**: `Inter` (Highly legible, neutral sans-serif). Handles mid-to-high density textual metadata cleanly.
*   **Data & System Output**: `Roboto Mono` (Tabular figures, consistent alignment). Perfect for numbers, scores, parameters, and logs.

### Card Design & Elevation
*   **Flat Neo-Brutalism**: Avoids blurred box-shadows. Instead, cards use a solid, hard offset shadow:
    `border: 2px solid #333333; box-shadow: 6px 6px 0px 0px #333333;`
*   **Tactile Hover State**: Interactive elements translate on hover to simulate physical clicks:
    `transform: translate(2px, 2px); box-shadow: 4px 4px 0px 0px #333333;`
*   **Status Borders**: Left-hand borders on cards map status colors directly (e.g., green for high-priority opportunities, red for ignored).

### Table Design
*   **Dense Columns**: Minimal spacing with explicit border grid lines (`border: 1px solid #333333`) to prevent visual drift.
*   **Sticky Header**: Solid black background headers pinned to the top of the table viewport for high-scroll datasets.
*   **Row Highlight**: Distinct background shift on row hover (`background: #262626`) for rapid scanning.

---

## 2. Information Architecture

The reference layout is structured around maximum scannability and structural density:
*   **Persistent Masthead**: A 20-rem tall sticky navigation bar providing clear orientation and category switching.
*   **Section Blocks**: Large, blocky labels wrapped in solid accent pills to define layout changes.
*   **Columnar Grids**: Multi-column responsive grids that display cards containing both quick stats (badge elements) and core data summaries.
*   **Tabular Density**: Dense tables designed to prioritize columns over spacing, preserving horizontal real estate.

---

## 3. OpportunityOS Adaptation

Rather than showing long text blocks, the visual language will be adapted into an **"Opportunity Terminal"** interface. The UI will shift from reading-heavy to action-heavy (Opportunity $\rightarrow$ Signal $\rightarrow$ Action):

```
┌────────────────────────────────────────────────────────┐
│ OpportunityOS Terminal v1.0.0               [🟢 DB: OK] │
├────────────────────────────────────────────────────────┤
│  [🔥 HOT]   |   [💰 GRANTS]   |   [🏆 HACK]   |   [⚡ BOUNTY]  │
├────────────────────────────────────────────────────────┤
│  ID   | SOURCE | TYPE    | TITLE                 | SCORE│
│  001  | HF     | Dataset | agentic-distill-fable |  80  │
│  002  | GitHub | Repo    | Qwen/AgentWorldBench  |  80  │
├────────────────────────────────────────────────────────┤
│  ACTIONS: [/save <id>]   [/wrong <id>]                 │
└────────────────────────────────────────────────────────┘
```

---

## 4. MVP UI

The Minimum Viable Product UI focuses strictly on displaying daily outputs and accepting basic user feedback commands.

### Structure
*   **Single-Screen Layout**: Split vertically. Left: Active Ingestion feed list. Right: Inspector & feedback pane.
*   **Key Panels**:
    *   **Pipeline Health Panel**: Shows latest execution metrics (fetch counts by source, execution time).
    *   **Hot List**: A dense table of the top 10 current opportunities (derived from `/today` bot command).
    *   **Terminal Input**: Command-line style prompt to execute `/save` or `/wrong`.

---

## 5. Phase 2 UI

Phase 2 introduces active filtering, search, and dynamic scoring analytics.

### Structure
*   **Multi-View Dashboard**: Tabs to switch between:
    1.  **Terminal**: Active stream of real-time opportunities.
    2.  **Analytics**: Performance charts of models and sources.
    3.  **Config**: Live tuning panel for scorer criteria weights.
*   **Key Panels**:
    *   **Scoring Breakdown**: Interactive radar chart showing how a selected opportunity's score was calculated.
    *   **Feedback Metrics**: Stored statistics on saved vs. rejected items to validate algorithmic accuracy.

---

## 6. Phase 3 UI

Phase 3 implements full automation control, system configuration, and data-graph visualization.

### Structure
*   **Control Room Layout**: Three-pane interface. Left: Ingestion orchestration trees. Center: Main workspace/graph view. Right: Config parameter inputs.
*   **Key Panels**:
    *   **Dynamic Source Topology**: Graphical network diagram showing active ingestion crawlers, health metrics, and failure counts.
    *   **Auto-Tuner**: AI-assisted recommendation pane suggest weight updates based on user save/wrong telemetry history.

---

## 7. Components to Reuse

*   **Cyber-Brutalist Layout Base**: Use the deep `#0A0A0A` base and `#171717` panels with thick `#333333` borders.
*   **Interactive Cards (with Accent Borders)**: High-contrast target panels with left-side status borders (emerald for high score, amber for medium, rose for low).
*   **Monospace Data Badges**: Use `Roboto Mono` tags for display indicators like `Score: 80` or `Err: 0`.
*   **Dense Grid Tables**: Utilize the sticky header, hover-state, grid-bordered table design to represent large lists of opportunities.
*   **Tactile Button Hovers**: Use the flat offset shadow translation animation on clickable actions.

---

## 8. Components to Reject

*   **Long-Form Paragraph Blocks**: Reject all multi-sentence paragraphs; the user only needs titles, key tags, and metrics.
*   **Educational Callouts**: Remove explanations of theory; replace callout blocks with direct log dumps or error code callouts.
*   **Aesthetic Device Frames**: Avoid mockups inside fake screens; prioritize raw application density.
*   **Deep Hierarchy Headers**: Limit header titles to two levels to optimize vertical density.
