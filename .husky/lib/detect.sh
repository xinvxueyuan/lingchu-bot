#!/usr/bin/env bash
# shellcheck shell=bash
#
# Source library file — sourced by .husky/pre-commit, not executed directly.
# Provides: tool resolution helpers, one-shot environment probing, staged-file
# type detection. Exposes functions and HAS_*/NEEDS_* flags to the caller.
#
# POSIX-sh compatible (parent .husky/pre-commit runs under `sh -e`); the
# shebang above is informational and ignored when sourced.

# ── 工具解析辅助函数 ────────────────────────────────────

# first_runnable <command>... — 返回第一个可执行且能启动的命令
first_runnable() {
    for candidate in "$@"; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

# first_cmd_runnable <command.cmd>... — 返回第一个可通过 cmd.exe 启动的 Windows 命令
first_cmd_runnable() {
    if ! command -v cmd.exe >/dev/null 2>&1; then
        return 1
    fi
    for candidate in "$@"; do
        if command -v "$candidate" >/dev/null 2>&1 && cmd.exe /c "$candidate" --version >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

# resolve_native <bin>... — 返回第一个可在当前 shell 直接调用的命令
resolve_native() {
    first_runnable "$@" && return 0
    return 1
}

# resolve_cmd <bin>... — 返回第一个可通过 cmd.exe 调用的 .cmd shim
resolve_cmd() {
    first_cmd_runnable "$@" && return 0
    return 1
}

# resolve_js <bin>
#   解析顺序：node_modules/.bin/<bin> → 全局 PATH → 全局 .cmd shim
#   输出：native:<path> | cmd:<path>（失败返回 1，调用方决定兜底）
#   Windows 上 .cmd shim 必须经 cmd.exe 包装，直接 $path 调用会被 Git Bash 静默跳过
resolve_js() {
    local bin="$1"
    local bin_path=""

    # 1. 本地 node_modules/.bin（devDep 已装时直接命中，零下载）
    if [ -x "node_modules/.bin/$bin" ]; then
        bin_path="node_modules/.bin/$bin"
    elif [ -f "node_modules/.bin/$bin.cmd" ]; then
        bin_path="node_modules/.bin/$bin.cmd"
    fi
    if [ -n "$bin_path" ]; then
        if printf '%s\n' "$bin_path" | grep -q '\.cmd$'; then
            printf 'cmd:%s\n' "$bin_path"
        else
            printf 'native:%s\n' "$bin_path"
        fi
        return 0
    fi

    # 2. 全局 PATH
    local resolved
    resolved=$(resolve_native "$bin" "$bin.exe") && { printf 'native:%s\n' "$resolved"; return 0; }
    resolved=$(resolve_cmd "$bin.cmd") && { printf 'cmd:%s\n' "$resolved"; return 0; }
    return 1
}

# run_resolved <resolver-output> <args...>
run_resolved() {
    case "$1" in
        native:*) local bin="${1#native:}"; shift; "$bin" "$@" ;;
        cmd:*) local bin="${1#cmd:}"; shift; cmd.exe /c "$bin" "$@" ;;
        *) return 127 ;;
    esac
}

# select_js_runner <bin> — 解析 pnpm/npx 等 wrapper 工具自身
select_js_runner() {
    local resolved
    resolved=$(resolve_native "$1" "$1.exe") && { printf 'native:%s\n' "$resolved"; return 0; }
    resolved=$(resolve_cmd "$1.cmd") && { printf 'cmd:%s\n' "$resolved"; return 0; }
    return 1
}

run_pnpm() {
    case "$PNPM_RUNNER" in
        native:*) "${PNPM_RUNNER#native:}" "$@" ;;
        cmd:*) cmd.exe /c "${PNPM_RUNNER#cmd:}" "$@" ;;
        *) return 127 ;;
    esac
}

# ── 一次性探测环境（缓存到变量）────────────────────────
GIT_CMD=$(first_runnable git git.exe)
UV_CMD=$(first_runnable uv uv.exe)
PNPM_RUNNER=$(select_js_runner pnpm)

