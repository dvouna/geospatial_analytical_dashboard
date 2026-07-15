# Districts Profile Implementation Plan

This document details the tasks required to duplicate `home_page.py` into a new page called `Districts Profile`, place it in the expandable sidebar navigation, and adjust it for runtime execution.

## Proposed Steps

1. **Duplicate File**:
   - Duplicate `home_page.py` to `pages/Districts_Profile.py`.

2. **Adjust Path Reference**:
   - In `pages/Districts_Profile.py`, update `DATA_DIR` definition:
     - Old: `DATA_DIR = Path(__file__).parent / "data"`
     - New: `DATA_DIR = Path(__file__).parent.parent / "data"`

3. **Update Page Header**:
   - Update the text header inside `pages/Districts_Profile.py` to:
     `Cancer Health Dashboard — Districts Profile`

4. **Update Navigation Router**:
   - In `app.py`, update the `st.navigation` list to add the new page between "Home" and "Population Demographics":
     ```python
     st.Page("home_page.py", title="Home", icon="🏠", default=True),
     st.Page("pages/Districts_Profile.py", title="Districts Profile", icon="🏢"),
     st.Page("pages/1_Population_Demographics.py", title="Population Demographics", icon="👥"),
     ```

5. **Ethnic Composition Table under Map**:
   - In `pages/Districts_Profile.py`, under the map display (within the map column `col_map` under the map settings), if `active_topic == "Population"` and a district is active (`active_fid` is selected):
     - Display a table containing the ethnic composition of the district.
     - Rows represent the detailed ethnic subgroups (e.g. White British, Indian, African, etc.).
     - Columns represent **Count** and **Percentage** (percentage is relative to the district's Total Population).

6. **IMD Subdomains Table under Map**:
   - In `pages/Districts_Profile.py`, under the map display (within the map column `col_map` under the map settings), if `active_topic == "Index of Multiple Deprivation"` and a district is active (`active_fid` is selected):
     - Display a table containing the IMD subdomain details for the selected district.
     - Rows represent the various subdomains (e.g., Overall IMD, Income, Employment, Education & Skills, Health & Disability, Crime, Housing & Services, Living Environment, IDACI, IDAOPI).
     - Columns represent the scores: **Rank** and **Decile** (calculated as `ceil(Rank / 29.6)` based on 296 authorities in England).

7. **Cancer Incidence Table under Map**:
   - In `pages/Districts_Profile.py`, under the map display (within the map column `col_map` under the map settings), if `active_topic == "Cancer Incidence"` and a district is active (`active_fid` is selected):
     - Display a table containing the cancer profile details for the selected district.
     - Rows represent the cancer types (e.g., Overall Cancer Rate, Total Diagnosed Cases, and individual cancer types like Bladder, Blood, Bowel, Brain, Breast, Head & Neck, Kidney, Liver & Biliary, Lung, Ovarian, Pancreatic, Prostate, Skin, Uterine).
     - Columns represent the values (such as standard rate per 100,000 or absolute count for total cases).




## Verification

- Confirm that Streamlit runs without syntax or runtime errors.
- Verify in the browser that the new sidebar menu contains **Districts Profile** between **Home** and **Population Demographics**.
- Click the page to verify it loads all maps and elements correctly.
