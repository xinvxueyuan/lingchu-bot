"""Tests for ``load_toml_dict_async`` and async helpers.

Covers ``load_toml_dict_async`` (parity with ``load_toml_dict_sync``),
``write_toml_dict_file_async`` round-trips, and the internal helpers
``_toml_loads_async`` / ``_toml_dumps_async`` / ``_deepcopy_async``.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiofiles
import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    TOMLFileReadError,
    load_toml_dict_async,
    load_toml_dict_sync,
    write_toml_dict_file_async,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store._helpers import (
    _deepcopy_async,
    _toml_dumps_async,
    _toml_loads_async,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# load_toml_dict_async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_async_reads_existing_dict(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("message_store_enabled = true\ncount = 42\n")

    loaded = await load_toml_dict_async(config_file)

    assert loaded == {"message_store_enabled": True, "count": 42}


@pytest.mark.asyncio
async def test_load_async_missing_file_returns_empty_default(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.toml"

    loaded = await load_toml_dict_async(missing)

    assert loaded == {}
    assert load_toml_dict_sync(missing) == loaded


@pytest.mark.asyncio
async def test_load_async_missing_file_returns_provided_default(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.toml"
    default: dict[str, Any] = {"fallback": True, "nested": {"a": 1}}

    loaded = await load_toml_dict_async(missing, default=default)

    assert loaded == default
    # Returned copy must be independent of the input default.
    loaded["fallback"] = False
    loaded["nested"]["a"] = 999
    assert default == {"fallback": True, "nested": {"a": 1}}


@pytest.mark.asyncio
async def test_load_async_missing_file_parity_with_sync(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.toml"
    default: dict[str, Any] = {"x": 1}

    async_result = await load_toml_dict_async(missing, default=default)
    sync_result = load_toml_dict_sync(missing, default=default)

    assert async_result == sync_result


@pytest.mark.asyncio
async def test_load_async_empty_file_returns_default(tmp_path: Path) -> None:
    empty = tmp_path / "empty.toml"
    async with aiofiles.open(empty, "w", encoding="utf-8") as f:
        await f.write("   \n  ")

    loaded = await load_toml_dict_async(empty, default={"keep": 1})

    assert loaded == {"keep": 1}
    assert loaded == load_toml_dict_sync(empty, default={"keep": 1})


@pytest.mark.asyncio
async def test_load_async_invalid_array_root_raises(tmp_path: Path) -> None:
    bad = tmp_path / "array.toml"
    async with aiofiles.open(bad, "w", encoding="utf-8") as f:
        await f.write("[1, 2, 3]")

    with pytest.raises(TOMLFileReadError):
        await load_toml_dict_async(bad)


@pytest.mark.asyncio
async def test_load_async_invalid_string_root_raises(tmp_path: Path) -> None:
    bad = tmp_path / "string.toml"
    async with aiofiles.open(bad, "w", encoding="utf-8") as f:
        await f.write('"just a string"')

    with pytest.raises(TOMLFileReadError):
        await load_toml_dict_async(bad)


@pytest.mark.asyncio
async def test_load_async_invalid_toml_raises_read_error(tmp_path: Path) -> None:
    broken = tmp_path / "broken.toml"
    async with aiofiles.open(broken, "w", encoding="utf-8") as f:
        await f.write("{invalid syntax")

    with pytest.raises(TOMLFileReadError):
        await load_toml_dict_async(broken)


@pytest.mark.asyncio
async def test_load_async_large_payload(tmp_path: Path) -> None:
    large = tmp_path / "large.toml"
    payload: dict[str, int] = {f"key_{i}": i for i in range(1000)}
    async with aiofiles.open(large, "w", encoding="utf-8") as f:
        await f.write(rtoml.dumps(payload))

    loaded = await load_toml_dict_async(large)

    assert loaded == payload
    assert len(loaded) == 1000


@pytest.mark.asyncio
async def test_load_async_merge_default(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("count = 42\n")

    loaded = await load_toml_dict_async(
        config_file,
        default={"count": 0, "enabled": True},
        merge_default=True,
    )

    assert loaded == {"count": 42, "enabled": True}
    assert loaded == load_toml_dict_sync(
        config_file, default={"count": 0, "enabled": True}, merge_default=True
    )


@pytest.mark.asyncio
async def test_load_async_concurrent_reads(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("a = 1\nb = 2\n")

    results = await asyncio.gather(
        load_toml_dict_async(config_file),
        load_toml_dict_async(config_file),
        load_toml_dict_async(config_file),
    )

    assert all(r == {"a": 1, "b": 2} for r in results)


@pytest.mark.asyncio
async def test_load_async_parity_with_sync_multiple_fixtures(
    tmp_path: Path,
) -> None:
    fixtures = [
        ("simple = true\n", None),
        ("a = 1\n[b]\nc = 2\n", None),
        ("# comment\nkept = 1\n", {"kept": 0}),
        ("x = 1\n", {"x": 0, "y": 2}),
    ]

    for content, default in fixtures:
        path = tmp_path / f"fixture_{abs(hash(content))}.toml"
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(content)

        async_result = await load_toml_dict_async(path, default=default)
        sync_result = load_toml_dict_sync(path, default=default)
        assert async_result == sync_result


# ---------------------------------------------------------------------------
# write_toml_dict_file_async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_async_overwrites_existing_content(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("old = true\n")

    await write_toml_dict_file_async(config_file, {"new": False})

    async with aiofiles.open(config_file, encoding="utf-8") as f:
        loaded = rtoml.loads(await f.read())
    assert loaded == {"new": False}
    assert "old" not in loaded


@pytest.mark.asyncio
async def test_write_async_creates_new_file(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "dir" / "config.toml"

    await write_toml_dict_file_async(nested, {"created": True})

    assert nested.exists()
    async with aiofiles.open(nested, encoding="utf-8") as f:
        assert rtoml.loads(await f.read()) == {"created": True}


@pytest.mark.asyncio
async def test_write_async_round_trip_with_load(tmp_path: Path) -> None:
    config_file = tmp_path / "round_trip.toml"
    payload: dict[str, Any] = {
        "string": "value",
        "number": 42,
        "nested": {"deep": [1, 2, 3]},
        "flag": True,
    }

    await write_toml_dict_file_async(config_file, payload)
    loaded = await load_toml_dict_async(config_file)

    assert loaded == payload


# ---------------------------------------------------------------------------
# _toml_loads_async / _toml_dumps_async / _deepcopy_async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toml_loads_async_parses_dict() -> None:
    content = "message_store_enabled = true\ncount = 42\n"

    loaded = await _toml_loads_async(content)

    assert loaded == {"message_store_enabled": True, "count": 42}
    assert loaded == rtoml.loads(content)


@pytest.mark.asyncio
async def test_toml_loads_async_rejects_non_document_array() -> None:
    with pytest.raises(ValueError):
        await _toml_loads_async("[1, 2, 3]")
    with pytest.raises(ValueError):
        await _toml_loads_async('"text"')
    with pytest.raises(ValueError):
        await _toml_loads_async("123")


@pytest.mark.asyncio
async def test_toml_dumps_async_serializes_dict() -> None:
    data: dict[str, Any] = {"a": 1, "b": True}

    dumped = await _toml_dumps_async(data)

    assert rtoml.loads(dumped) == data
    assert dumped == rtoml.dumps(data, pretty=True, none_value=None)


@pytest.mark.asyncio
async def test_toml_dumps_async_round_trip() -> None:
    data: dict[str, Any] = {"nested": {"list": [1, 2, 3]}, "value": "hello"}

    dumped = await _toml_dumps_async(data)
    loaded = await _toml_loads_async(dumped)

    assert loaded == data


@pytest.mark.asyncio
async def test_deepcopy_async_returns_independent_copy() -> None:
    original: dict[str, Any] = {"nested": {"a": 1}, "list": [1, 2, 3]}

    copied = await _deepcopy_async(original)

    assert copied == original
    assert copied is not original
    assert copied["nested"] is not original["nested"]
    assert copied["list"] is not original["list"]


@pytest.mark.asyncio
async def test_deepcopy_async_mutation_does_not_affect_original() -> None:
    original: dict[str, Any] = {"nested": {"a": 1}, "list": [1, 2]}

    copied = await _deepcopy_async(original)
    copied["nested"]["a"] = 999
    copied["list"].append(3)
    copied["new_key"] = True

    assert original == {"nested": {"a": 1}, "list": [1, 2]}
