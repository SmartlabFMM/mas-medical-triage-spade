"""
core/belief_base.py — BeliefBase BDI (inchangée, compatible SPADE).
"""
from __future__ import annotations
from datetime import datetime
from typing import Any


class BeliefBase:
    def __init__(self) -> None:
        self._beliefs: dict[str, Any] = {}
        self._history: list[dict] = []

    def update(self, key: str, value: Any) -> None:
        old = self._beliefs.get(key)
        self._beliefs[key] = value
        self._history.append({"timestamp": datetime.now().isoformat(),
                               "key": key, "old": old, "new": value})

    def get(self, key: str, default: Any = None) -> Any:
        return self._beliefs.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._beliefs

    def remove(self, key: str) -> None:
        self._beliefs.pop(key, None)

    def all(self) -> dict[str, Any]:
        return dict(self._beliefs)

    def revision_count(self) -> int:
        return len(self._history)

    def __repr__(self) -> str:
        return f"BeliefBase({list(self._beliefs.keys())})"
