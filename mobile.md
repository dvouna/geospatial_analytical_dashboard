# Mobile & Responsive UX Enhancement Plan
## Cancer Health Dashboard — East of England

---

## ✅ Confirmed Design Decisions

| # | Decision | Choice Made |
|---|---|---|
| 1 | Mobile navigation | `st.selectbox` dropdown replaces the 7-column button bar |
| 2 | Map on mobile | Shown at **reduced height (350px)** — not hidden |
| 3 | AI Research Assistant on analytics pages | **Removed from analytics sidebars** — only on its dedicated page |
| 4 | KPI cards on mobile | **Keep 2-column layout** — touch targets improved via CSS |

---

## 📐 Breakpoint Reference

| Zone | Range | Typical Device |
|---|---|---|
| **Mobile** | `< 640px` | Phones — portrait |
| **Tablet** | `640px – 1023px` | Tablets, landscape phones, small laptops |
| **Desktop** | `≥ 1024px` | Laptops, monitors |

---

## 🔍 Diagnosed Pain Points

### Critical (content fails to render)

| # | Issue | File | Impact |
|---|---|---|---|
| 1 | `padding-left/right: 14rem` crushes content to 0px on 360px screens | `app.py` L122–128 | All pages |
| 2 | 7-column nav stacks to 7 full-height buttons before content | `app.py` L373 | All pages |
| 3 | 620px Folium map hijacks iOS scroll gestures | `map_fragment.py` L187 | Districts Profile |

### High

| # | Issue | File | Impact |
|---|---|---|---|
| 4 | `[7, 3]` column split renders AI widget in 30%-wide unreadable sidebar | 3 analytics pages | Pop, Dep, Cancer |
| 5 | `[1, 1]` choropleth selectors too narrow to tap on mobile | `map_fragment.py` L133–157 | Districts Profile |

### Medium

| # | Issue | File | Impact |
|---|---|---|---|
| 6 | All font sizes hardcoded — no responsive scaling | `app.py`, all pages | All pages |
| 7 | 12 duplicate inline `style=""` font blocks across 6 page files | All page files | All pages |
| 8 | Dark mode toggle only accessible by scrolling to page bottom | `app.py` footer | All pages, mobile |
| 9 | No URL state — links always land on Home page | `app.py` | All pages |
| 10 | Example queries block chat input on mobile | `5_AI_Research_Assistant.py` | RA page |

### Low / Enhancement

| # | Issue | File | Impact |
|---|---|---|---|
| 11 | Plotly modebar visible on touch screens (mouse-only feature) | All analytics pages | Analytics pages |
| 12 | Wide ethnic composition table requires excessive horizontal scrolling | `Districts_Profile.py` | Districts Profile |
| 13 | Large population table renders unconditionally (50 rows) | `Districts_Profile.py` | Districts Profile |
| 14 | iOS Safari keyboard pushes `st.chat_input` off-screen | `5_AI_Research_Assistant.py` | RA page, iOS |

---

## 🏗️ Device Detection Strategy

Two complementary layers — neither alone is sufficient:

### A. Python User-Agent Detection (structural branching)
Used to switch Streamlit **component structure** (columns → selectbox, map height).
Runs server-side before the page renders — no layout shift.

```python
# utils/device.py

def is_mobile_device() -> bool:
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            ua = headers.get("User-Agent", "").lower()
            return any(k in ua for k in ["mobile", "android", "iphone", "ipad", "phone"])
    except Exception:
        pass
    return False

def get_is_mobile() -> bool:
    """Session-cached wrapper — avoids header lookup on every rerun."""
    if "is_mobile" not in st.session_state:
        st.session_state["is_mobile"] = is_mobile_device()
    return st.session_state["is_mobile"]
```

> **Note:** Uses `streamlit.web.server.websocket_headers._get_websocket_headers` — an
> internal API stable across Streamlit 1.30–1.50. The `try/except` fallback defaults
> to desktop if the API ever changes.

### B. CSS Media Queries (visual styling)
Used for **font sizes, spacing, touch targets, and animations**. No Python logic needed.

---

## 📋 Implementation Steps

---

# Phase 1 — Critical Layout Fixes
*Makes the dashboard usable on mobile. Ship this first.*

---

