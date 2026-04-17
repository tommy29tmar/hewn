"""Thin read-only helpers over the existing profile JSON format.

Profiles are produced by evals/suggest_profile.py and consumed by
evals/build_routed_run.py / integrations/claude-code/render_claude_md.py.
This module does not duplicate those semantics — it is a small inspector
that answers 'which variant does this profile recommend for (task_id,
category)?' and nothing more.

Profile schema (as emitted by calibration): {
    "name": ..., "objective": ..., "granularity": ...,
    "categories": {<category>: <variant_name>, ...},
    "tasks": {<task_id>: <variant_name>, ...},
    ...
}

Either 'categories' or 'tasks' (or both) may be present. pick_variant
resolves task_id override first, then category fallback. No default
argument — callers apply their own default.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_profile(path: Path) -> dict[str, Any]:
    """Load a profile JSON file and perform minimal shape validation.

    Raises ValueError if the profile has neither 'categories' nor 'tasks',
    or if either is present with a non-dict value.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"profile {path}: top-level must be an object")
    cats = data.get("categories")
    tasks = data.get("tasks")
    if cats is not None and not isinstance(cats, dict):
        raise ValueError(f"profile {path}: 'categories' must be object or absent")
    if tasks is not None and not isinstance(tasks, dict):
        raise ValueError(f"profile {path}: 'tasks' must be object or absent")
    if not cats and not tasks:
        raise ValueError(
            f"profile {path}: at least one of 'categories' or 'tasks' must be non-empty"
        )
    return data


def pick_variant(
    profile: dict[str, Any],
    *,
    task_id: str | None = None,
    category: str | None = None,
) -> str | None:
    """Return the variant name recommended by the profile, or None.

    Task override wins over category fallback. No default-fallback arg —
    the caller applies their own.
    """
    tasks = profile.get("tasks") or {}
    if task_id is not None and task_id in tasks:
        return str(tasks[task_id])
    categories = profile.get("categories") or {}
    if category is not None and category in categories:
        return str(categories[category])
    return None
