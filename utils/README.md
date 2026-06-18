utils — cross-cutting helpers

This package provides small, well-tested helper functions used across the
project's pages and utilities.

Modules
- `io.py` — CSV / JSON loaders and `normalize_id_column` for reliable joins.
- `paths.py` — helpers for deriving `project_root()` and `data_path()` so
  code is robust when modules are moved under `pages/`.

Examples

Load a CSV from the project's `data/` folder:

```python
from utils import load_csv, data_path
p = data_path() / "population_detail.csv"
df = load_csv(p, index_col="fid")
```

Normalize an overlay's id column before merging with a GeoDataFrame:

```python
from utils import normalize_id_column
overlay = normalize_id_column(overlay, col="fid")
```

Notes
- Keep these helpers small and focused. If a helper grows, consider moving
  it to a dedicated module under `utils/` or into `map_utils.py` if it's
  map-specific.
