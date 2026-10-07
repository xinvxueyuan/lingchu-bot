"""静态守卫：全项目内任何 ``At`` 出现处都必须同时接受 ``int``。

规则来源（用户拍板）：**全项目范围，at 解析都要同时声明 int**。

背景：QQ 的 @ 在协议端拿不到真实 uid（LLBot 的 at 段定位不到目标），因此本插件所有
带目标的命令都允许直接传数字 user_id，命令侧统一声明 ``Args["user", At | int]``。

两类真实故障使这条规则必须由静态检查守住：

1. handler 入参只写 ``user: At``（命令侧已声明 ``At | int``）→ Alconna 依赖注入收到
   数字时解析失败，表现为**命令匹配成功却完全无回复**（日志只有 ``running complete``，
   既无回复也无异常）。
2. 解析助手只写 ``user: At`` 却内部访问 ``user.target`` / ``user.display`` → 传数字时
   ``AttributeError``。

单元测试抓不到它们：现有测试都是**直接调用**函数（绕过依赖注入），传 int 也能过。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import pathlib

SOURCE_ROOT = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "plugins"
    / "nonebot_plugin_lingchu_bot"
)

#: 期望至少能扫到这么多处 At 标注；低于此值说明扫描逻辑失效（会假通过）。
MIN_AT_ANNOTATIONS = 20

AT_NAME = "At"
WRAPPER_NAME = "selected_adapter_handle"


@dataclass(frozen=True)
class AtAnnotation:
    """一处提到 ``At`` 的注解。"""

    location: str
    context: str
    annotation: str

    @property
    def accepts_int(self) -> bool:
        """该注解是否同时允许数字 user_id。"""
        return "int" in self.annotation.replace(" ", "")


def _annotation_text(node: ast.AST | None) -> str:
    return ast.unparse(node) if node is not None else ""


def _compact(text: str) -> str:
    return text.replace(" ", "")


def _references_at(annotation: str) -> bool:
    """注解是否引用了名为 ``At`` 的类型（排除 ``Attrs`` 等同前缀名）。"""
    try:
        tree = ast.parse(annotation, mode="eval")
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.Name) and node.id == AT_NAME for node in ast.walk(tree)
    )


def _iter_annotated_nodes() -> list[AtAnnotation]:
    """扫描全项目：函数参数、AnnAssign、dataclass 字段等所有注解。"""
    found: list[AtAnnotation] = []
    root = SOURCE_ROOT.parent.parent
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[tuple[str, ast.AST | None]] = []
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                all_args = [
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                ]
                if node.args.vararg is not None:
                    all_args.append(node.args.vararg)
                if node.args.kwarg is not None:
                    all_args.append(node.args.kwarg)
                candidates.extend(
                    (f"{node.name}({arg.arg})", arg.annotation) for arg in all_args
                )
            elif isinstance(node, ast.AnnAssign):
                candidates.append((
                    f"annassign {ast.unparse(node.target)}",
                    node.annotation,
                ))
            for label, annotation in candidates:
                text = _annotation_text(annotation)
                if text and _references_at(text):
                    found.append(
                        AtAnnotation(
                            location=f"{path.relative_to(root)}:{getattr(node, 'lineno', 0)}",
                            context=label,
                            annotation=text,
                        )
                    )
    return found


def _literal_args_declarations() -> list[tuple[str, str]]:
    """收集命令侧 ``Args["user"/"target?", <type>]`` 声明。

    结构化判定（用 ast 而非字符串前缀），因为 ``ast.unparse`` 对字符串常量输出单引号。
    """
    declared: list[tuple[str, str]] = []
    commands_root = SOURCE_ROOT / "handle" / "qq" / "commands"
    for path in sorted(commands_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            value = node.value
            if not isinstance(value, ast.Name) or value.id != "Args":
                continue
            slice_node = node.slice
            if not isinstance(slice_node, ast.Tuple) or not slice_node.elts:
                continue
            first = slice_node.elts[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                continue
            # 只看目标参数本身；reason/content/duration 等其它 Args 与本规则无关
            if first.value.rstrip("?") not in {"user", "target"}:
                continue
            declared.append((f"{path.name}:{node.lineno}", ast.unparse(node)))
    return declared


def test_scan_finds_enough_at_annotations() -> None:
    """守卫自身的前提：必须真的扫到足够多的 At 标注，否则下面的断言会假通过。"""
    annotated = _iter_annotated_nodes()

    assert len(annotated) >= MIN_AT_ANNOTATIONS, [item.context for item in annotated]


def test_every_at_annotation_also_accepts_int() -> None:
    """规则本体：任何提到 At 的注解都必须同时含 int。"""
    offenders = [
        f"{item.location} {item.context}: {item.annotation}"
        for item in _iter_annotated_nodes()
        if not item.accepts_int
    ]

    assert not offenders, (
        "以下注解只接受 At、没有同时声明 int —— 传数字 user_id 时会失败"
        "（命令无回复或 AttributeError）：\n" + "\n".join(offenders)
    )


def test_command_declarations_all_accept_numeric_user_id() -> None:
    """命令侧 Args 声明必须一致地允许 int —— 这是 handler 侧规则的依据。"""
    declared = _literal_args_declarations()

    assert len(declared) >= 10, declared
    offenders = [
        f"{location} {source}"
        for location, source in declared
        if "int" not in _compact(source)
    ]
    assert not offenders, "以下命令未声明接受数字 user_id：\n" + "\n".join(offenders)


def test_all_target_handlers_accept_numeric_user_id() -> None:
    """所有 ``@selected_adapter_handle`` 处理器的 user/target 参数都必须接受 int。"""
    offenders: list[str] = []
    checked = 0
    for path in sorted((SOURCE_ROOT / "handle").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            if not any(
                (
                    isinstance(dec, ast.Call)
                    and _compact(ast.unparse(dec.func)) == WRAPPER_NAME
                )
                or (isinstance(dec, ast.Name) and dec.id == WRAPPER_NAME)
                for dec in node.decorator_list
            ):
                continue
            for arg in node.args.args:
                if arg.arg not in {"user", "target"}:
                    continue
                checked += 1
                text = _annotation_text(arg.annotation)
                if "int" not in _compact(text):
                    offenders.append(
                        f"{path.name}:{node.lineno} {node.name}({arg.arg}: {text})"
                    )

    assert checked >= 20, f"只检查到 {checked} 个处理器参数，扫描可能失效"
    assert not offenders, "以下命令处理器不接受数字 user_id：\n" + "\n".join(offenders)


def test_failure_prone_functions_are_covered() -> None:
    """回归锚点：本次故障涉及的函数必须被扫到且接受 int。"""
    covered = {item.context: item for item in _iter_annotated_nodes()}

    for expected in (
        "onebot11_unblock_member(user)",
        "onebot11_global_unblock_member(user)",
        "target_user_onebot11(user)",
        "resolve_user_onebot11(user)",
    ):
        assert expected in covered, f"{expected} 未被守卫扫描到"
        assert covered[expected].accepts_int, f"{expected} 不接受数字 user_id"
