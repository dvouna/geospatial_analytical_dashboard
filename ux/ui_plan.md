# UX/UI Improvement Plan

This plan turns the UX/UI review into a practical implementation checklist. The goal is to reduce visual noise, make navigation clearer, preserve space for analysis, and make the interface feel more coherent across the dashboard.

## 1. Remove Global Column Card Styling

**Issue:** `app.py` styles every Streamlit column as a bordered card. Columns are used for page layout, control groups, metric rows, and narrow sidebars, so this creates accidental cards everywhere.

**Impact:** The interface feels heavier than necessary, with nested surfaces and inconsistent spacing.

**Recommendation:**
- Remove or narrow the global `[data-testid="column"]` styling.
- Keep card styling only for explicit custom classes such as `.kpi-card`, `.metric-panel`, or `.assistant-panel`.
- Use simple unframed columns for layout and controls.

**Files:**
- `app.py`
- `home_page.py`
- page modules where card-like containers are intentionally needed

**Acceptance Criteria:**
- Layout columns no longer automatically show borders, backgrounds, padding, or hover shadows.
- KPI cards retain their visual styling.
- Control rows feel lighter and denser.

## 2. Simplify Navigation

**Issue:** The app has two navigation systems: Streamlit sidebar navigation and a home-page topic radio that duplicates the same domains.

**Impact:** Users may not know whether `Population` on the home radio and `Population Demographics` in the sidebar are equivalent or separate workflows.

**Recommendation:**
- Use sidebar navigation as the primary page-level navigation.
- Keep the home page focused on the persistent map overview and selected-district summary.
- If the home page needs topic switching, label it as map overlay mode rather than page navigation.

**Files:**
- `app.py`
- `home_page.py`
- `map_fragment.py`

**Acceptance Criteria:**
- Major domains are reached from one clear navigation model.
- Home-page controls do not duplicate page navigation labels.
- Map-specific controls are named as map controls, not app navigation.

## 3. Reduce Instruction Density Above the Fold

**Issue:** Several pages render visible "How to use this page" blocks and also provide guide popovers.

**Impact:** The first viewport spends too much space explaining the tool instead of showing the tool.

**Recommendation:**
- Remove the visible "How to use this page" HTML blocks.
- Keep one compact guide popover per page.
- Use short captions near specific controls only where needed.
- Remove stray literal periods after closing HTML blocks.

**Files:**
- `home_page.py`
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- optionally `pages/3_Cancer_Trends.py`
- `pages/5_AI_Research_Assistant.py`

**Acceptance Criteria:**
- Page heading, short subtitle, and main controls/data appear higher on the screen.
- No stray punctuation appears after custom HTML blocks.
- Help remains available through popovers or concise captions.

## 4. Reposition the AI Assistant on Analysis Pages

**Issue:** Population, Deprivation, and Cancer pages reserve about 30% of the horizontal space for the AI assistant widget.

**Impact:** Dense charts and tables have less room, which can hurt readability, especially for long district labels and multi-series comparisons.

**Recommendation:**
- Move the assistant widget into an expander, popover, sidebar section, or dedicated Research Assistant page.
- On analysis pages, make the main visualization area full-width by default.
- Consider an "Ask about this view" action near charts that sends context to the Research Assistant page.

**Files:**
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- `pages/3_Cancer_Trends.py`
- `pages/5_AI_Research_Assistant.py`

**Acceptance Criteria:**
- Main analysis pages use the full available width for tabs, charts, and data tables.
- AI remains accessible but no longer dominates every analysis page.
- Chat history behavior is clear if shared across pages.

## 5. Make Dark Mode Complete or Remove It Temporarily

**Issue:** Global dark-mode tokens exist, but many inline HTML blocks and Plotly layouts use hardcoded light colors.

**Impact:** Dark mode can produce mixed light/dark surfaces and inconsistent readability.

**Recommendation:**
- Either remove the dark-mode toggle until fully supported, or complete theme coverage.
- Convert hardcoded inline colors to CSS variables.
- Add a dark Plotly layout or generate Plotly layout from current theme state.
- Check alert, metric, dataframe, chat, and insight panels in dark mode.

**Files:**
- `app.py`
- `visualizer.py`
- `gemini_queries.py`
- `home_page.py`
- page modules with inline HTML

**Acceptance Criteria:**
- Dark mode has no obvious light-only panels.
- Plotly chart text, gridlines, legends, and backgrounds remain readable.
- Inline custom HTML inherits theme tokens.

## 6. Standardize Page Headers and Layout Helpers

**Issue:** Page titles and subtitles are repeated as inline HTML across modules.

**Impact:** Styling changes require editing multiple files, and small inconsistencies accumulate.

**Recommendation:**
- Add shared helper functions for page headers, subtitles, guide popovers, and section headings.
- Prefer Streamlit-native `st.title`, `st.caption`, and `st.markdown` where possible.
- Use custom HTML only for design elements that Streamlit cannot express cleanly.