if [ -z "$GIT_CMD" ]; then
    echo "❌ 未找到可运行的 git，无法检测暂存区变更。"
    exit 1
fi

# 预解析 JS 工具：devDep 命中本地 bin 时直接调用，避免 npx 重新下载
GITNEXUS_RESOLVED=$(resolve_js gitnexus || true)

# react-doctor 不在 devDep 中：尝试全局命中，否则走 pnpm dlx（带 pnpm 缓存），
# 最后才用 npx（每次都重新拉包）
REACT_DOCTOR_RESOLVED=$(resolve_js react-doctor || true)
DLX_RUNNER=""
if [ -z "$REACT_DOCTOR_RESOLVED" ] && [ -n "$PNPM_RUNNER" ]; then
    DLX_RUNNER="pnpm"
elif [ -z "$REACT_DOCTOR_RESOLVED" ]; then
    DLX_RUNNER=$(select_js_runner npx || true)
fi

# ── 变更检测 ────────────────────────────────────────────
STAGED_FILES=$("$GIT_CMD" diff --cached --name-only --diff-filter=ACMR 2>/dev/null)

# has_pattern <glob_pattern>... — 任一模式匹配到暂存文件则返回 0
has_pattern() {
    for pattern in "$@"; do
        if printf '%s\n' "$STAGED_FILES" | grep -qE "$pattern"; then
            return 0
        fi
    done
    return 1
}

HAS_PYTHON=false
HAS_PY_CONFIG=false   # pyproject.toml / ruff.toml / uv.lock 等 Python 配置
HAS_MARKDOWN=false    # .md 文件变更

# ── Docs 文件分类（apps/docs/）─────────────────────────
HAS_DOCS_CODE=false     # .ts/.tsx/.mjs/.mts — 代码文件，触发 ESLint + check-types + Vitest
HAS_DOCS_TSX=false      # .tsx — React 组件，触发 React Doctor（CODE 的子集）
HAS_DOCS_CONTENT=false  # .mdx/.json — 内容文件，触发 check-types + Vitest（fumadocs-mdx 重新生成类型）
HAS_DOCS_MDX=false      # .mdx — MDX 内容文件，触发 ESLint（eslint-plugin-mdx 覆盖 .mdx）
HAS_DOCS_STYLE=false    # .css — 样式文件，触发 ESLint（CSS Modules 可能影响类型）
HAS_DOCS_CONFIG=false   # 配置文件（next.config.mjs/tsconfig.json 等），触发 ESLint + check-types + Vitest

# ── Packages 文件分类（packages/）──────────────────────
HAS_PACKAGES_CODE=false   # .ts/.tsx/.mjs/.mts/.js/.css — 代码/样式文件
HAS_PACKAGES_CONFIG=false # .json — 配置文件（含嵌套路径）

# markdownlint-cli2 范围由根目录 .markdownlint-cli2.jsonc 统一驱动（globs + ignores + config）
# 无参调用即可，无需在此维护 glob 列表

if has_pattern '\.py$'; then
    HAS_PYTHON=true
fi
if has_pattern '(^|/)(pyproject\.toml|ruff\.toml|\.ruff\.toml|uv\.lock|\.python-version)$'; then
    HAS_PY_CONFIG=true
fi

# Docs: 代码文件（.ts/.tsx/.mjs/.mts）
if has_pattern '^apps/docs/.*\.(ts|tsx|mjs|mts)$'; then
    HAS_DOCS_CODE=true
fi
# Docs: React 组件（.tsx，CODE 的子集，单独标记以触发 React Doctor）
if has_pattern '^apps/docs/.*\.tsx$'; then
    HAS_DOCS_TSX=true
fi
# Docs: 内容文件（.mdx/.json，fumadocs-mdx 据此生成类型）
if has_pattern '^apps/docs/.*\.(mdx|json)$'; then
    HAS_DOCS_CONTENT=true
