"""A size-capped, TTL'd, in-memory cache. Nothing here ever touches disk.

This is where post enrichment lives, and the fact that it is *only* here is a
design decision, not an optimisation (ADR 0005). The cache exists to spare
BookWyrm instances repeat fetches for the same post. It does not exist to
accumulate a corpus of other people's reading, so it is deliberately volatile:
a restart empties it, which is the correct behaviour.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, max_size: int, ttl: float) -> None:
        self._max_size = max(1, max_size)
        self._ttl = ttl
        self._items: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.monotonic():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return value

    def put(self, key: str, value: T) -> None:
        self._items[key] = (time.monotonic() + self._ttl, value)
        self._items.move_to_end(key)
        while len(self._items) > self._max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def stats(self) -> dict[str, Any]:
        """Sizes only — never keys. The keys are post URIs."""
        return {"entries": len(self._items), "max": self._max_size, "ttl": self._ttl}
