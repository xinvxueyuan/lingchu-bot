"""
typed_command --- 命令解析与路由模块 / Command parsing and routing

该模块实现了一套轻量的命令解析器和路由器，支持类型注解驱动的参数解析、
布尔标志提取、子路由挂载以及中间件链执行。所有公开接口使用明确的类型注解，
并在函数/类处添加中英文 docstring 以便国际化文档需求。

This module implements a lightweight command parser and router. It supports
type-annotation driven parameter parsing, boolean flag extraction, sub-router
mounting, and middleware chaining. Public interfaces are fully type-annotated
and documented in both Chinese and English.

注意：抑制与 lint/typing 无关的警告应集中在模块顶部处理。
Note: Suppressions unrelated to lint/typing should be centralized at the top
of the module.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Union,
    get_args,
    get_origin,
)
from typing import Literal as LiteralType

if TYPE_CHECKING:
    from collections.abc import Callable

_TOKEN_PATTERN = re.compile(
    r'"([^"]*)"'
    r"|\[CQ:([a-zA-Z0-9_]+)((?:,[a-zA-Z0-9_]+=[^,\]]*)*)\]"
    r"|@(\d+)"
    r"|(\S+)"
)

_CQ_ARGS_PATTERN = re.compile(r"([a-zA-Z0-9_]+)=(.+?)(?=,[a-zA-Z0-9_]+=|$)")


class ParseError(Exception):
    """命令解析错误的基本异常。

    Args:
        message: 错误信息 / Error message.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class Token:
    """解析后的小型 token 对象，用于表示命令片段。

    Attributes:
        type: token 类型，例如 'str'/'word'/'cq'/'user'
        value: 解析后的值
        raw: 原始文本片段
    """

    __slots__ = ("raw", "type", "value")

    def __init__(self, type_: str, value: Any, raw: str) -> None:
        self.type = type_
        self.value = value
        self.raw = raw

    def __repr__(self) -> str:
        return f"<{self.type}:{self.value}>"


def tokenize(text: str) -> list[Token]:
    """将输入文本切分为命令 token 列表。

    Args:
        text: 原始命令文本 / Raw command text.

    Returns:
        token 列表 / List of tokens.
    """

    tokens: list[Token] = []
    for match in _TOKEN_PATTERN.finditer(text):
        quoted, cq_type, cq_args, at, normal = match.groups()
        raw = match.group(0)
        if quoted is not None:
            tokens.append(Token("str", quoted, raw))
        elif cq_type is not None:
            params: dict[str, str] = {}
            if cq_args:
                cq_args = cq_args.strip(",")
                for sub in _CQ_ARGS_PATTERN.finditer(cq_args):
                    params[sub.group(1)] = sub.group(2)
            tokens.append(Token("cq", {"type": cq_type, "params": params}, raw))
        elif at is not None:
            tokens.append(Token("user", int(at), raw))
        else:
            tokens.append(Token("word", normal, raw))
    return tokens


class TypeSpec:
    """类型解析器封装。

    Attributes:
        name: 类型名 / human readable name.
        parser: 从 Token 解析出值的函数 / parser function.
    """

    def __init__(self, name: str, parser: Callable[[Token], Any]) -> None:
        self.name = name
        self.parser = parser


def _parse_none(token: Token) -> None:
    if token.type == "word" and token.value.lower() in ("none", "null"):
        return
    msg = f"期望 none/null，得到 {token.raw}"
    raise ParseError(msg) from None


def _parse_int(token: Token) -> int:
    if token.type == "user":
        return token.value
    if token.type == "word":
        try:
            return int(token.value)
        except ValueError as err:
            msg = f"期望整数，得到 {token.raw}"
            raise ParseError(msg) from err
    msg = f"期望整数，得到 {token.raw}"
    raise ParseError(msg) from None


def _parse_str(token: Token) -> str:
    if token.type in ("str", "word"):
        return token.value
    msg = f"期望字符串，得到 {token.raw}"
    raise ParseError(msg) from None


