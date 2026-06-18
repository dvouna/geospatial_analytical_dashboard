# Shared Map Page Structure Template

This file defines the target structure for map-backed pages so Maps, Population, IMD, and Cancer Incidence use the same layout and interaction model.

## Target Layout

Each page should follow this structure:

1. Page title and short description.
2. Sidebar data source and map tile controls.
3. Data loading:
   - Load `data/base_gdf.geojson`.
   - Load the page-specific overlay CSV if needed.
   - Validate join keys before merging.
   - Merge overlay data by `fid`.
   - Prepare GeoJSON payload with stable feature IDs.
4. Selection model:
   - Build a list of local authority display names from GeoJSON properties.
   - Display a selectbox labelled `Select an authority:`.
   - The selected authority determines the selected `fid`.
5. Main layout:
   - Left/main column: selectbox above the map, then the map.
   - Right column: authority information box.
   - Optional data table below the map or below both columns.
6. Map behavior:
   - The selected authority from the selectbox is passed to `add_geojson_layer(..., selected_id=selected_fid)`.
   - The selected polygon is highlighted on the map.
7. Information box behavior:
   - The side information box reads the same selected `fid`.
   - It displays page-specific overlay metrics when available.
   - It falls back to base GeoJSON properties when overlay data is missing.
8. Optional map click behavior:
   - If map click-to-selectbox sync is kept, verify the selected event object contains a feature ID.
   - If it cannot reliably identify a feature, keep selectbox as the source of truth.

## Recommended Helper Shape

Shared helper functions should live in `map_utils.py` where practical:

- `load_base_gdf(data_dir: Path) -> gpd.GeoDataFrame`
- `get_tile_config(map_type: str) -> tuple[str, str | None]`
- `build_authority_options(geojson_payload: dict) -> tuple[list[str], dict[str, str], dict[str, dict]]`
- `display_props_as_kv(props: dict) -> None`
- `validate_join_keys(base_gdf, overlay_df, base_key="fid", overlay_key="fid") -> None`
- `load_and_merge_overlay(base_gdf, overlay_path, base_key="fid", overlay_key="fid")`

These helpers should keep each page focused on page-specific text and metrics.

## Page Skeleton

```python
def render_example_page():
    st.title("Page Title")
    st.subheader("Page subtitle")
    st.write("Short page description.")

    st.sidebar.header("Data Source")
    st.sidebar.write("**Page-specific data source**")

    map_type = st.sidebar.radio(
        "Map type:",
        ["Basic (OpenStreetMap)", "Light Streets (CartoDB)", "Satellite (ArcGIS)"],
        key="example_map_type",
        index=2,
    )
    tiles, attr = get_tile_config(map_type)

    gdf = load_base_gdf(DATA_DIR)
    overlay_df = load_overlay_dataframe(OVERLAY_PATH, index_col="fid")
    validate_join_keys(gdf, overlay_df, "fid", "fid")
    gdf = merge_overlay(gdf, overlay_df, base_key="fid", overlay_key="fid")

    center = compute_center(gdf)
    geojson_payload, id_field = prepare_geojson_payload(gdf)
    options, option_to_id, id_to_props = build_authority_options(geojson_payload)

    if "example_select_display" not in st.session_state:
        st.session_state["example_select_display"] = options[0] if options else None

    col_map, col_info = st.columns([9, 3], gap="medium")

    with col_map:
        selected_display = st.selectbox(
            "Select an authority:",
            options=options,
            key="example_select_display",
        )
        selected_fid = option_to_id.get(selected_display)

        m = create_folium_map(center=center, tiles=tiles, attr=attr)
        add_geojson_layer(m, geojson_payload, gdf.columns, selected_id=selected_fid)
        map_output = render_map_st_folium(
            m,
            width="100%",
            height=500,
            returned_objects=["last_object_clicked"],
        )

    with col_info:
        st.markdown("### Authority Information")
        props = id_to_props.get(str(selected_fid), {}) if selected_fid else {}
        if props:
            st.success(f"Active Selection: {props.get('LAD24NM', selected_fid)}")
            display_page_metrics(selected_fid, props, overlay_df)
        else:
            st.info("Pick an authority from the selector to display data.")
```

## Current Issues To Resolve

### `maps.py`

- The overall layout mostly matches the target structure.
- The selectbox currently uses `props.get(id_field)` for labels, which can show `fid` or code instead of `LAD24NM`.
- Root-level `maps.py` may not be the Streamlit page users open if `pages/maps.py` is the canonical page.
- Task: use the shared authority option helper and confirm whether `maps.py` or `pages/maps.py` is canonical.

### `pages/population.py`

- The bidirectional layout matches the target shape, but the page currently calls missing `load_base_gdf`.
- The non-bidirectional branch does not show the required selectbox/info-box structure.
- The selectbox uses shared session key `maps_select_display`.
- Task: add/import base loader, remove the alternate layout branch or make it use the same structure, and switch to `population_select_display`.

### `pages/imd.py`

- The default bidirectional layout mostly matches the target shape.
- Fallback info rendering calls undefined `_display_props_as_kv`.
- The non-bidirectional branch does not show the required selectbox.
- The selectbox uses shared session key `maps_select_display`.
- Task: add shared property-display helper, use one consistent layout, and switch to `imd_select_display`.

### `cancer_incidence.py`

- The current root-level file does not match the target structure.
- It has no selectbox.
- It does not pass `selected_id` into `add_geojson_layer`.
- The information box is click-only.
- Task: rebuild this page around the shared selectbox-driven structure and use `cancer_select_display`.

### `pages/cancer_incidence.py`

- The page version mostly matches the target shape in bidirectional mode.
- Fallback info rendering calls undefined `_display_props_as_kv`.
- The non-bidirectional branch does not show the required selectbox.
- The selectbox uses shared session key `maps_select_display`.
- Task: decide whether root `cancer_incidence.py` or `pages/cancer_incidence.py` is canonical, then apply the shared structure to the canonical file.

## Implementation Tasks

- [ ] Decide canonical page files for Maps and Cancer Incidence.
- [ ] Add shared helper functions to `map_utils.py`.
- [ ] Convert every map-backed page to the same selectbox-first layout.
- [ ] Use page-specific selectbox and map-type session keys.
- [ ] Ensure every page passes `selected_id` to `add_geojson_layer`.
- [ ] Ensure every side information box reads from the selected `fid`.
- [ ] Make overlay joins validate `fid` before merging.
- [ ] Replace silent overlay exceptions with visible Streamlit warnings/errors.
- [ ] Remove or simplify non-bidirectional branches so they do not drift from the required page structure.
- [ ] Verify map-click sync separately from selectbox-driven behavior.

## Acceptance Checks

- [ ] Each page has a visible `Select an authority:` selectbox.
- [ ] Changing the selectbox changes the highlighted polygon.
- [ ] Changing the selectbox changes the side information box.
- [ ] Missing overlay rows fall back to base authority properties.
- [ ] Missing overlay files produce a visible warning or error.
- [ ] Page selections do not leak across Maps, Population, IMD, and Cancer pages.
- [ ] The exposed Streamlit pages match the files being maintained.
