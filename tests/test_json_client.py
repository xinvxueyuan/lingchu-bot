"""
单元测试：针对 RobustAsyncJSON5DB 异步 JSON5 数据库客户端。

覆盖初始化、加载/保存、CRUD、路径导航、错误处理、自动保存、
原子写入、文件监听、关闭及上下文管理器等核心功能。
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import aiofiles
import aiofiles.os
import json5
import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from _asyncio import Task
    from collections.abc import AsyncGenerator

from src.builtin_plugins.client.json_client import (
    AtomicReplacementError,
    CallbackTypeError,
    DatabaseClosedError,
    DatabaseError,
    EmptyPathSegmentError,
    IntermediateListNoneError,
    InvalidDefaultTypeError,
    InvalidKeyPathError,
    LoadStateMismatchError,
    LoadTaskCancelledError,
    RobustAsyncJSON5DB,
    TerminalPathResolutionError,
    WatchAlreadyRunningError,
)

# ruff: noqa: PLR2004

# ---------------------------------------------------------------------------
# Constants (to avoid magic number warnings)
# ---------------------------------------------------------------------------
DEFAULT_VALUE_42 = 42
DEFAULT_VALUE_10 = 10
DEFAULT_VALUE_20 = 20
DEFAULT_VALUE_3 = 3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def tmp_db_path() -> AsyncGenerator[Path]:
    """创建临时 JSON5 文件路径，并在测试后清理。"""
    fd, path = tempfile.mkstemp(suffix=".json5")
    os.close(fd)
    yield Path(path)
    # 清理可能残留的临时文件
    for p in [Path(path), Path(path).with_suffix(suffix=".tmp.json5")]:
        p.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def db(tmp_db_path: Path) -> AsyncGenerator[RobustAsyncJSON5DB]:
    """返回未加载的数据库实例。"""
    instance = RobustAsyncJSON5DB(file_path=tmp_db_path, auto_save=False)
    yield instance
    await instance.close()


@pytest_asyncio.fixture
async def loaded_db(tmp_db_path: Path) -> AsyncGenerator[RobustAsyncJSON5DB]:
    """返回已加载的数据库实例，自动关闭。"""
    instance = RobustAsyncJSON5DB(file_path=tmp_db_path, auto_save=False)
    await instance.load()
    yield instance
    await instance.close()


@pytest_asyncio.fixture
async def auto_save_db(tmp_db_path: Path) -> AsyncGenerator[RobustAsyncJSON5DB]:
    """返回启用自动保存的已加载数据库。"""
    instance = RobustAsyncJSON5DB(file_path=tmp_db_path, auto_save=True)
    await instance.load()
    yield instance
    await instance.close()


# ---------------------------------------------------------------------------
# 初始化测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_default_not_dict() -> None:
    """非 dict 的 default 应该抛出 InvalidDefaultTypeError。"""
    bad_default: Any = [1, 2, 3]
    with pytest.raises(expected_exception=InvalidDefaultTypeError):
        RobustAsyncJSON5DB(file_path="dummy.json5", default=bad_default)


@pytest.mark.asyncio
async def test_repr(loaded_db: RobustAsyncJSON5DB) -> None:
    """__repr__ 应该显示路径和状态。"""
    r = repr(loaded_db)
    assert "RobustAsyncJSON5DB" in r
    assert "loaded" in r


@pytest.mark.asyncio
async def test_is_closed(loaded_db: RobustAsyncJSON5DB) -> None:
    """is_closed 应正确反映关闭状态。"""
    assert not loaded_db.is_closed
    await loaded_db.close()
    assert loaded_db.is_closed


# ---------------------------------------------------------------------------
# 加载与基础读写
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_new_file(db: RobustAsyncJSON5DB) -> None:
    """文件不存在时应使用默认模板初始化。"""
    await db.load()
    data: Any = await db.read()
    assert data == {}


@pytest.mark.asyncio
async def test_load_with_default(tmp_db_path: Path) -> None:
    """提供 default 参数时，新文件应使用该模板。"""
    template: dict[str, Any] = {"count": 0, "tags": []}
    db = RobustAsyncJSON5DB(file_path=tmp_db_path, default=template)
    await db.load()
    data = await db.read()
    assert data == template


@pytest.mark.asyncio
async def test_load_existing_file(tmp_db_path: Path) -> None:
    """已有文件应正确加载 JSON5 内容。"""
    content: dict[str, str | int] = {"key": "value", "num": DEFAULT_VALUE_42}
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write(json5.dumps(obj=content))
    db = RobustAsyncJSON5DB(file_path=tmp_db_path)
    await db.load()
    data: Any = await db.read()
    assert data == content


@pytest.mark.asyncio
async def test_load_empty_file(tmp_db_path: Path) -> None:
    """空文件应回退到默认（空 dict）。"""
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write("   ")
    db = RobustAsyncJSON5DB(file_path=tmp_db_path, default={"hello": "world"})
    await db.load()
    data: Any = await db.read()
    assert data == {"hello": "world"}


@pytest.mark.asyncio
async def test_load_invalid_json(tmp_db_path: Path, caplog: Any) -> None:
    """无效 JSON 应回退默认并记录警告。"""
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write("{invalid")
    db = RobustAsyncJSON5DB(file_path=tmp_db_path, default={"fallback": True})
    await db.load()
    data: Any = await db.read()
    assert data == {"fallback": True}
    assert "Loading failed" in caplog.text


@pytest.mark.asyncio
async def test_load_non_dict_root(tmp_db_path: Path, caplog: Any) -> None:
    """根不是 dict 时应回退默认并警告。"""
    async with aiofiles.open(tmp_db_path, "w", encoding="utf-8") as f:
        await f.write("[1, 2, 3]")
    db = RobustAsyncJSON5DB(file_path=tmp_db_path, default={"ok": 1})
    await db.load()
    data: Any = await db.read()
    assert data == {"ok": 1}
    assert "Root is not a dict" in caplog.text


# ---------------------------------------------------------------------------
# 关闭与上下文管理器
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operations_after_close(loaded_db: RobustAsyncJSON5DB) -> None:
    """关闭后读写应抛 DatabaseClosedError。"""
    await loaded_db.close()
    with pytest.raises(expected_exception=DatabaseClosedError):
        await loaded_db.read()
    with pytest.raises(expected_exception=DatabaseClosedError):
        await loaded_db.set(key_path="x", value=1)


@pytest.mark.asyncio
async def test_async_context_manager(tmp_db_path: Path) -> None:
    """async with 应自动加载并在退出时保存（若 auto_save=False）。"""
    path: Path = tmp_db_path
    async with RobustAsyncJSON5DB(file_path=path, auto_save=False) as db:
        await db.set(key_path="k", value=100)
    # 退出后文件应包含数据
    async with aiofiles.open(file=path, encoding="utf-8") as f:
        saved = json5.loads(await f.read())
    assert saved == {"k": 100}


@pytest.mark.asyncio
async def test_context_manager_exception(tmp_db_path: Path) -> None:
    path: Path = tmp_db_path
    with pytest.raises(RuntimeError):
        async with RobustAsyncJSON5DB(file_path=path, auto_save=False) as db:
            await db.set(key_path="keep", value=1)
            raise RuntimeError("boom")
    # 文件原本存在（空），但内容不应包含 "keep"
    async with aiofiles.open(path, encoding="utf-8") as f:
        content = await f.read()
    assert "keep" not in content


# ---------------------------------------------------------------------------
# read / atomic_read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_root(loaded_db: RobustAsyncJSON5DB) -> None:
    """读取根对象。"""
    await loaded_db.set(key_path="a", value=1)
    data: Any = await loaded_db.read()
    assert data == {"a": 1}


@pytest.mark.asyncio
async def test_read_nested(loaded_db: RobustAsyncJSON5DB) -> None:
    """深层路径读取。"""
    await loaded_db.set(key_path="x.y.z", value="deep")
    val: Any = await loaded_db.read(key_path="x.y.z")
    assert val == "deep"


@pytest.mark.asyncio
async def test_read_default_value(loaded_db: RobustAsyncJSON5DB) -> None:
    """路径不存在时返回 default。"""
    val: Any = await loaded_db.read(key_path="no.such", default=DEFAULT_VALUE_42)
    assert val == DEFAULT_VALUE_42


@pytest.mark.asyncio
async def test_read_use_deepcopy(loaded_db: RobustAsyncJSON5DB) -> None:
    """use_deepcopy=True 时应返回独立副本。"""
    await loaded_db.set(key_path="mylist", value=[1, 2, 3])
    copy1: Any = await loaded_db.read(key_path="mylist")
    copy2: Any = await loaded_db.read(key_path="mylist")
    assert copy1 == [1, 2, 3]
    assert copy1 is not copy2


@pytest.mark.asyncio
async def test_atomic_read(loaded_db: RobustAsyncJSON5DB) -> None:
    """atomic_read 返回深拷贝且保持一致性。"""
    await loaded_db.set(key_path="deep", value={"nested": {"a": 1}})
    val: Any = await loaded_db.atomic_read(key_path="deep")
    assert val == {"nested": {"a": 1}}
    val["nested"]["a"] = 999
    orig: Any = await loaded_db.read(key_path="deep")
    assert orig["nested"]["a"] == 1


# ---------------------------------------------------------------------------
# set / create / update / delete / exists / clear
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_new_key(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="new.key", value="hi")
    assert await loaded_db.read(key_path="new.key") == "hi"


@pytest.mark.asyncio
async def test_set_overwrite(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="k", value=1)
    await loaded_db.set(key_path="k", value=2)
    assert await loaded_db.read(key_path="k") == 2


@pytest.mark.asyncio
async def test_create_success(loaded_db: RobustAsyncJSON5DB) -> None:
    result: bool = await loaded_db.create(key_path="alpha", value=DEFAULT_VALUE_10)
    assert result is True
    assert await loaded_db.read(key_path="alpha") == DEFAULT_VALUE_10


@pytest.mark.asyncio
async def test_create_already_exists(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="beta", value=DEFAULT_VALUE_20)
    result: bool = await loaded_db.create(key_path="beta", value=30)
    assert result is False
    assert await loaded_db.read(key_path="beta") == DEFAULT_VALUE_20


@pytest.mark.asyncio
async def test_update_existing(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="gamma", value=1)
    result: bool = await loaded_db.update(key_path="gamma", value=2)
    assert result is True
    assert await loaded_db.read(key_path="gamma") == 2


@pytest.mark.asyncio
async def test_update_nonexistent(loaded_db: RobustAsyncJSON5DB) -> None:
    result: bool = await loaded_db.update(key_path="delta", value=1)
    assert result is False


@pytest.mark.asyncio
async def test_delete(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="del.me", value="bye")
    result: bool = await loaded_db.delete(key_path="del.me")
    assert result is True
    assert not await loaded_db.exists(key_path="del.me")


@pytest.mark.asyncio
async def test_delete_nonexistent(loaded_db: RobustAsyncJSON5DB) -> None:
    result: bool = await loaded_db.delete(key_path="nope")
    assert result is False


@pytest.mark.asyncio
async def test_delete_list_shifts(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="items", value=["a", "b", "c"])
    await loaded_db.delete(key_path="items.1")
    lst: Any = await loaded_db.read(key_path="items")
    assert lst == ["a", "c"]


@pytest.mark.asyncio
async def test_exists(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="e.x", value=1)
    assert await loaded_db.exists(key_path="e.x") is True
    assert await loaded_db.exists(key_path="e.y") is False


@pytest.mark.asyncio
async def test_clear(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="x", value=1)
    await loaded_db.clear()
    assert await loaded_db.read() == {}


# ---------------------------------------------------------------------------
# set_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_batch(loaded_db: RobustAsyncJSON5DB) -> None:
    await loaded_db.set(key_path="a", value=0)
    updates: dict[str, int | list[int]] = {"b.c": 1, "d": [10, 20]}
    await loaded_db.set_batch(updates)
    assert await loaded_db.read(key_path="b.c") == 1
    assert await loaded_db.read(key_path="d") == [10, 20]
    assert await loaded_db.read(key_path="a") == 0  # 独立变更不受影响


@pytest.mark.asyncio
async def test_set_batch_empty(loaded_db: RobustAsyncJSON5DB) -> None:
    # 空批次不应出错
    await loaded_db.set_batch(updates={})
    assert await loaded_db.read() == {}


@pytest.mark.asyncio
async def test_set_batch_atomic(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """批量更新应原子性保存（auto_save=True 时）。"""
    await auto_save_db.set(key_path="x", value=1)
    # 提供非法路径之一，触发异常
    with pytest.raises(expected_exception=InvalidKeyPathError):
        await auto_save_db.set_batch(updates={"y": 2, "": DEFAULT_VALUE_3})  # 空路径段
    # 验证文件内容未被部分修改
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        content = json5.loads(await f.read())
    assert content == {"x": 1}


# ---------------------------------------------------------------------------
# 自动保存行为
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_save_writes_immediately(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    await auto_save_db.set(key_path="instant", value=1)
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        saved = json5.loads(await f.read())
    assert saved == {"instant": 1}


@pytest.mark.asyncio
async def test_no_auto_save(loaded_db: RobustAsyncJSON5DB, tmp_db_path: Path) -> None:
    """auto_save=False 时不立即写入文件。"""
    await loaded_db.set(key_path="later", value=1)
    # 还未保存，文件应该不变
    if await aiofiles.os.path.exists(tmp_db_path):
        async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
            content = await f.read()
        assert "later" not in content
    await loaded_db.save()
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        saved = json5.loads(await f.read())
    assert saved == {"later": 1}


# ---------------------------------------------------------------------------
# 路径导航：字典/列表混合、索引、错误场景
# ---------------------------------------------------------------------------


# 修复 test_path_through_list
@pytest.mark.asyncio
async def test_path_through_list(loaded_db: RobustAsyncJSON5DB) -> None:
    # 先创建列表，并手动放入一个空字典，作为后续下钻的容器
    await loaded_db.set("outer", [{}])
    await loaded_db.set(key_path="outer.0.name", value="Alice")
    assert await loaded_db.read(key_path="outer.0.name") == "Alice"
    data = await loaded_db.read()
    assert data == {"outer": [{"name": "Alice"}]}


@pytest.mark.asyncio
async def test_path_list_index_none_placeholder(loaded_db: RobustAsyncJSON5DB) -> None:
    """None 占位符不允许直接下钻为字典，应抛出 IntermediateListNoneError。"""
    # 先创建一个列表并在索引0存入 None
    await loaded_db.set(key_path="mylist", value=[None])
    with pytest.raises(expected_exception=IntermediateListNoneError):
        await loaded_db.set(key_path="mylist.0.key", value=1)  # 尝试在 None 上创建字典


@pytest.mark.asyncio
async def test_parent_path_resolution_error(loaded_db: RobustAsyncJSON5DB) -> None:
    """当父节点类型不匹配时抛出 TerminalPathResolutionError"""
    await loaded_db.set(key_path="val", value=DEFAULT_VALUE_42)
    with pytest.raises(expected_exception=TerminalPathResolutionError):
        await loaded_db.set(key_path="val.sub", value=1)  # val 是 int，无法下钻


@pytest.mark.asyncio
async def test_terminal_path_resolution_error(loaded_db: RobustAsyncJSON5DB) -> None:
    """目标容器不支持对应键时抛出 TerminalPathResolutionError。"""
    await loaded_db.set(key_path="lst", value=[1, 2])
    with pytest.raises(expected_exception=TerminalPathResolutionError):
        await loaded_db.set(key_path="lst.key", value=1)  # 列表上不能使用字符串键


@pytest.mark.asyncio
async def test_empty_path_segment() -> None:
    """空路径段抛出 EmptyPathSegmentError。"""
    db = RobustAsyncJSON5DB(file_path="dummy.json5")
    with pytest.raises(expected_exception=EmptyPathSegmentError):
        db._validate_path(key_path="a..b")


@pytest.mark.asyncio
async def test_invalid_key_path() -> None:
    """非字符串或空路径抛出 InvalidKeyPathError。"""
    db = RobustAsyncJSON5DB(file_path="dummy.json5")
    bad_path: Any = None
    with pytest.raises(expected_exception=InvalidKeyPathError):
        db._validate_path(key_path=bad_path)
    with pytest.raises(expected_exception=InvalidKeyPathError):
        db._validate_path(key_path="")


@pytest.mark.asyncio
async def test_read_nonexistent_list_index(loaded_db: RobustAsyncJSON5DB) -> None:
    """读取不存在的列表索引返回默认值。"""
    await loaded_db.set(key_path="arr", value=[10])
    val = await loaded_db.read(key_path="arr.5", default="missing")
    assert val == "missing"


# ---------------------------------------------------------------------------
# 保存与原子替换
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_creates_parent_directory(tmp_db_path: Path) -> None:
    """如果父目录不存在，保存时应自动创建。"""
    nested_dir: Path = tmp_db_path.parent / "subdir" / "data.json5"
    db = RobustAsyncJSON5DB(file_path=nested_dir)
    await db.load()
    await db.set(key_path="x", value=1)
    await db.save()
    assert await aiofiles.os.path.exists(nested_dir)
    # 清理
    await db.close()
    shutil.rmtree(path=nested_dir.parent)


@pytest.mark.asyncio
async def test_atomic_replace_simulation(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await auto_save_db.set(key_path="existing", value="original")
    # 等待自动保存完成（auto_save=True 已持久化）
    await asyncio.sleep(0.01)

    async with aiofiles.open(tmp_db_path, encoding="utf-8") as f:
        original_content = json5.loads(await f.read())

    async def fake_replace(*_args: Any, **_kwargs: Any):
        raise OSError("simulated")

    monkeypatch.setattr(aiofiles.os, "replace", fake_replace)

    with pytest.raises(AtomicReplacementError):
        await auto_save_db.set(key_path="new_key", value="fail")  # 自动保存会触发替换

    async with aiofiles.open(tmp_db_path, encoding="utf-8") as f:
        saved = json5.loads(await f.read())
    assert saved == original_content


# ---------------------------------------------------------------------------
# reload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reload_from_disk(
    loaded_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """外部修改文件后 reload 应获得最新数据。"""
    await loaded_db.set(key_path="v1", value=1)
    # 外部写入新数据
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write(json5.dumps(obj={"v2": 2}))
    await loaded_db.reload()
    data: Any = await loaded_db.read()
    assert data == {"v2": 2}
    assert await loaded_db.exists(key_path="v1") is False


@pytest.mark.asyncio
async def test_reload_with_callback(loaded_db: RobustAsyncJSON5DB) -> None:
    """reload 结束时调用回调。"""
    called = False

    async def on_reload() -> None:
        nonlocal called
        called = True

    await loaded_db.reload(callback=on_reload)
    assert called is True


@pytest.mark.asyncio
async def test_reload_invalid_callback(loaded_db: RobustAsyncJSON5DB) -> None:
    """非 async 回调应抛出 CallbackTypeError。"""

    def not_async_callback() -> None:
        return

    with pytest.raises(expected_exception=CallbackTypeError):
        await loaded_db.reload(callback=not_async_callback)  # type: ignore[arg-type]  # ty:ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# watch（文件监听）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_detects_external_change(
    loaded_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """文件被外部修改后，watcher 应自动 reload 并调用回调。"""
    callback_event = asyncio.Event()

    async def on_change() -> None:
        callback_event.set()

    await loaded_db.watch(callback=on_change, interval=0.05)

    # 等待一段时间让 watcher 启动并记录初始 mtime
    await asyncio.sleep(delay=0.1)

    # 外部修改文件
    async with aiofiles.open(file=tmp_db_path, mode="w", encoding="utf-8") as f:
        await f.write(json5.dumps(obj={"new": "data"}))

    # 等待回调触发
    try:
        await asyncio.wait_for(fut=callback_event.wait(), timeout=2.0)
    except TimeoutError:
        pytest.fail(reason="Watch callback was not triggered")

    # 数据库应已自动重新加载
    data: Any = await loaded_db.read()
    assert data == {"new": "data"}

    # 关闭 watcher（通过 close）
    await loaded_db.close()


@pytest.mark.asyncio
async def test_watch_already_running(loaded_db: RobustAsyncJSON5DB) -> None:
    """重复启动 watcher 应抛出 WatchAlreadyRunningError。"""
    await loaded_db.watch(interval=0.5)
    with pytest.raises(expected_exception=WatchAlreadyRunningError):
        await loaded_db.watch(interval=0.5)
    await loaded_db.close()


# ---------------------------------------------------------------------------
# 并发加载保证
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_load_calls_one_load_task(
    db: RobustAsyncJSON5DB, mocker: Any
) -> None:
    """多次并发调用 load/ensure_loaded 应该只启动一个加载任务。"""
    call_count = 0
    original_unsafe_load = RobustAsyncJSON5DB._unsafe_load

    async def patched_unsafe_load(
        self_: RobustAsyncJSON5DB, default_copy: dict[str, Any]
    ) -> None:
        nonlocal call_count
        call_count += 1
        await original_unsafe_load(self_, default_copy)

    mocker.patch.object(RobustAsyncJSON5DB, "_unsafe_load", new=patched_unsafe_load)
    await asyncio.gather(db.load(), db.load(), db.load())
    assert call_count == 1


# ---------------------------------------------------------------------------
# 关闭时取消任务
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_cancels_load_task() -> None:
    """关闭数据库时应取消正在进行的加载任务。"""
    db = RobustAsyncJSON5DB(file_path="never_used.json5")

    async def stuck_load(_self: Any) -> None:
        await asyncio.Event().wait()

    with patch.object(target=RobustAsyncJSON5DB, attribute="_do_load", new=stuck_load):
        task: Task[None] = asyncio.create_task(coro=db.load())
        await asyncio.sleep(delay=0.05)
        await db.close()
        assert task.cancelled() or task.done()


# ---------------------------------------------------------------------------
# 异常继承关系
# ---------------------------------------------------------------------------


def test_exception_hierarchy() -> None:
    """验证自定义异常的继承关系。"""
    assert issubclass(DatabaseClosedError, DatabaseError)
    assert issubclass(InvalidKeyPathError, DatabaseError)
    assert issubclass(AtomicReplacementError, DatabaseError)
    assert issubclass(InvalidDefaultTypeError, DatabaseError)


# ---------------------------------------------------------------------------
# 边界场景：深层复制、自动保存关闭下的显式保存
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_deepcopy_scalar(loaded_db: RobustAsyncJSON5DB) -> None:
    """非容器类型不应被深拷贝影响。"""
    await loaded_db.set(key_path="num", value=DEFAULT_VALUE_42)
    val: Any = await loaded_db.read(key_path="num", use_deepcopy=True)
    assert val == DEFAULT_VALUE_42


@pytest.mark.asyncio
async def test_auto_save_create_update_return(auto_save_db: RobustAsyncJSON5DB) -> None:
    """验证 auto_save 模式下 create/update 仍返回正确布尔。"""
    res: bool = await auto_save_db.create(key_path="foo", value=1)
    assert res is True
    res: bool = await auto_save_db.create(key_path="foo", value=2)
    assert res is False
    res: bool = await auto_save_db.update(key_path="bar", value=DEFAULT_VALUE_3)
    assert res is False
    await auto_save_db.set(key_path="bar", value=0)
    res: bool = await auto_save_db.update(key_path="bar", value=DEFAULT_VALUE_3)
    assert res is True
    assert await auto_save_db.read(key_path="bar") == DEFAULT_VALUE_3


@pytest.mark.asyncio
async def test_set_batch_with_auto_save(
    auto_save_db: RobustAsyncJSON5DB, tmp_db_path: Path
) -> None:
    """批量更新在 auto_save 下立即持久化。"""
    await auto_save_db.set_batch(updates={"a": 1, "b.c": 2})
    async with aiofiles.open(file=tmp_db_path, encoding="utf-8") as f:
        content = json5.loads(await f.read())
    assert content == {"a": 1, "b": {"c": 2}}


# ---------------------------------------------------------------------------
# load task cancellation edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_task_cancelled_error() -> None:
    """模拟加载任务被取消（非关闭情况），应抛出 LoadTaskCancelledError。"""
    db = RobustAsyncJSON5DB(file_path="some_file.json5")

    async def never_finish(_self: Any) -> None:
        await asyncio.Event().wait()

    with patch.object(
        target=RobustAsyncJSON5DB, attribute="_do_load", new=never_finish
    ):
        await db._start_load_task()
        if db._load_task is not None:
            db._load_task.cancel()
        with pytest.raises(expected_exception=LoadTaskCancelledError):
            await db._await_load_task()
    await db.close()


@pytest.mark.asyncio
async def test_load_state_mismatch() -> None:
    """如果加载完成但 _loaded 仍为 False，应抛出 LoadStateMismatchError。"""
    db = RobustAsyncJSON5DB(file_path="x.json5")

    async def fake_unsafe_load(_self: Any, _default_copy: dict[str, Any]) -> None:
        pass

    with (
        patch.object(
            target=RobustAsyncJSON5DB, attribute="_unsafe_load", new=fake_unsafe_load
        ),
        pytest.raises(expected_exception=LoadStateMismatchError),
    ):
        await db._ensure_loaded()
    await db.close()
