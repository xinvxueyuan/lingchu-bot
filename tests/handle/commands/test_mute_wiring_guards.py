"""接线与分层静态守卫：钉住 matcher 声明、导出链与私有 API 分层硬约束。"""

import ast
import inspect
from pathlib import Path

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    mute as mute_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import mute as cmd_module

#: default/ 目录下被视为「协议端私有」的 action（新增时同步补充）
PRIVATE_ACTIONS = {
    "get_group_shut_list",  # LLBot 私有
    "_send_group_notice",  # NapCat 私有
    "set_group_portrait",  # NapCat 私有
}


def _default_dir() -> Path:
    return Path(mute_module.__file__).parent


def _module_ast() -> ast.Module:
    """直接读源码文件构建 AST（比 inspect.getsource 稳）。"""
    return ast.parse(_default_dir().joinpath("mute.py").read_text(encoding="utf-8"))


FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _function_node(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(_module_ast()):
        if isinstance(node, FUNC_NODES) and node.name == name:
            return node
    msg = f"未找到函数定义: {name}"
    raise AssertionError(msg)


def _alconna_block(name: str) -> str:
    """取 ``<name>: type[Matcher] = on_alconna(...)`` 的完整调用块（括号配平）。"""
    src = inspect.getsource(cmd_module)
    marker = f"{name}: type[Matcher] = on_alconna("
    start = src.find(marker)
    assert start != -1, f"未找到 matcher 声明: {name}"
    i = start + len(marker)
    depth = 1
    while i < len(src) and depth:
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
        i += 1
    return src[start:i]


def test_one_click_unmute_matcher_declared_and_exported() -> None:
    """「一键解禁」matcher 存在、导出链完整、装饰器参数正确。"""
    assert hasattr(cmd_module, "one_click_unmute_cmd")
    assert "onebot11_one_click_unmute" in cmd_module._LAZY_EXPORTS

    func = _function_node("onebot11_one_click_unmute")
    joined = " ".join(ast.unparse(d) for d in func.decorator_list)
    assert "selected_adapter_handle" in joined
    assert "~onebot.v11" in joined
    assert "one_click_unmute" in joined


def test_mute_list_matcher_declared_and_exported() -> None:
    """「禁言列表」matcher 存在、导出链完整、装饰器参数正确。"""
    assert hasattr(cmd_module, "mute_list_cmd")
    assert "onebot11_mute_list" in cmd_module._LAZY_EXPORTS

    func = _function_node("onebot11_mute_list")
    joined = " ".join(ast.unparse(d) for d in func.decorator_list)
    assert "selected_adapter_handle" in joined
    assert "~onebot.v11" in joined
    assert "mute_list" in joined


def test_new_matchers_use_expected_priority_and_block() -> None:
    """priority/block/use_cmd_sep 与同文件既有 matcher 一致。"""
    for name in ("one_click_unmute_cmd", "mute_list_cmd"):
        block = _alconna_block(name)
        assert "priority=805" in block, name
        assert "block=True" in block, name
        assert "use_cmd_sep=False" in block, name
        assert "use_cmd_start=True" in block, name


def test_new_matchers_declare_no_alconna_args() -> None:
    """这两个命令无参数：不能声明 Args（否则纯命令会被当成缺参而失配）。"""
    for name in ("one_click_unmute_cmd", "mute_list_cmd"):
        assert "Args[" not in _alconna_block(name), name


def test_default_layer_has_no_private_action_calls() -> None:
    """硬约束守卫：``default/`` 不得直接调用协议端私有 action。

    私有 API（1 个协议端实现独有）必须落在 ``onebot11/<implementation>/``，
    由 ``default/`` 作为中间层解析后分派。这里按 AST 扫所有 ``call_api`` 的
    字面量首参，命中已知私有 action 即视为违规。
    """
    default_dir = Path(mute_module.__file__).parent
    private_actions = {
        "get_group_shut_list",  # LLBot 私有
        "_send_group_notice",  # NapCat 私有
        "set_group_portrait",  # NapCat 私有
    }

    offenders: list[str] = []
    checked = 0
    for py in sorted(default_dir.glob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "call_api"):
                continue
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                checked += 1
                if first.value in private_actions:
                    offenders.append(f"{py.name}: {first.value}")

    # 防「扫描恒为空」的假通过：本目录下确实存在 call_api 字面量调用
    assert checked >= 1, "未扫到任何 call_api 字面量调用 —— 扫描逻辑失效"
    assert not offenders, f"default/ 直接调用了私有 action: {offenders}"


def test_private_layer_owns_the_llbot_action() -> None:
    """LLBot 私有 action 名必须定义在私有层。"""
    private_layer = _default_dir().parent / "llbot"
    assert private_layer.is_dir(), "私有层 llbot/ 不存在"

    llbot_src = (private_layer / "mute_list.py").read_text(encoding="utf-8")
    assert '"get_group_shut_list"' in llbot_src


def test_dispatch_routes_llbot_through_private_layer() -> None:
    """中间层分派必须把 LLBot 指向私有层实现，而不是自己调接口。"""
    src = ast.unparse(_function_node("_resolve_shut_list_action"))

    assert "app_name" in src
    assert "protocol_version" in src
    assert "fetch_group_shut_list" in src, "未把 LLBot 分派到私有层实现"
    assert "不支持" in src, "缺少「不支持」分支（不对未知协议端猜实现）"
