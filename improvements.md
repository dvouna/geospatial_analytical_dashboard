# Project Improvement Ideas

These tasks go beyond immediate integration fixes and would make the project easier to maintain, test, and extend.

## Architecture

- [ ] Create one canonical page implementation per feature.
  - Remove or delegate duplicate root files such as `maps.py` and `cancer_incidence.py` if the `pages/` versions are the real Streamlit pages.

- [ ] Centralize shared map-page behavior in `map_utils.py`.
  - Candidates include tile config, base GeoJSON loading, authority option building, side-panel rendering, overlay validation, and table formatting.

- [ ] Add a reusable map page controller.
  - A helper such as `render_authority_map_page(config)` could handle selectbox, map, highlight, and side info consistently.
  - Individual pages would only supply title text, overlay path, and metric display logic.

## Data Quality

- [ ] Add schema validation for every CSV and GeoJSON input.
  - Required base columns should include `fid`, `LAD24CD`, and `LAD24NM`.
  - Page-specific overlays should validate their required metric columns before rendering.

- [ ] Add a data dictionary.
  - Document every dataset in `data/`, expected columns, join key, source, and consuming page.

- [ ] Normalize all join keys once.
  - Ensure every loader strips whitespace and casts `fid` values to string before joins and lookups.

## User Experience

- [ ] Curate side information panels.
  - Replace raw dictionary dumps with page-specific metrics, friendly labels, and number formatting.

- [ ] Add consistent empty and error states.
  - Missing overlay row, missing file, failed merge, and no selected authority should all have clear user-facing messages.

- [ ] Add a summary metrics strip above each map.
  - Examples: selected authority, key rate/rank/population, region average, and percentile or rank if available.

- [ ] Add download buttons for selected or filtered data.
  - Let users export the selected authority row or visible table.

## Reliability

- [ ] Add smoke tests for page imports.
  - Verify `app.py`, `map_utils.py`, and every file in `pages/` imports or compiles cleanly.

- [ ] Add unit tests for `map_utils.py`.
  - Cover `prepare_geojson_payload`, `merge_overlay`, join-key validation, and authority option building.

- [ ] Add small fixture datasets.
  - Use tiny GeoJSON and CSV fixtures so tests do not depend on large production data files.

## Maintainability

- [ ] Remove unused imports and dead functions across all pages.

- [ ] Add type hints to shared helpers.

- [ ] Add or expand project documentation.
  - Include how to run the app, expected data files, page structure, and troubleshooting steps.

- [ ] Add formatting and linting.
  - Use a tool such as `ruff` for unused imports, formatting, and basic code quality checks.

## Performance

- [ ] Cache overlay CSV loading consistently with `st.cache_data`.

- [ ] Avoid rebuilding lookup dictionaries repeatedly.
  - Build `id_to_props`, `option_to_id`, and overlay lookup dictionaries once per render.

- [ ] Consider simplifying large GeoJSON before rendering.
  - The base GeoJSON is large, so geometry simplification or a lighter layer could improve map responsiveness.

## Product Polish

- [ ] Decide whether authority selection should persist across pages.
  - If yes, use a clearly named global key.
  - If no, keep page-specific session keys.

- [ ] Add "About this data" sections to each page.
  - Include source, date, caveats, and metric definitions.

- [ ] Align page names across `app.py`, filenames, titles, and sidebar labels.