def _parse_float(token: Token) -> float:
    if token.type == "word":
        try:
            return float(token.value)
        except ValueError as err:
            msg = f"期望浮点数，得到 {token.raw}"
            raise ParseError(msg) from err
    msg = f"期望浮点数，得到 {token.raw}"
    raise ParseError(msg) from None


def _parse_bool(token: Token) -> bool:
    if token.type == "word":
        val = token.value.lower()
        if val in ("true", "1"):
            return True
        if val in ("false", "0"):
            return False
    msg = f"期望布尔值，得到 {token.raw}"
    raise ParseError(msg) from None


def _parse_user(token: Token) -> int:
    if token.type == "user":
        return token.value
    if token.type == "cq" and token.value.get("type") == "at":
        qq = token.value["params"].get("qq")
        if qq is not None:
            try:
                return int(qq)
            except (ValueError, TypeError) as err:
                msg = f"CQ at 的 qq 字段无效: {qq}"
                raise ParseError(msg) from err
    msg = f"期望 @用户 或 CQ at，得到 {token.raw}"
    raise ParseError(msg) from None


TYPE_REGISTRY: dict[Any, TypeSpec] = {
    int: TypeSpec("int", _parse_int),
    str: TypeSpec("str", _parse_str),
    float: TypeSpec("float", _parse_float),
    bool: TypeSpec("bool", _parse_bool),
    "user": TypeSpec("user", _parse_user),
    type(None): TypeSpec("none", _parse_none),
}


def register_type(name: str, parser: Callable[[Token], Any]) -> None:
    TYPE_REGISTRY[name] = TypeSpec(name, parser)


def type_name(spec: Any) -> str:
    if isinstance(spec, TypeSpec):
        return spec.name
    if isinstance(spec, tuple):
        kind = spec[0]
        if kind == "list":
            return f"List[{type_name(spec[1])}]"
        if kind == "optional":
            return f"Optional[{type_name(spec[1])}]"
        if kind == "union":
            inners = ", ".join(type_name(s) for s in spec[1])
            return f"Union[{inners}]"
        if kind == "literal":
            allowed = ", ".join(repr(v) for v in spec[1])
            return f"Literal[{allowed}]"
    return str(spec)


