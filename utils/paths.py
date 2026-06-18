"""Path helpers for locating project resources.

Helpers keep code robust when modules are moved (for example into `pages/`).
"""

from pathlib import Path


def project_root() -> Path:
    """Return the project root folder (two levels up from this file)."""
    return Path(__file__).resolve().parents[1]


def data_path() -> Path:
    """Return the canonical `data/` folder under the project root."""
    return project_root() / "data"


def resource_path(*parts) -> Path:
    """Return a path under the project root composed from `parts`.

    Usage: `resource_path('data', 'my.csv')`
    """
    return project_root().joinpath(*parts)
