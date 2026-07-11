from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

import pytest
import rtoml

from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import (
    RobustAsyncTOMLDB,
    TOMLSerializationError,
    write_toml_dict_file_async,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_write_omits_mapping_none_without_mutating_input(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    payload: dict[str, Any] = {
        "enabled": True,
        "optional": None,
        "nested": {"value": 1, "optional": None},
    }
    original = deepcopy(payload)

    await write_toml_dict_file_async(path, payload)

    assert payload == original
    assert rtoml.load(path) == {"enabled": True, "nested": {"value": 1}}


@pytest.mark.asyncio
async def test_write_rejects_none_inside_list(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"

    with pytest.raises(TOMLSerializationError, match="None inside a list"):
        await write_toml_dict_file_async(path, {"values": [1, None, 2]})

    assert not path.exists()


@pytest.mark.asyncio
async def test_write_prepends_schema_directive(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"

    await write_toml_dict_file_async(
        path,
        {"enabled": True},
        schema_basename="config.schema.json",
    )

    content = path.read_text(encoding="utf-8")
    assert content.startswith("#:schema ./config.schema.json\n")
    assert rtoml.loads(content) == {"enabled": True}


@pytest.mark.asyncio
async def test_set_none_deletes_mapping_key(tmp_path: Path) -> None:
    path = tmp_path / "state.toml"

    async with RobustAsyncTOMLDB(path, default={"optional": "value"}) as db:
        await db.set("optional", None)

    assert rtoml.load(path) == {}


@pytest.mark.asyncio
async def test_set_none_does_not_create_missing_parent_tables(tmp_path: Path) -> None:
    path = tmp_path / "state.toml"

    async with RobustAsyncTOMLDB(path) as db:
        await db.set("missing.optional", None)

    assert not path.exists()


@pytest.mark.asyncio
async def test_create_none_does_not_delete_existing_key(tmp_path: Path) -> None:
    path = tmp_path / "state.toml"

    async with RobustAsyncTOMLDB(path, default={"key": "value"}) as db:
        created = await db.create("key", None)
        assert await db.read("key") == "value"

    assert created is False
    assert not path.exists()


@pytest.mark.asyncio
async def test_set_batch_none_deletes_mapping_key(tmp_path: Path) -> None:
    path = tmp_path / "state.toml"

    async with RobustAsyncTOMLDB(path, default={"key": "value"}) as db:
        await db.set_batch({"key": None})
        assert await db.read("key", "missing") == "missing"

    assert rtoml.load(path) == {}