def resolve_type(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        none_types = [a for a in args if a is type(None)]
        non_none_types = [a for a in args if a is not type(None)]
        if len(none_types) == 1 and len(non_none_types) == 1:
            inner = resolve_type(non_none_types[0])
            return ("optional", inner)
        return ("union", [resolve_type(a) for a in args])
    if origin is list:
        inner = get_args(annotation)[0]
        return ("list", resolve_type(inner))
    if origin is LiteralType:
        allowed = get_args(annotation)
        return ("literal", allowed)
    if isinstance(annotation, str):
        spec = TYPE_REGISTRY.get(annotation)
        if spec is None:
            msg = f"未知类型名: {annotation}"
            raise ValueError(msg) from None
        return spec
    spec = TYPE_REGISTRY.get(annotation)
    if spec is None:
        msg = f"未注册的类型: {annotation}"
        raise ValueError(msg) from None
    return spec


@dataclass
class MatchContext:
    """列表匹配上下文，供列表参数处理使用。"""

    inner_spec: Any
    remaining_params: list["Param"]
    tokens: list["Token"]
    i: int
    tlen: int
    param_name: str
    has_default: bool
    is_optional: bool
    defaults: dict[str, Any]
    node: "Param"


class Node:
    pass


class Literal(Node):
    def __init__(self, value: str) -> None:
        self.value = value


@dataclass
class Param(Node):
    """表示命令参数元信息的节点。

    Attributes:
        name: 参数名
        spec: 参数类型描述（resolve_type 返回值）
        has_default: 是否有默认值
        greedy: 是否为贪婪参数（吃掉剩余文本）
        flag: 是否为布尔标志
        flag_short: 短标志，例如 '-f'
    """

    name: str
    spec: Any
    has_default: bool = False
    greedy: bool = False
    flag: bool = False
    flag_short: str | None = None


@dataclass
class Context:
    """执行时的上下文对象，传递给命令处理函数。

    Attributes:
        raw_text: 原始文本
        tokens: token 列表（可选，通常由 parse 填充）
        user_id: 用户标识（可选）
        channel_id: 频道标识（可选）
        extra: 额外数据字典
    """

    raw_text: str = ""
    tokens: list[Token] | None = None
    user_id: Any = None
    channel_id: Any = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tokens is None:
            self.tokens = []

    def __getitem__(self, key: str) -> Any:
        return self.extra[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.extra[key] = value


class MatchError:
    """参数匹配失败时返回的错误结构。

    Attributes:
        message: 错误信息
        param: 相关参数名（如有）
        token: 失败的 token 或其原始文本
        index: 失败位置
        expected: 期望的类型描述
        score: 错误评分（用于选择最佳错误）
    """

    def __init__(  # noqa: PLR0913
        self,
        message: str,
        *,
        param: str | None = None,
        token: Any = None,
        index: int | None = None,
        expected: str | None = None,
        score: int = 0,
    ) -> None:
        self.message = message
        self.param = param
        self.token = token
        self.index = index
        self.expected = expected
        self.score = score

    def to_dict(self, command: str | None = None) -> dict[str, Any]:
        return {
            "error": True,
            "command": command,
            "message": self.message,
            "param": self.param,
            "token": self.token,
            "index": self.index,
            "expected": self.expected,
        }


def build_ast(name: str, func: Callable) -> tuple[list[Node], dict[str, Any]]:
    """根据处理函数签名构建 AST 节点与默认值表。

    Args:
        name: 命令名称（字符串）。
        func: 处理函数对象。

    Returns:
        (nodes, defaults) 二元组：节点列表与默认值映射。
    """

    sig = inspect.signature(func)
    nodes: list[Node] = [Literal(name)]
    defaults: dict[str, Any] = {}

    params = list(sig.parameters.values())

    for p in params:
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            msg = f"命令处理函数不支持 *args 或 **kwargs 参数: {p.name}"
            raise ValueError(msg) from None

    real_params = [p for p in params if p.name != "ctx"]

    for i, p in enumerate(real_params):
        annotation = p.annotation
        spec = (
            resolve_type(annotation)
            if annotation is not inspect.Parameter.empty
            else resolve_type(str)
        )
        has_default = p.default is not inspect.Parameter.empty
        default_value = p.default if has_default else None

        is_flag = (
            p.name.startswith("flag_")
            and spec == TYPE_REGISTRY[bool]
            and has_default
            and default_value is False
        )
        flag_short = None
        if is_flag:
            long_name = p.name[5:]
            short = long_name[0]
            flag_short = f"-{short}"

        greedy = (
            spec == TYPE_REGISTRY[str] and i == len(real_params) - 1 and not is_flag
        )
        nodes.append(
            Param(
                name=p.name,
                spec=spec,
                has_default=has_default,
                greedy=greedy,
                flag=is_flag,
                flag_short=flag_short,
            )
        )
        if has_default:
            defaults[p.name] = default_value
    return nodes, defaults


def extract_flags(
    tokens: list[Token], flag_defs: dict[str, tuple[str, str | None]]
) -> tuple[dict[str, bool], list[Token]]:
    """提取命令中的布尔标志并返回剩余 token 列表。

    行为：遇到独立的 `--` 停止标志解析，后续全部视为普通参数。
    """

    flag_values = dict.fromkeys(flag_defs, False)
    remaining: list[Token] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "word" and tok.value == "--":
            remaining.extend(tokens[i + 1 :])
            break
        if tok.type != "word":
            remaining.append(tok)
            i += 1
            continue
        val = tok.value
        matched = False
        for name, (full, short) in flag_defs.items():
            if val == f"--{full}" or (short and val == short):
                flag_values[name] = True
                matched = True
                break
        if not matched:
            remaining.append(tok)
        i += 1
    return flag_values, remaining


def _match_union(inner_specs: list[Any], token: Token) -> Any:
    """尝试匹配 Union 中的任一类型。"""
    for inner in inner_specs:
        try:
            return match_single(token, inner)
        except ParseError:
            continue
    msg = f"无法匹配任何 Union 类型，token={token.raw}"
    raise ParseError(msg) from None


def _match_literal(token: Token, allowed: tuple) -> Any:
    """匹配 Literal 类型值。"""
    if token.type in ("word", "str"):
        result = next((v for v in allowed if _literal_match(token.value, v)), None)
        if result is not None:
            return result
    msg = f"期望值 {allowed}，得到 {token.raw}"
    raise ParseError(msg) from None


def match_single(token: Token, spec: Any) -> Any:
    """根据 spec 将单个 token 解析为目标值。

    Raises:
        ParseError: 当 token 无法匹配 spec 时抛出。
    """

    if isinstance(spec, TypeSpec):
        return spec.parser(token)
    if not isinstance(spec, tuple):
        msg = f"未知 spec 类型: {spec}"
        raise ParseError(msg) from None

    kind = spec[0]
    if kind == "optional":
        return match_single(token, spec[1])
    if kind == "union":
        return _match_union(spec[1], token)
    if kind == "literal":
        return _match_literal(token, spec[1])
    if kind == "list":
        msg = (
            "当前版本不支持嵌套列表类型，"
            "请使用纯 List[X] 或 Optional[List[X]] 作为参数类型"
        )
        raise ParseError(msg) from None
    msg = f"未知 spec 类型: {spec}"
    raise ParseError(msg) from None


def _literal_match(raw: str, v: Any) -> bool:
    """判断原始字符串是否与 Literal 值匹配（对布尔/None 有特殊处理）。"""

    if isinstance(v, bool):
        r = raw.lower()
        if v:
            return r in ("true", "1")
        return r in ("false", "0")
    if v is None:
        return raw.lower() in ("none", "null")
    return raw == str(v)


def _is_required(param: Param) -> bool:
    return not (
        param.greedy
        or param.flag
        or param.has_default
        or (isinstance(param.spec, tuple) and param.spec[0] == "optional")
    )


def resolve_default_for_param(node: Param, defaults: dict[str, Any]) -> Any:
    return defaults.get(node.name) if node.has_default else None


def _unpack_list_spec(spec: Any) -> tuple[Any, bool] | None:
    """分析是否为 List[X] 或 Optional[List[X]]，并返回内部类型与可选性标记。"""

    if isinstance(spec, tuple):
        if spec[0] == "list":
            return spec[1], False
        if (
            spec[0] == "optional"
            and isinstance(spec[1], tuple)
            and spec[1][0] == "list"
        ):
            return spec[1][1], True
    return None


def _handle_list_matching(
    ctx: MatchContext,
) -> tuple[Any | None, int, MatchError | None]:
    """统一处理列表参数的匹配逻辑。

    返回 (values, new_pos, error)。当匹配失败返回适当的 MatchError 对象。
    """

    min_needed = len(ctx.remaining_params)
    max_take = ctx.tlen - ctx.i - min_needed
    values = []
    pos = ctx.i
    if ctx.tlen > pos and max_take > 0:
        taken = 0
        while taken < max_take and pos < ctx.tlen:
            try:
                values.append(match_single(ctx.tokens[pos], ctx.inner_spec))
                pos += 1
                taken += 1
            except ParseError:
                if taken == 0:
                    token_val = ctx.tokens[ctx.i].raw
                    error = MatchError(
                        "列表参数类型错误",
                        param=ctx.param_name,
                        token=token_val,
                        index=ctx.i,
                        expected=type_name(ctx.inner_spec),
                        score=ctx.i,
                    )
                    return None, pos, error
                break

    if not values:
        if ctx.has_default or ctx.is_optional:
            return resolve_default_for_param(ctx.node, ctx.defaults), pos, None
        error = MatchError(
            "列表参数至少需要一个值",
            param=ctx.param_name,
            index=ctx.i,
            expected=type_name(ctx.inner_spec),
            score=ctx.i,
        )
        return None, pos, error
    return values, pos, None


def match(
    nodes: list[Node], tokens: list[Token], defaults: dict[str, Any]
) -> tuple[dict[str, Any] | None, MatchError | None]:
    """将 token 列表与 AST 节点匹配并返回参数映射或错误。

    Returns:
        (result, error) 二元组：result 为参数字典或 None；error 为 MatchError 或 None。
    """

    result: dict[str, Any] = {}
    i = 0
    tlen = len(tokens)

    param_nodes = [n for n in nodes if isinstance(n, Param)]

    for idx, node in enumerate(param_nodes):
        if node.flag:
            continue

        spec = node.spec

        if node.greedy:
            result[node.name] = " ".join(t.value for t in tokens[i:])
            return result, None

        list_info = _unpack_list_spec(spec)
        if list_info is not None:
            inner_spec, is_optional = list_info
            remaining = [n for n in param_nodes[idx + 1 :] if _is_required(n)]
            ctx = MatchContext(
                inner_spec,
                remaining,
                tokens,
                i,
                tlen,
                node.name,
                node.has_default,
                is_optional,
                defaults,
                node,
            )
            values, i, error = _handle_list_matching(ctx)
            if error:
                return None, error
            result[node.name] = values
            continue

        if i < tlen:
            try:
                result[node.name] = match_single(tokens[i], spec)
                i += 1
            except ParseError:
                return None, MatchError(
                    "类型错误",
                    param=node.name,
                    token=tokens[i].raw,
                    index=i,
                    expected=type_name(spec),
                    score=i,
                )
        elif node.has_default or (isinstance(spec, tuple) and spec[0] == "optional"):
            result[node.name] = resolve_default_for_param(node, defaults)
        else:
            return None, MatchError("缺少参数", param=node.name, index=i, score=i)

    if i != tlen:
        rest = [t.raw for t in tokens[i:]]
        return None, MatchError("多余参数", token=" ".join(rest), index=i, score=i)
    return result, None


class TrieNode:
    __slots__ = ("children", "routes", "sub_router")

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.routes: list[
            tuple[
                list[Node], Callable, dict[str, Any], dict[str, tuple[str, str | None]]
            ]
        ] = []
        self.sub_router: CommandRouter | None = None


class CommandRouter:
    """命令路由器，支持注册、挂载子路由及帮助生成。

    简要说明：可通过 `command` 装饰器注册处理函数，通过 `mount` 挂载子路由器，
    并支持中间件链式调用。
    """

    def __init__(self, name: str = "") -> None:
        self.root = TrieNode()
        self.name = name
        self.middlewares: list[Callable] = []
        self.parent: CommandRouter | None = None
        self.mount_path: str | None = None

    def use(self, middleware: Callable) -> CommandRouter:
        """注册中间件（必须为异步函数）。"""

        if not inspect.iscoroutinefunction(middleware):
            raise TypeError("中间件必须是异步函数")
        self.middlewares.append(middleware)
        return self

    def command(self, path: str, aliases: list[str] | None = None) -> Callable:
        """装饰器：在给定路径注册命令处理函数。

        Args:
            path: 主命令路径。
            aliases: 可选别名列表。
        """

        def decorator(func: Callable) -> Callable:
            paths = [path] + (aliases or [])
            for p in paths:
                parts = p.strip().split()
                if not parts:
                    raise ValueError("命令路径不能为空")
                node = self.root
                for part in parts[:-1]:
                    node = node.children.setdefault(part, TrieNode())
                last_node = node.children.setdefault(parts[-1], TrieNode())
                if last_node.sub_router is not None:
                    msg = f"路径 '{p}' 已挂载子路由器，无法注册命令"
                    raise RuntimeError(msg) from None
                ast, defaults = build_ast(parts[-1], func)
                flag_defs: dict[str, tuple[str, str | None]] = {}
                short_flags_seen: set[str] = set()
                for n in ast:
                    if isinstance(n, Param) and n.flag:
                        long_name = n.name[5:]
                        short = n.flag_short
                        if short:
                            if short in short_flags_seen:
                                msg = f"短标志 '{short}' 在命令 '{p}' 中重复定义"
                                raise ValueError(msg) from None
                            short_flags_seen.add(short)
                        flag_defs[n.name] = (long_name, short)
                last_node.routes.append((ast, func, defaults, flag_defs))
            return func

        return decorator

    def mount(self, path: str, router: CommandRouter) -> None:
        """挂载子路由器到指定路径。

        Raises:
            ValueError: 当 path 为空时。
            RuntimeError: 当目标节点已有直接注册的命令时。
        """

        parts = path.strip().split()
        if not parts:
            raise ValueError("挂载路径不能为空")
        node = self.root
        for part in parts:
            node = node.children.setdefault(part, TrieNode())
        if node.routes:
            msg = f"路径 '{path}' 已存在直接注册的命令，无法挂载子路由器"
            raise RuntimeError(msg) from None
        node.sub_router = router
        router.parent = self
        router.mount_path = path

    def _collect_help(
        self, prefix: str = "", node: TrieNode | None = None
    ) -> list[str]:
        if node is None:
            node = self.root
        lines: list[str] = []
        for part, child in node.children.items():
            current_prefix = f"{prefix}{part} "
            if child.sub_router:
                lines.extend(child.sub_router._collect_help(current_prefix))
            lines.extend(self._build_route_help(current_prefix, child.routes))
            lines.extend(self._collect_help(current_prefix, child))
        return lines

    def _build_route_help(self, prefix: str, routes: list) -> list[str]:
        """为给定路由生成帮助文本行列表。"""

        lines: list[str] = []
        for ast, func, defaults, flag_defs in routes:
            cmd_name = next((n.value for n in ast if isinstance(n, Literal)), None)
            if not cmd_name:
                continue
            doc = func.__doc__ or ""
            param_reprs = self._build_param_reprs(ast, defaults)
            flags_display = [f"[--{long_name}]" for long_name, _ in flag_defs.values()]
            param_str = " ".join(param_reprs + flags_display)
            lines.append(f"{prefix}{param_str} -> {doc.strip()}")
        return lines

    def _build_param_reprs(
        self, ast: list[Node], defaults: dict[str, Any]
    ) -> list[str]:
        """构建参数展示字符串列表。"""

        param_reprs: list[str] = []
        for p in ast:
            if not isinstance(p, Param) or p.flag:
                continue
            if p.greedy:
                param_reprs.append("[text...]")
            else:
                param_reprs.append(self._format_param(p, defaults))
        return param_reprs

    def _format_param(self, p: Param, defaults: dict[str, Any]) -> str:
        """格式化单个参数的显示字符串。"""

        if p.has_default:
            dv = defaults.get(p.name)
            is_optional_spec = isinstance(p.spec, tuple) and p.spec[0] == "optional"
            if dv is None and is_optional_spec:
                param_str = f"[{p.name}]"
            else:
                param_str = f"[{p.name}={dv}]"
        elif isinstance(p.spec, tuple) and p.spec[0] == "optional":
            param_str = f"[{p.name}]"
        else:
            param_str = p.name

        if isinstance(p.spec, tuple) and p.spec[0] == "literal":
            allowed = p.spec[1]
            pattern = "{" + "|".join(str(v) for v in allowed) + "}"
            param_str += pattern
        return param_str

    def help(self, command: str | None = None) -> str:
        """返回命令帮助文本。

        如果提供 `command`，返回该命令的详细说明；否则返回注册的命令列表。
        """

        if command:
            parsed = self.parse(command, dry_run=True)
            if parsed and not parsed.get("error"):
                func = parsed.get("handler")
                if func:
                    doc = func.__doc__ or "无帮助信息"
                    return f"命令: {command}\n{doc}"
            return f"未找到命令: {command}"
        lines = self._collect_help()
        if not lines:
            return "没有注册任何命令。"
        return "可用命令：\n" + "\n".join(lines)

    def _find_best_route_match(
        self,
        ast_routes: list,
        tokens: list[Token],
        i: int,
    ) -> tuple[dict[str, Any] | None, MatchError | None, Any]:
        """在候选路由中选出最佳匹配并返回 (params, error, handler)。"""

        best_error: MatchError | None = None
        for ast, func, defaults, flag_defs in ast_routes:
            flag_values, remaining_tokens = extract_flags(tokens[i:], flag_defs)
            result, err = match(ast, remaining_tokens, defaults)
            if result is not None:
                result.update(flag_values)
                return result, None, func
            if err and (best_error is None or err.score > best_error.score):
                best_error = err
        return None, best_error, None

    def parse(  # noqa: PLR0911
        self, text: str, *, dry_run: bool = False, context: Context | None = None
    ) -> dict[str, Any]:
        """解析命令文本并返回解析结果或错误描述。

        Returns:
            当解析成功时返回包含 `path`、`params`、`handler` 的字典；
            失败时返回包含 `error` 的错误描述。
        """

        tokens = tokenize(text)
        if not tokens:
            return {"error": True, "message": "空命令"}

        node = self.root
        path_parts: list[str] = []
        i = 0
        while (
            i < len(tokens)
            and tokens[i].type == "word"
            and tokens[i].value in node.children
        ):
            part = tokens[i].value
            path_parts.append(part)
            node = node.children[part]
            i += 1

        if node.sub_router is not None:
            sub_result = node.sub_router.parse(
                " ".join(t.raw for t in tokens[i:]), dry_run=dry_run, context=context
            )
            if sub_result and not sub_result.get("error"):
                sub_path = sub_result.get("path", "").strip()
                full_path_parts = list(filter(None, [" ".join(path_parts), sub_path]))
                sub_result["full_path"] = " ".join(full_path_parts)
            return sub_result

        if not path_parts:
            return {"error": True, "message": f"未知命令 '{tokens[0].raw}'"}

        if not node.routes:
            cmd_path = " ".join(path_parts)
            return {"error": True, "message": f"命令 '{cmd_path}' 不存在"}

        result, best_error, handler = self._find_best_route_match(
            node.routes, tokens, i
        )
        if result is not None:
            return {
                "path": " ".join(path_parts),
                "params": result,
                "handler": handler,
                "flags": {k: v for k, v in result.items() if k.startswith("flag_")},
                "dry_run": dry_run,
            }

        if best_error:
            return best_error.to_dict(command=" ".join(path_parts))
        return {"error": True, "message": "匹配失败"}

    async def dispatch(self, text: str, context: Context | None = None) -> Any:
        """执行解析与分发流程，包含中间件链调用。

        Args:
            text: 原始命令文本。
            context: 可选执行上下文。

        Returns:
            handler 的执行结果，或错误描述。
        """

        if context is None:
            context = Context(raw_text=text)

        parsed = self.parse(text, dry_run=False, context=context)
        if parsed.get("error"):
            return parsed

        handler = parsed["handler"]
        params = dict(parsed["params"])

        sig = inspect.signature(handler)
        if "ctx" in sig.parameters:
            params["ctx"] = context

        async def final_handler():
            if inspect.iscoroutinefunction(handler):
                return await handler(**params)
            return handler(**params)

        chain: list[list[Callable]] = []
        current = self
        while current:
            chain.append(current.middlewares)
            current = current.parent
        middlewares: list[Callable] = [mw for level in reversed(chain) for mw in level]

        async def run_with_middlewares(idx: int) -> Any:
            if idx >= len(middlewares):
                return await final_handler()
            mw = middlewares[idx]
            next_idx = idx + 1
            return await mw(parsed, lambda: run_with_middlewares(next_idx))

        return await run_with_middlewares(0)