### Step 1 — Create `utils/device.py`
New shared utility exposing `is_mobile_device()` and `get_is_mobile()`.
See detection strategy above for full code.

**Files:** `utils/device.py` *(new)*

---

### Step 2 — Fix Global Block-Container Padding
Replace `padding-left/right: 14rem` with media-query scoped rules.
Single highest-impact change — without it, all content is invisible on mobile.

```diff
- .block-container { padding-left: 14rem !important; padding-right: 14rem !important; }
+ .block-container { padding-top: 1.5rem !important; padding-bottom: 4rem !important; max-width: 100% !important; }
+ @media (min-width: 768px) { .block-container { padding-left: 14rem !important; padding-right: 14rem !important; } }
+ @media (max-width: 767px) { .block-container { padding-left: 1rem !important; padding-right: 1rem !important; } }
```

**Files:** `app.py`

---

### Step 3 — Adaptive Navigation (Selectbox on Mobile)
Branch the navigation render on `get_is_mobile()`:
- **Desktop:** unchanged 7-column `st.columns([6, 17, 23, 20, 13, 16, 18])` button bar.
- **Mobile:** full-width `st.selectbox` with page keys as options.

```python
if get_is_mobile():
    selected = st.selectbox("Navigate", list(PAGES_CONFIG.keys()),
                            index=..., key="mobile_nav_select",
                            label_visibility="collapsed")
    if selected != st.session_state["current_page"]:
        st.session_state["current_page"] = selected
        st.rerun()
else:
    # existing cols = st.columns([6, 17, 23, 20, 13, 16, 18]) block
    ...
```

**Files:** `app.py`

---

### Step 4 — Responsive Map Height + Scroll Fix
Reduce map height on mobile and disable scroll-wheel zoom.

```python
# map_fragment.py
map_height = 350 if get_is_mobile() else 620
map_output = render_map_st_folium(m, width="100%", height=map_height, ...)
```

```python
# map_utils.py — create_folium_map()
scrollWheelZoom = not get_is_mobile()  # False on mobile
```

**Files:** `map_fragment.py`, `map_utils.py`

---

### Step 5 — Single-Column Choropleth Selectors on Mobile
Stack the district + metric dropdowns vertically on mobile; keep side-by-side on desktop.

```python
if get_is_mobile():
    selected_display = st.selectbox("Select an authority:", ...)
    selected_metric_label = st.selectbox("Color map by metric:", ...)
else:
    col_sel1, col_sel2 = st.columns([1, 1])
    with col_sel1: selected_display = st.selectbox(...)
    with col_sel2: selected_metric_label = st.selectbox(...)
```

**Files:** `map_fragment.py`

---

### Step 6 — Remove AI Widget from Analytics Page Sidebars
The widget is removed from all three analytics pages **on all viewports**. No device
detection needed — this is a clean simplification. The Research Assistant remains fully
available on its own dedicated page.

- **`pages/1_Population_Demographics.py` (line 196):** Remove `col_main, col_sidebar = st.columns([7, 3])`, delete `with col_sidebar:` block, unwrap `with col_main:`.
- **`pages/2_Deprivation_Analysis.py` (line 159):** Same. Remove sidebar block (lines 161–166), unwrap from line 168.
- **`pages/3_Cancer_Trends.py` (line 210):** Same. Remove sidebar block (lines 212–217), unwrap from line 219.

**Files:** `pages/1_Population_Demographics.py`, `pages/2_Deprivation_Analysis.py`, `pages/3_Cancer_Trends.py`

---

### Step 7 — Mobile CSS Polish
Add to `app.py` `_CSS` block:

```css
@media (max-width: 767px) {
    /* WCAG 2.5.5 — minimum 44×44px touch targets */
    div[data-testid="column"] button, div.stColumn button {
        padding: 12px 8px !important;
        min-height: 44px !important;
    }
    /* Prevent Folium iframe from capturing iOS scroll gestures */
    .stIFrame { touch-action: pan-y !important; }
    /* KPI card touch padding */
    .kpi-card { padding: 14px 16px !important; }
}
```

KPI cards: 2-column layout is **preserved on all viewports**; touch targets addressed via padding above.

**Files:** `app.py`

---

# Phase 2 — Typography & Accessibility
*Zero visual change on desktop. Only mobile/tablet viewports see different sizes.*

