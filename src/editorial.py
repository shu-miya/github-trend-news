"""Small, manually README-reviewed editorial dossiers for selected Trending repositories.

Unlike generic keyword rules, these claims were checked against the linked,
commit-pinned official README. Project fit is an editorial hypothesis, not an
official endorsement or tested integration. Unknown repositories get no dossier.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def _profiles() -> dict:
    path = Path(__file__).with_name("editorial_profiles.json")
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def reviewed_profile(full_name: str) -> dict | None:
    """Return a defensive copy so one period cannot mutate another period."""
    if not isinstance(full_name, str):
        return None
    profile = _profiles().get(full_name.casefold())
    return deepcopy(profile) if profile else None
