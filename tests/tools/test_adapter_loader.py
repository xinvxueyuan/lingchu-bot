"""测试 tools/adapter_loader.py 停维适配器加载工具。"""

import pytest

from tools.adapter_loader import (
    list_deprecated_adapters,
    load_deprecated_adapter,
)


def test_list_deprecated_adapters() -> None:
    """list_deprecated_adapters 返回全部停维适配器列表（排序）。"""
    result = list_deprecated_adapters()
    assert result == ("~milky", "~onebot.v12", "~qq")
    assert "~milky" in result
    assert "~qq" in result
    assert "~onebot.v12" in result


def test_load_deprecated_adapter_unknown() -> None:
    """加载未在停维列表中的适配器时抛出 ValueError。"""
    with pytest.raises(ValueError, match="不在停维列表中"):
        load_deprecated_adapter("~unknown")