---

### Step 8 — CSS Custom Property Type Scale
All `font-size` values are replaced with `--fs-*` CSS custom property tokens, defined
once in `:root` and overridden per breakpoint.

**Token table:**

| Token | Mobile `<640px` | Tablet `640–1023px` | Desktop `≥1024px` | Usage |
|---|---|---|---|---|
| `--fs-hero` | `1.5rem` | `2rem` | `2.5rem` | `.gradient-title` |
| `--fs-subtitle` | `0.875rem` | `0.95rem` | `1.05rem` | `.sub-title` |
| `--fs-page-title` | `1.15rem` | `1.3rem` | `1.4rem` | Per-page hero div |
| `--fs-body` | `0.9375rem` | `1rem` | `1rem` | Body paragraphs |
| `--fs-label` | `0.75rem` | `0.78rem` | `0.78rem` | KPI labels |
| `--fs-value` | `1.25rem` | `1.45rem` | `1.6rem` | KPI values |
| `--fs-badge` | `0.7rem` | `0.72rem` | `0.72rem` | KPI badges |
| `--fs-tab` | `0.78rem` | `0.84rem` | `0.88rem` | Tab labels |
| `--fs-radio` | `0.875rem` | `0.9rem` | `0.9rem` | Radio labels |
| `--fs-mono` | `0.8125rem` | `0.875rem` | `0.875rem` | Code / mono |

Desktop values **exactly match the current hardcoded sizes** — zero regression risk.

Implementation adds:
1. `--fs-*` tokens in both `:root` blocks (light + dark theme vars) with desktop defaults.
2. `@media (max-width: 1023px)` tablet override block.
3. `@media (max-width: 639px)` mobile override block.
4. Replace all hardcoded `font-size` literals in `_CSS` with `var(--fs-*)` references.

**Files:** `app.py`

---

### Step 9 — Shared `.page-title` / `.page-body` CSS Classes
All 6 page files contain **12 duplicate inline `style=""` HTML blocks** for the hero
title and body paragraph. These are replaced by two shared CSS classes in `app.py`:

```css
.page-title {
    font-family: 'Inter', sans-serif;
    font-size: var(--fs-page-title);
    font-weight: 700;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #1F77B4 0%, #6941C6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.15;
}
.page-body {
    font-family: 'Inter', sans-serif;
    font-size: var(--fs-body);
    color: var(--color-text-muted, #64748B);
    font-weight: 400;
}
```

Each page's inline div becomes: `<div class="page-title">...</div>`

**Files:** `app.py` (class definitions) + `home_page.py` (L27–56) +
`pages/Districts_Profile.py` (L439–469) + `pages/1_Population_Demographics.py` (L124–169) +
`pages/2_Deprivation_Analysis.py` (L75–113) + `pages/3_Cancer_Trends.py` (L117–159) +
`pages/5_AI_Research_Assistant.py` (L285–315)

---

### Step 10 — Accessibility: Colour Contrast & Reduced Motion
Two accessibility fixes added to the `app.py` `_CSS` block:

**a) Colour contrast for small text on mobile:**
`#64748B` and `#94A3B8` fail WCAG AA (4.5:1) at the reduced `0.75rem` / `0.7rem`
sizes used on mobile. Darken within the mobile breakpoint:

```css
@media (max-width: 639px) {
    :root {
        --color-text-muted:   #475569;  /* 5.9:1 on white — WCAG AA ✓ */
        --color-text-subtle:  #64748B;  /* 4.6:1 on white — WCAG AA ✓ */
    }
}
```

**b) `prefers-reduced-motion` — disable KPI card animations:**
```css
@media (prefers-reduced-motion: reduce) {
    .kpi-card, .kpi-card:hover { transition: none !important; transform: none !important; }
    * { transition-duration: 0.01ms !important; }
}
```

**Files:** `app.py`

---

### Step 11 — Plotly Mobile Layout Dict *(Optional)*
Add `PLOTLY_MOBILE_LAYOUT` (reduced `px` sizes: `font.size=11`, tick `9px`) and a
`get_plotly_layout()` helper to `visualizer.py`. Pages switch from
`**PLOTLY_LIGHT_LAYOUT` to `**get_plotly_layout()`.