**Files:**
- new helper module, for example `utils/ui.py`
- `home_page.py`
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- `pages/3_Cancer_Trends.py`
- `pages/5_AI_Research_Assistant.py`

**Acceptance Criteria:**
- Page header style is defined in one place.
- Changing title size or subtitle spacing requires one edit.
- Inline HTML volume is reduced.

## 7. Rename Tabs Around User Tasks

**Issue:** Some tab labels mix concepts, data types, and implementation terms.

**Impact:** Users may need to inspect several tabs before finding the workflow they need.

**Recommendation:**
- Use task-oriented names:
  - `Compare Districts`
  - `Explore One Metric`
  - `Regional Patterns`
  - `Demographics vs Cancer`
  - `Demographics vs Deprivation`
  - `Raw Data`
- Keep naming consistent across Population, Deprivation, and Cancer pages.

**Files:**
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- `pages/3_Cancer_Trends.py`

**Acceptance Criteria:**
- Tab names describe what the user does, not just the dataset category.
- Similar workflows have similar names across pages.
- Labels remain short enough for narrower screens.

## 8. Add Active Context Summaries

**Issue:** Analytical pages often have several selected controls: year, districts, metric, chart type, sort order, and filters.

**Impact:** Users can lose track of the current analytical context while scrolling.

**Recommendation:**
- Add a compact context line above charts, such as:
  - `2022 | 5 districts | Lung cancer rate | Sorted highest first`
  - `Proportional view | Asian group | Top 15 districts`
- Use understated captions or small pill-style labels.

**Files:**
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- `pages/3_Cancer_Trends.py`

**Acceptance Criteria:**
- Each major chart clearly communicates the active filters and comparison mode.
- Context summaries do not add large vertical space.

## 9. Improve Chart Readability for Dense Comparisons

**Issue:** Many charts include long district names, rotated labels, and multi-series comparisons.

**Impact:** On smaller screens or narrower columns, labels can be hard to scan.

**Recommendation:**
- Prefer horizontal bar charts for ranked district comparisons.
- Limit default district count to a readable number.
- Add controls for "Top N" where all-district charts would be crowded.
- Keep legends outside the plotting area when possible.
- Standardize chart heights by chart type.

**Files:**
- `visualizer.py`
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- `pages/3_Cancer_Trends.py`

**Acceptance Criteria:**
- District labels are readable without excessive rotation.
- Default views are useful before the user changes controls.
- Charts avoid cramped legends and overlapping labels.

## 10. Clarify Data Tables as Secondary Detail

**Issue:** Many tabs pair charts with full or large dataframes immediately below.

**Impact:** Pages can feel long and technical, especially for users who primarily want visual insight.

**Recommendation:**
- Put large tables in `Raw Data` tabs or collapsed expanders.
- Keep small comparison tables visible when they directly support the chart.
- Add row counts and concise labels for table purpose.

**Files:**
- `home_page.py`
- `pages/1_Population_Demographics.py`
- `pages/2_Deprivation_Analysis.py`
- `pages/3_Cancer_Trends.py`
- `pages/5_AI_Research_Assistant.py`

**Acceptance Criteria:**
- Primary tabs lead with charts and interpretation.
- Large tables are available but do not dominate first-pass analysis.

## 11. Fix Encoding/Mojibake Display Risk

**Issue:** Source output shows mojibake-like strings for icons and punctuation in multiple files.

**Impact:** If the runtime renders these literally, users will see corrupted icons and text.

**Recommendation:**
- Audit UI strings in the browser.
- Replace corrupted emoji/punctuation strings with plain text or verified UTF-8.
- Prefer text labels over decorative emoji where clarity matters.

**Files:**
- `app.py`
- `home_page.py`
- all `pages/*.py`
- `visualizer.py`
- `map_fragment.py`

**Acceptance Criteria:**
- No visible strings such as `ðŸ`, `â€”`, `âœ`, or `Ã—` appear in the app.
- Important labels are readable without relying on emoji.

## Suggested Implementation Order

1. Remove global column card styling.
2. Remove visible instruction blocks and stray punctuation.
3. Simplify navigation labels and home-page topic behavior.
4. Move or collapse the AI assistant widget on analysis pages.
5. Centralize page header/UI helpers.
6. Rename tabs around user tasks.
7. Add active context summaries.
8. Improve dense chart defaults.
9. Move large tables into raw-data sections or expanders.
10. Finish or remove dark mode.
11. Audit browser-rendered text for encoding issues.

## UX Acceptance Criteria

- First viewport on each page shows the main workflow, not a wall of instructions.
- Navigation has one obvious hierarchy.
- Analysis charts have enough horizontal space to be readable.
- Visual cards are used intentionally, not as a side effect of layout columns.
- Dark mode is either consistently usable or not presented as an option.
- Tab labels and chart context make it clear what the user is looking at.
- Large data tables are available without overwhelming the main analytical flow.