fi
# Docs: MDX 文件（eslint-plugin-mdx 覆盖 .mdx，需触发 ESLint；.json 不触发）
if has_pattern '^apps/docs/.*\.mdx$'; then
    HAS_DOCS_MDX=true
fi
# Docs: 样式文件（.css）
if has_pattern '^apps/docs/.*\.css$'; then
    HAS_DOCS_STYLE=true
fi
# Docs: 配置文件（影响 lint/type/test 行为）
if has_pattern '^apps/docs/(next\.config\.mjs|source\.config\.ts|tsconfig\.json|vitest\.config\.ts|playwright\.config\.ts|eslint\.config\.mjs|postcss\.config\.mjs|package\.json)$'; then
    HAS_DOCS_CONFIG=true
fi

# Packages: 代码/样式文件（.ts/.tsx/.mjs/.mts/.js/.css）
if has_pattern '^packages/.*\.(ts|tsx|mjs|mts|js|css)$'; then
    HAS_PACKAGES_CODE=true
fi
# Packages: 配置文件（.json，含嵌套路径如 packages/ui/tsconfig.json）
if has_pattern '^packages/.*\.json$'; then
    HAS_PACKAGES_CONFIG=true
fi

# Markdown 文件
if has_pattern '\.md$'; then
    HAS_MARKDOWN=true
fi

NEEDS_PYTHON_CHECK=false
if [ "$HAS_PYTHON" = true ] || [ "$HAS_PY_CONFIG" = true ]; then
    NEEDS_PYTHON_CHECK=true
fi

# ── 派生条件 ──────────────────────────────────────────
# HAS_DOCS / HAS_PACKAGES / HAS_FRONTEND: 用于日志和兜底判断
HAS_DOCS=false
if [ "$HAS_DOCS_CODE" = true ] || [ "$HAS_DOCS_CONTENT" = true ] || [ "$HAS_DOCS_STYLE" = true ] || [ "$HAS_DOCS_CONFIG" = true ]; then
    HAS_DOCS=true
fi
HAS_PACKAGES=false
if [ "$HAS_PACKAGES_CODE" = true ] || [ "$HAS_PACKAGES_CONFIG" = true ]; then
    HAS_PACKAGES=true
fi
HAS_FRONTEND=false
if [ "$HAS_DOCS" = true ] || [ "$HAS_PACKAGES" = true ]; then
    HAS_FRONTEND=true
fi

# NEEDS_LINT: 代码/样式/文档配置/MDX 内容变更触发 ESLint（纯 .json 内容跳过）
NEEDS_LINT=false
if [ "$HAS_DOCS_CODE" = true ] || [ "$HAS_DOCS_STYLE" = true ] || [ "$HAS_DOCS_CONFIG" = true ] || [ "$HAS_DOCS_MDX" = true ] || [ "$HAS_PACKAGES_CODE" = true ]; then
    NEEDS_LINT=true
fi

# NEEDS_TYPE_CHECK: 任意前端变更触发（fumadocs-mdx 需重新生成类型，CSS Modules 可能影响类型）
NEEDS_TYPE_CHECK=false
if [ "$HAS_FRONTEND" = true ]; then
    NEEDS_TYPE_CHECK=true
fi

# NEEDS_REACT_DOCTOR: 仅 .tsx 变更触发（React 组件扫描）
NEEDS_REACT_DOCTOR=false
if [ "$HAS_DOCS_TSX" = true ]; then
    NEEDS_REACT_DOCTOR=true
fi

# NEEDS_DOCS_TEST: 代码/内容/配置变更触发 Vitest（纯样式 .css 跳过）
NEEDS_DOCS_TEST=false
if [ "$HAS_DOCS_CODE" = true ] || [ "$HAS_DOCS_CONTENT" = true ] || [ "$HAS_DOCS_CONFIG" = true ]; then
    NEEDS_DOCS_TEST=true
fi