> Optional — `use_container_width=True` already scales chart width. Implement after
> real-device testing if tick label legibility is still a concern.

**Files:** `visualizer.py` + `1_Population_Demographics.py`, `2_Deprivation_Analysis.py`, `3_Cancer_Trends.py`

---

# Phase 3 — UX Enhancements
*Quality-of-life improvements. Each step is independently deployable.*

---

### Step 12 — Floating Dark Mode Toggle
**Problem:** Dark mode toggle is at the page bottom — users must scroll all the way down
to find it on mobile.

**Fix:** Replace the footer `st.toggle` with a CSS `position: fixed` floating pill button
in the bottom-right corner — always visible regardless of scroll position.

```css
.dark-mode-float {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 9999;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 999px;
    padding: 8px 16px;
    box-shadow: var(--shadow-md);
}
```

**Files:** `app.py`

---

### Step 13 — URL Deep Linking via `st.query_params`
**Problem:** Session state is ephemeral. Sharing a URL always navigates to the Home page.

**Fix:** Use Streamlit's stable `st.query_params` API (available since v1.38; installed
v1.50) to sync `current_page` and `active_fid` to and from the URL:

```python
# Read on first load
if "page" in st.query_params and "current_page" not in st.session_state:
    if st.query_params["page"] in PAGES_CONFIG:
        st.session_state["current_page"] = st.query_params["page"]

# Write on navigation
st.query_params["page"] = st.session_state["current_page"]
```

**Benefit:** Shareable links, browser back/forward, bookmarkable district views.

**Files:** `app.py`, `pages/Districts_Profile.py`

---

### Step 14 — OS-Level Auto Dark Mode (`prefers-color-scheme`)
**Problem:** Users must find and click the toggle to activate dark mode on first visit.

**Fix:** Inject a one-time JS snippet via `st.components.v1.html` that reads
`window.matchMedia("(prefers-color-scheme: dark)")` and writes `?os_theme=dark` to the URL
on first visit. `app.py` reads this param and initialises `st.session_state["theme"]`
accordingly. The user's manual toggle always overrides the OS preference.

> Triggers one reload on first visit for OS dark-mode users only. Subsequent reruns use
> session state with no reload.

**Files:** `app.py`

---

### Step 15 — Data Table UX Improvements
Three targeted changes to make dense tables more usable on mobile:

**a) Ethnic composition column reorder** (`Districts_Profile.py` L679):
Move `Subgroup` and `Percentage` to columns 1 and 2 — the most useful pair — so mobile
users see key data without horizontal scrolling.

**b) Population table wrapped in expander** (`Districts_Profile.py` L778):
Wrap `st.dataframe(pop_df.head(50), ...)` in `st.expander("📋 View All Authorities", expanded=False)`. Collapsed by default — content is accessible without dominating the page.

**c) Short column headers via `column_config`:**
Truncate verbose ethnic subgroup header strings for display without altering data.

**Files:** `pages/Districts_Profile.py`

---

### Step 16 — AI Research Assistant Mobile UX
Three targeted improvements to the Research Assistant page:

**a) Collapsible example queries:**
Wrap the 7 example queries in `st.expander("💡 Example questions", expanded=not get_is_mobile())`.
Collapsed by default on mobile; open on desktop — chat input is immediately visible on mobile.

**b) Cap full-page chat history height on mobile:**
Add `st.container(height=400)` around the history render loop when `get_is_mobile()` is True,
keeping the chat input visible without excessive scrolling.

**c) iOS Safari `dvh` keyboard fix (`app.py` CSS):**
```css
@supports (height: 100dvh) {
    [data-testid="stChatInput"] {
        bottom: env(keyboard-inset-height, 0px);
    }
}
```
Prevents the chat input from being pushed off-screen when the iOS virtual keyboard opens.

**Files:** `pages/5_AI_Research_Assistant.py`, `app.py`

---

### Step 17 — Plotly Chart Polish on Mobile *(Low priority)*
**a) Remove modebar on mobile:**
Add `config={"displayModeBar": False}` to all `st.plotly_chart()` calls when `get_is_mobile()`.
The zoom/pan/download toolbar is mouse-oriented and clutters the mobile view.

**b) Tighter margins on mobile:**
Pass `margin=dict(t=28, b=16, l=4, r=4)` when on mobile to maximise usable chart area.

