"""Helpers for turning Read Store ORM rows into JSON-serializable dicts.

The cache stores plain JSON, so loaders return lists of dicts (not ORM objects).
"""

from __future__ import annotations

from typing import Any


def row_to_dict(obj: Any) -> dict[str, Any]:
    """Serialize a SQLAlchemy ORM instance to a plain dict (drops internals)."""
    data = dict(obj.__dict__)
    data.pop("_sa_instance_state", None)
    return data
