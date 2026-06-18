# Integration Fix Tasks

## High Priority

- [x] Define or import `_display_props_as_kv` where fallback property display is used.
  - Affected files: `pages/cancer_incidence.py`, `pages/imd.py`.
  - Add a small helper that displays feature properties as a two-column key/value table, or move the shared helper into `map_utils.py` and import it.
  - Acceptance check: selecting an authority with no matching overlay row no longer raises `NameError`.

- [ ] Add or import `load_base_gdf` in `pages/population.py`.
  - `render_click_analytics_page` and `render_population_page` call `load_base_gdf`, but the function is not defined in the file.
  - Prefer moving the shared base loader into `map_utils.py` or adding a local cached loader that mirrors `pages/imd.py`.
  - Acceptance check: opening the Population page no longer raises `NameError: name 'load_base_gdf' is not defined`.

- [ ] Fix map click-to-authority selection across map-backed pages.
  - Affected files: `pages/cancer_incidence.py`, `pages/imd.py`, `pages/population.py`, `maps.py`.
  - Verify what `streamlit_folium` returns for GeoJSON feature clicks.
  - If `last_object_clicked` only returns coordinates, switch to a supported returned object such as feature click/hover data, or add a reliable feature-id lookup path.
  - Acceptance check: clicking a local authority updates the selectbox, highlights the clicked authority, and refreshes the information panel on each page.

## Medium Priority

- [ ] Replace silent overlay `except Exception` blocks with visible error handling.
  - Affected files: `pages/cancer_incidence.py`, `pages/imd.py`, `pages/population.py`, `maps.py`.
  - Catch `FileNotFoundError` separately where appropriate.
  - Show a warning or error when overlay files cannot be loaded or merged.
  - Include the exception message so data/schema problems are diagnosable.
  - Acceptance check: missing or malformed overlay data produces a clear Streamlit message instead of silently falling back.

- [ ] Validate join keys before calling `merge_overlay` on all pages.
  - Confirm `fid` exists in both `base_gdf.geojson` and each overlay CSV before merging.
  - Affected overlays: `overall_incidence.csv`, `iod_2025.csv`, `population_detail.csv`, and the overlay candidates in `maps.py`.
  - Stop with a clear message if either key is missing.
  - Acceptance check: schema changes fail clearly before the merge.

- [ ] Use page-specific Streamlit session keys for selectors and map controls.
  - Replace shared keys such as `maps_select_display` and repeated `map_type` with page-specific keys.
  - Suggested keys: `maps_select_display`, `population_select_display`, `imd_select_display`, `cancer_select_display`, `maps_map_type`, `population_map_type`, `imd_map_type`, `cancer_map_type`.
  - Acceptance check: selections on Maps, Population, IMD, and Cancer pages no longer overwrite each other.

- [ ] Decide whether `maps.py` or `pages/maps.py` is the canonical Maps page.
  - `app.py` relies on Streamlit's `pages/` discovery, so root-level `maps.py` is not discovered as a page unless imported elsewhere.
  - Reconcile duplicated map-page logic so fixes are applied to the version users actually open.
  - Acceptance check: there is one canonical Maps implementation, or duplicated files clearly delegate to shared helpers.

- [ ] Fix display-name construction in `maps.py`.
  - Current options are built from `props.get(id_field)`, which usually shows `fid`/code rather than `LAD24NM`.
  - Use the same display-name fallback pattern as the other pages: `LAD24NM`, `name`, `NAME`, `LA_Name`, then id.
  - Acceptance check: the Maps selectbox displays human-readable authority names.

## Low Priority

- [ ] Add `load_overlay_dataframe` and `merge_overlay` to `map_utils.__all__`.
  - Acceptance check: the public export list matches the helpers consumed by page modules.

- [ ] Move common base-map helpers into `map_utils.py`.
  - Candidates: `load_base_gdf`, display-name/option mapping, id-to-properties lookup, property key/value rendering, tile selection, and overlay join validation.
  - Acceptance check: map-backed pages share the same integration behavior without copy/pasted helper logic.

- [ ] Remove unused imports and dead code from map-backed pages.
  - Affected files: `pages/cancer_incidence.py`, `pages/imd.py`, `pages/population.py`, `maps.py`.
  - Candidates include unused imports such as `folium`, `json`, `geopandas`, `st_folium`, and unused loaders where they are not needed.
  - Acceptance check: lint/static analysis shows no unused imports in the reviewed files.

- [ ] Align `app.py` page list with actual pages.
  - Add Research Assistant to the displayed list, or intentionally omit it with a comment.
  - Acceptance check: the welcome page accurately reflects the available Streamlit pages.

- [ ] Replace deprecated rerun calls if needed.
  - Check whether the installed Streamlit version supports `st.experimental_rerun`; if not, use `st.rerun`.
  - Affected files include map-backed pages that sync selectbox state after map clicks.
  - Acceptance check: map-click sync reruns without deprecation warnings or runtime errors.

## Verification

- [ ] Run `python -m py_compile app.py map_utils.py maps.py pages/cancer_incidence.py pages/imd.py pages/population.py`.
- [ ] Run the Streamlit app and open the Cancer Incidence page.
- [ ] Open the IMD page.
- [ ] Open the Population page.
- [ ] Open the Maps page that is actually exposed through Streamlit navigation.
- [ ] Confirm the page loads with `overall_incidence.csv` present.
- [ ] Confirm the IMD page loads with `iod_2025.csv` present.
- [ ] Confirm the Population page loads with `population_detail.csv` present.
- [ ] Confirm fallback behavior when an overlay row is missing.
- [ ] Confirm map selection, selectbox selection, highlighting, and information table stay in sync on all map-backed pages.