**Files:** `pages/1_Population_Demographics.py`, `pages/2_Deprivation_Analysis.py`, `pages/3_Cancer_Trends.py`

---

## ✅ Verification Checklist

### Phase 1 — Critical Layout

| Test | Tool | Pass Criteria |
|---|---|---|
| Content visible on 360px | DevTools emulator | No horizontal scroll; text readable |
| Mobile nav selectbox | DevTools + iPhone UA override | Selectbox replaces 7-column bar |
| Map 350px on mobile | DevTools emulator | Map does not fill entire screen |
| Analytics pages — no AI sidebar | DevTools emulator (360px) | Single column, full width |
| Touch targets ≥ 44×44px | Chrome Accessibility panel | WCAG 2.5.5 pass |
| Scroll past map (iOS) | Real iOS Safari | Page scrolls; map does not pan |
| Desktop unchanged at 1280px | Desktop browser | 7 columns, 14rem padding, 620px map |
| Research Assistant standalone | Desktop + mobile | AI chat fully functional |

### Phase 2 — Typography & Accessibility

| Test | Tool | Pass Criteria |
|---|---|---|
| `.gradient-title` 1.5rem on mobile | DevTools emulator (360px) | No overflow; fits on screen |
| KPI value 1.25rem; label 0.75rem | DevTools emulator (360px) | No overlapping text |
| Tablet sizes at 768px | DevTools emulator (768px) | Hero 2rem; KPI value 1.45rem |
| Desktop sizes unchanged at 1280px | Desktop browser | Visually identical to baseline |
| `.page-title` gradient on all 6 pages | All pages — desktop + mobile | Gradient + correct colour |
| Small text contrast on mobile | Chrome Accessibility panel | ≥ 4.5:1 WCAG AA |
| Reduced motion respected | DevTools → Emulate `prefers-reduced-motion` | No KPI card animation |

### Phase 3 — UX Enhancements

| Test | Tool | Pass Criteria |
|---|---|---|
| Dark mode toggle visible while scrolling | Real mobile device | Floating button always in corner |
| Shared page URL navigates correctly | Browser (copy + paste URL) | Correct page loaded |
| District URL highlights correct area | Browser | Correct district + topic loaded |
| OS dark mode auto-detects | iOS Safari (Dark OS theme) | Dashboard opens in dark mode |
| Ethnic composition column order | DevTools emulator | Subgroup + Percentage first |
| Population table collapsed by default | Mobile browser | Expander closed on load |
| Example queries collapsed on mobile | Mobile browser | Chat input immediately visible |
| Chat input visible with iOS keyboard | Real iOS Safari | Input not obscured |
| Plotly toolbar absent on mobile | Mobile browser | No modebar visible |

---

## 📁 Files Modified Summary

### Phase 1

| File | Type | Change |
|---|---|---|
| `utils/device.py` | **New** | `is_mobile_device()` + `get_is_mobile()` |
| `app.py` | Modify | Responsive padding, adaptive nav, mobile CSS polish |
| `map_fragment.py` | Modify | 350/620px map height, single-column selectors |
| `map_utils.py` | Modify | `scrollWheelZoom=False` on mobile |
| `pages/1_Population_Demographics.py` | Modify | Remove `[7,3]` split + AI sidebar |
| `pages/2_Deprivation_Analysis.py` | Modify | Same |
| `pages/3_Cancer_Trends.py` | Modify | Same |
| `pages/Districts_Profile.py` | No change | KPI layout preserved; CSS touch targets via `app.py` |

### Phase 2

| File | Type | Change |
|---|---|---|
| `app.py` | Modify | `--fs-*` tokens; tablet/mobile overrides; `var()` replacements; `.page-title`/`.page-body`; contrast; `prefers-reduced-motion` |
| `home_page.py` | Modify | Inline style → `.page-title` / `.page-body` |
| `pages/Districts_Profile.py` | Modify | Same |
| `pages/1_Population_Demographics.py` | Modify | Same |
| `pages/2_Deprivation_Analysis.py` | Modify | Same |
| `pages/3_Cancer_Trends.py` | Modify | Same |
| `pages/5_AI_Research_Assistant.py` | Modify | Same |
| `visualizer.py` | Modify *(optional)* | `PLOTLY_MOBILE_LAYOUT` + `get_plotly_layout()` |

