from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import backend.app as app_module


class CounterDB:
    def __init__(self, value: int) -> None:
        self.value = value

    def count_items(self, *_args, **_kwargs) -> int:
        return self.value


class EmptyDB:
    pass


def test_pagination_payload_includes_navigation_offsets() -> None:
    payload = app_module._pagination_payload(limit=5, offset=10, count=5, total=23)

    assert payload == {
        "limit": 5,
        "offset": 10,
        "count": 5,
        "total": 23,
        "hasMore": True,
        "nextOffset": 15,
        "prevOffset": 5,
    }


def test_pagination_payload_handles_first_page_without_limit() -> None:
    payload = app_module._pagination_payload(limit=None, offset=None, count=3, total=3)

    assert payload == {
        "limit": None,
        "offset": 0,
        "count": 3,
        "total": 3,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": None,
    }


def test_count_with_fallback_prefers_database_counter() -> None:
    db = CounterDB(value=41)

    total = app_module._count_with_fallback(
        db,
        "count_items",
        [{"id": 1}],
        "arg-1",
        key="value",
        fallback_counter=lambda: 99,
    )

    assert total == 41


def test_count_with_fallback_uses_fallback_counter_when_missing() -> None:
    db = EmptyDB()

    total = app_module._count_with_fallback(
        db,
        "count_items",
        [{"id": 1}],
        fallback_counter=lambda: 8,
    )

    assert total == 8


def test_count_with_fallback_uses_row_count_as_last_resort() -> None:
    db = EmptyDB()

    total = app_module._count_with_fallback(
        db,
        "count_items",
        [{"id": 1}, {"id": 2}, {"id": 3}],
    )

    assert total == 3


def test_pagination_payload_handles_empty_page_with_offset() -> None:
    payload = app_module._pagination_payload(limit=None, offset=6, count=0, total=6)

    assert payload == {
        "limit": None,
        "offset": 6,
        "count": 0,
        "total": 6,
        "hasMore": False,
        "nextOffset": None,
        "prevOffset": 5,
    }
