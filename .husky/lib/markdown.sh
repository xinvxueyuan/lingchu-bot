#!/usr/bin/env bash
# shellcheck shell=bash
#
# Source library file — sourced by .husky/pre-commit, not executed directly.
# Provides: run_markdown_checks() — markdownlint pre-commit phase.
#
# Phases included:
#   - Phase 2: markdownlint-cli2（.md 变更触发，秒级）
#
# Depends on (provided by detect.sh):
#   GIT_CMD, PNPM_RUNNER, run_pnpm, HAS_MARKDOWN

# run_markdown_checks — 执行 Markdown 相关 phase
run_markdown_checks() {
    # ── Phase 2: Markdownlint（秒级）──────────────────────────
    if [ "$HAS_MARKDOWN" = true ] && [ -n "$PNPM_RUNNER" ]; then
        echo "📝 正在运行 markdownlint-cli2..."
        run_pnpm exec markdownlint-cli2
        if [ $? -ne 0 ]; then
            echo "ℹ️  markdownlint 发现问题，正在尝试自动修复..."
            run_pnpm exec markdownlint-cli2 --fix
            if [ $? -ne 0 ]; then
                echo "❌ markdownlint 自动修复失败，请手动修复后重新提交。"
                exit 1
            fi
            echo "ℹ️  markdownlint 自动修复成功，正在暂存..."
            "$GIT_CMD" add -u
            echo "📝 正在重新验证 markdownlint..."
            run_pnpm exec markdownlint-cli2
            if [ $? -ne 0 ]; then
                echo "❌ markdownlint 验证失败，请手动修复后重新提交。"
                exit 1
            fi
        fi
    else
        echo "⏭️  无 Markdown 变更，跳过 markdownlint。"
    fi
}