### Phase 3

| File | Type | Change |
|---|---|---|
| `app.py` | Modify | Floating dark mode toggle; `st.query_params` sync; OS dark mode JS; iOS `dvh` CSS |
| `pages/Districts_Profile.py` | Modify | Column reorder; table expander; `column_config` |
| `pages/5_AI_Research_Assistant.py` | Modify | Collapsible queries; mobile container height |
| `pages/1_Population_Demographics.py` | Modify | `displayModeBar: False`; tight mobile margins |
| `pages/2_Deprivation_Analysis.py` | Modify | Same |
| `pages/3_Cancer_Trends.py` | Modify | Same |

---

*Last updated: 2026-07-16 — Phase 4 desktop enhancements added (Steps 18–27)*

---

# Phase 4 — Desktop Enhancements
*For desktop users at 1280px+ and 1440px+ viewports. Independent of Phases 1–3.*

---

### Step 18 — Content Width Clamping for Ultra-Wide Screens
At 1920px+ the 14rem padding produces a 1248px content strip in empty space. At 2560px
(increasingly common) it is even narrower. Add a max-width centred column at `≥1440px`:

```css
@media (min-width: 1440px) {
    .block-container {
        max-width: 1400px !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
}
```

**Files:** `app.py`

---

### Step 19 — Taller Map on Large Desktop Screens
The 620px map looks short on 1440p monitors. Extend via a CSS override (avoids Python UA
complexity for a purely visual change):

```css
@media (min-width: 1440px) {
    .stIFrame { min-height: 740px !important; }
}
```

**Files:** `app.py` (CSS), `map_fragment.py` (document the three-tier height logic)

---

### Step 20 — Plotly Legends Outside Chart Area
The current legend floats *inside* the plot, obscuring data on multi-trace charts
(ethnic group breakdowns, cancer type comparisons). Reposition to the right:

```python
# visualizer.py — PLOTLY_LIGHT_LAYOUT
legend=dict(
    ...,
    xanchor="left", x=1.02,  # push right of the plot area
    y=1, yanchor="top",
),
margin=dict(t=48, b=32, l=16, r=120),  # was r=16 — give legend room
```

**Files:** `visualizer.py`

---

### Step 21 — CSV Data Export Buttons
There are **zero data export options** across the dashboard. Desktop users (NHS analysts,
researchers) need to take data into Excel or R. Add `st.download_button` next to the
relevant chart or table on each page:

| Page | What to Export |
|---|---|
| Districts Profile | Full district KPI dataset (population, IMD, cancer DSR) |
| Population Demographics | Active chart's filtered dataframe |
| Deprivation Analysis | IMD data for visible selection |
| Cancer Trends | Selected cancer type time-series |

**Files:** `pages/Districts_Profile.py`, `pages/1_Population_Demographics.py`,
`pages/2_Deprivation_Analysis.py`, `pages/3_Cancer_Trends.py`

---

### Step 22 — KPI Grid Expansion on Wide Screens
On 1440px+ screens the 2-column KPI grid wastes horizontal space. Expand to 4 columns
via a CSS grid override:

```css
@media (min-width: 1440px) {
    div[data-testid="stHorizontalBlock"]:has(.kpi-card) {
        display: grid !important;
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 1rem;
    }
}
```

**Files:** `app.py`

---

### Step 23 — Wider Map/Panel Split on Large Screens
Extend the Districts Profile map column from 60% to 65% at `≥1440px` for richer
choropleth detail without reducing the panel's usability:

```css
@media (min-width: 1440px) {
    section[data-testid="column"]:first-of-type {
        flex: 0 0 65% !important;
        max-width: 65% !important;
    }
}
```

**Files:** `app.py`

---

### Step 24 — Fullscreen Map Toggle
A toggle button above the Folium map collapses the detail panel so analysts can view
the choropleth at full container width:

```python
# pages/Districts_Profile.py
if st.button("🗖 Expand map" if not fullscreen else "⬜ Exit", key="map_fs_btn"):
    st.session_state["map_fullscreen"] = not st.session_state.get("map_fullscreen", False)
    st.rerun()

if st.session_state.get("map_fullscreen"):
    render_persistent_map(...)              # full width
else:
    col_map, col_panel = st.columns([6, 4])
    ...
```

