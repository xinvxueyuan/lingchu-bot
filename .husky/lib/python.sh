#!/usr/bin/env bash
# shellcheck shell=bash
#
# Source library file — sourced by .husky/pre-commit, not executed directly.
# Provides: run_python_checks() — Python-specific pre-commit phases.
#
# Phases included:
#   - Phase 2.5: 忽略注释防回退（src/ 新增 # noqa 告警，非阻断）
#   - Phase 4:   Pyright 类型检查（ty 已由 prek 处理，此处不再重复）
#   - Phase 5:   pytest 测试
#
# REMOVED (由 prek.toml 中的 ruff/ruff-format/ty 钩子接管):
#   - Phase 3: Ruff lint + Ruff format
#   - Phase 4 中的 ty 类型检查
#
# Depends on (provided by detect.sh):
#   GIT_CMD, UV_CMD, HAS_PYTHON, HAS_PY_CONFIG, NEEDS_PYTHON_CHECK, STAGED_FILES

# run_python_checks — 执行 Python 相关 phase
run_python_checks() {
    # ── Phase 2.5: 忽略注释防回退（秒级）──────────────────
    # 非阻断：仅告警 src/ 中新增的 # noqa 注释（tests/ 不检查）
    # 内联 noqa 已迁移至 pyproject.toml [tool.ruff.lint.per-file-ignores]，
    # 此检查防止 src/ 重新引入内联 noqa；CI 会做更严格的审计
    if [ "$HAS_PYTHON" = true ]; then
        STAGED_SRC_PY=$(printf '%s\n' "$STAGED_FILES" | grep -E '^src/.*\.py$' || true)
        if [ -n "$STAGED_SRC_PY" ]; then
            # 仅检查新增行（diff 中以 + 开头），避免对存量 noqa 误报
            # shellcheck disable=SC2086
            NEW_NOQA=$("$GIT_CMD" diff --cached --unified=0 -- $STAGED_SRC_PY 2>/dev/null | grep -E '^\+' | grep -F '# noqa' || true)
            if [ -n "$NEW_NOQA" ]; then
                echo "⚠️  检测到 src/ 中新增 # noqa 注释："
                printf '%s\n' "$NEW_NOQA"
                echo "   内联 noqa 已迁移至 pyproject.toml [tool.ruff.lint.per-file-ignores]，"
                echo "   请将抑制规则移至 per-file-ignores 配置，或在注释中说明特殊理由。"
                echo "   （此告警不阻断提交，但会在 CI 中再次审计）"
            fi
        fi
    fi

    # ── Phase 3 (Ruff lint + Ruff format) 已移除 ──────────
    # Ruff lint 与 Ruff format 现由 prek.toml 中的 ruff (args=["--fix"]) 与
    # ruff-format 钩子在 Phase 1 统一处理，此处不再重复执行，避免双重运行。

    # ── Phase 4: 类型检查（十秒级）────────────────────────
    # 仅运行 Pyright；ty 已由 prek.toml 中的 ty 钩子在 Phase 1 处理
    if [ "$NEEDS_PYTHON_CHECK" = true ] && [ -n "$UV_CMD" ]; then
        echo "🔍 正在运行 Pyright 类型检查..."
        "$UV_CMD" run -m pyright .
        if [ $? -ne 0 ]; then
            echo "❌ Pyright 类型检查失败，请修复后重新提交。"
            exit 1
        fi
    else
        echo "⏭️  无 Python 变更，跳过 Pyright 类型检查。"
    fi

    # ── Phase 5: 测试（十秒级）────────────────────────────
    if [ "$NEEDS_PYTHON_CHECK" = true ] && [ -n "$UV_CMD" ]; then
        echo "🧪 正在运行 pytest..."
        "$UV_CMD" run -m pytest -x -q
        if [ $? -ne 0 ]; then
            echo "❌ pytest 测试失败，请修复后重新提交。"
            exit 1
        fi
    else
        echo "⏭️  无 Python 变更，跳过 pytest 测试。"
    fi
}