**Files:** `pages/Districts_Profile.py`

---

### Step 25 — Metric Tooltips & Glossary
Desktop hover is reliable; users get no contextual help for DSR, IMD decile, or
confidence intervals. Three layers:

- **a) HTML `title` attribute** on KPI cards — native browser tooltip; zero JS.
- **b) `st.popover("ℹ️")` next to section headings** — floating panel with full metric definition (Streamlit 1.33+).
- **c) `st.expander("📖 Metric Glossary")` at page bottom** — single shared `GLOSSARY_MD` constant in `app.py`.

**Files:** `app.py` (glossary constant), `pages/Districts_Profile.py`,
`pages/1_Population_Demographics.py`, `pages/2_Deprivation_Analysis.py`,
`pages/3_Cancer_Trends.py`

---

### Step 26 — AI Research Assistant Two-Pane Desktop Layout
Full-width chat on desktop produces very long line lengths. A `[58, 42]` split gives:
- **Left:** Chat conversation + input
- **Right:** Context panel — district context, data sources, last retrieved stats, copy button

```python
if not get_is_mobile():
    col_chat, col_ctx = st.columns([58, 42])
    with col_chat: render_chat_interface()
    with col_ctx:  render_context_panel()
else:
    render_chat_interface()
```

**Files:** `pages/5_AI_Research_Assistant.py`

---

### Step 27 — Print Stylesheet
No `@media print` CSS exists. Printing from Chrome renders navigation, toolbars, and
Scrollbars alongside content. A minimal stylesheet produces clean output:

```css
@media print {
    .nav-container, [data-testid="stToolbar"],
    .dark-mode-float, .stButton { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    .kpi-card { break-inside: avoid; }
    .stIFrame { display: none !important; }  /* Folium can't print */
}
```

**Files:** `app.py`

---

## ✅ Verification Checklist (Phase 4)

| Test | Tool | Pass Criteria |
|---|---|---|
| Content centred at 1920px | Desktop at 1920px | Max 1400px; equal margins |
| Content centred at 2560px | Desktop at 2560px | Comfortable reading width |
| Map taller at 1440px | Desktop at 1440px | `min-height: 740px` on iframe |
| Plotly legends outside chart | Desktop browser | Legend doesn't overlap data |
| CSV download on Districts Profile | Desktop browser | Correct data; valid file |
| CSV download on analytics pages | Desktop browser | Filtered data exports |
| 4-col KPI grid at 1440px | Desktop at 1440px | 4 cards per row, not 2 |
| Wider map split at 1440px | Desktop at 1440px | Map ≈65% width |
| Fullscreen map toggle | Desktop browser | Map expands; panel hides |
| Exit fullscreen restores layout | Desktop browser | Panel reappears at 60% |
| KPI card tooltip on hover | Desktop browser | Tooltip after ~500ms |
| `st.popover` info button | Desktop browser | Opens with metric text |
| Glossary expander | All pages, desktop | Glossary accessible |
| AI chat two-pane on desktop | Desktop (1280px+) | Context panel alongside chat |
| Print preview — nav hidden | Chrome Print Preview | No nav or toolbars |
| Print preview — KPI cards clean | Chrome Print Preview | No page-break inside card |

---

## 📁 Files Modified Summary (Phase 4)

| File | Type | Change |
|---|---|---|
| `app.py` | Modify | Max-width 1400px at ≥1440px; taller map CSS; 4-col KPI grid; wider map split; print stylesheet |
| `visualizer.py` | Modify | Legend outside chart (`x=1.02`); right margin `r=120` |
| `map_fragment.py` | Modify | Three-tier height documented; 740px CSS for 1440px+ |
| `pages/Districts_Profile.py` | Modify | Fullscreen toggle; CSV export; KPI tooltips; popovers; glossary |
| `pages/1_Population_Demographics.py` | Modify | CSV export; glossary; `st.popover` headings |
| `pages/2_Deprivation_Analysis.py` | Modify | CSV export; glossary |
| `pages/3_Cancer_Trends.py` | Modify | CSV export; glossary |
| `pages/5_AI_Research_Assistant.py` | Modify | Two-pane desktop layout |
