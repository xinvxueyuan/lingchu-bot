#!/usr/bin/env bash
# shellcheck shell=bash
#
# Source library file — sourced by .husky/pre-commit, not executed directly.
# Provides: run_frontend_checks() — frontend (apps/docs + packages) pre-commit phases.
#
# Phases included:
#   - Phase 6a: ESLint（代码/样式/配置/MDX 变更触发）
#   - Phase 6b: 类型检查 turbo run check-types（任意前端变更触发）
#   - Phase 6c: Docs Vitest（代码/内容/配置变更触发）
#   - Phase 6d: Docs Playwright Chromium 冒烟（任意 docs 变更触发）
#   - Phase 7:  React Doctor（仅 .tsx 变更触发）
#
# NOTE: 无独立 Prettier phase — Prettier 由 `task format` / `task fix` 在开发
# 工作流中运行，不在 pre-commit hook 中；ESLint 通过 eslint-config-prettier
# 关闭与 Prettier 冲突的规则，避免重复格式化。
#
# Depends on (provided by detect.sh):
#   GIT_CMD, PNPM_RUNNER, run_pnpm, run_resolved, REACT_DOCTOR_RESOLVED, DLX_RUNNER,
#   NEEDS_LINT, NEEDS_TYPE_CHECK, NEEDS_DOCS_TEST, NEEDS_REACT_DOCTOR,
#   HAS_DOCS, HAS_DOCS_CODE, HAS_DOCS_MDX, HAS_DOCS_CONFIG, HAS_PACKAGES_CODE

# run_frontend_checks — 执行前端相关 phase
run_frontend_checks() {
    # ── Phase 6a: ESLint（秒级，仅代码/样式/配置变更）──────────────────
    if [ "$NEEDS_LINT" = true ] && [ -n "$PNPM_RUNNER" ]; then
        echo "🔍 正在运行 ESLint (all workspaces)..."
        run_pnpm turbo run lint
        if [ $? -ne 0 ]; then
            echo "ℹ️  ESLint 发现问题，正在尝试自动修复..."
            # ESLint --fix 需要针对各个 workspace 执行
            if [ "$HAS_DOCS_CODE" = true ] || [ "$HAS_DOCS_MDX" = true ] || [ "$HAS_DOCS_CONFIG" = true ]; then
                run_pnpm --filter docs exec eslint . --fix
            fi
            if [ "$HAS_PACKAGES_CODE" = true ]; then
                run_pnpm --filter packages exec eslint . --fix 2>/dev/null || true
            fi
            echo "ℹ️  ESLint 自动修复完成，正在暂存..."
            "$GIT_CMD" add -u
            echo "🔍 正在重新验证 ESLint..."
            run_pnpm turbo run lint
            if [ $? -ne 0 ]; then
                echo "❌ ESLint 验证失败，请手动修复后重新提交。"
                exit 1
            fi
        fi
    else
        echo "⏭️  无代码/样式/配置变更，跳过 ESLint。"
    fi

    # ── Phase 6b: 类型检查（十秒级，任意前端变更）──────────────────────
    if [ "$NEEDS_TYPE_CHECK" = true ] && [ -n "$PNPM_RUNNER" ]; then
        echo "🔍 正在运行类型检查 (all workspaces)..."
        run_pnpm turbo run check-types
        if [ $? -ne 0 ]; then
            echo "❌ 类型检查失败，请修复后重新提交。"
            exit 1
        fi
    else
        echo "⏭️  无前端变更，跳过类型检查。"
    fi

    # ── Phase 6c: Docs Vitest（十秒级，代码/内容/配置变更）──────────────
    if [ "$NEEDS_DOCS_TEST" = true ] && [ -n "$PNPM_RUNNER" ]; then
        echo "🧪 正在运行 Docs Vitest..."
        run_pnpm --filter docs test
        if [ $? -ne 0 ]; then
            echo "❌ Docs 测试失败，请修复后重新提交。"
            exit 1
        fi
    fi

    # ── Phase 6d: Docs Playwright（Chromium 冒烟，任意 docs 变更）────────
    if [ "$HAS_DOCS" = true ] && [ -n "$PNPM_RUNNER" ]; then
        # 跨平台检查 Playwright Chromium 浏览器是否已安装
        # Linux/macOS: ~/.cache/ms-playwright   Windows: %LOCALAPPDATA%/ms-playwright
        PW_CHROMIUM_FOUND=false
        for pw_base in "${HOME}/.cache/ms-playwright" "${LOCALAPPDATA:+$LOCALAPPDATA/ms-playwright}"; do
            if [ -d "$pw_base" ] && command -v find >/dev/null 2>&1; then
                if find "$pw_base" -maxdepth 2 \( -name "chrome" -o -name "chrome.exe" -o -name "chrome-headless-shell" -o -name "chrome-headless-shell.exe" \) -type f 2>/dev/null | head -1 | grep -q .; then
                    PW_CHROMIUM_FOUND=true
                    break
                fi
            fi
        done
        if [ "$PW_CHROMIUM_FOUND" = false ]; then
            echo "⚠️  Playwright Chromium 浏览器未安装，跳过 Docs Playwright 冒烟测试。"
            echo "💡 运行 'pnpm --filter docs exec playwright install' 安装浏览器后再试。"
        else
            echo "🎭 正在运行 Docs Playwright (Chromium)..."
            run_pnpm --filter docs run test:e2e:hook
            if [ $? -ne 0 ]; then
                echo "❌ Docs Playwright 测试失败，请修复后重新提交。"
                exit 1
            fi
        fi
    fi

    # ── Phase 7: React Doctor（十秒级，仅 .tsx 变更）────────────────────
    if [ "$NEEDS_REACT_DOCTOR" = true ]; then
        if [ -n "$REACT_DOCTOR_RESOLVED" ]; then
            echo "🩺 正在运行 React Doctor..."
            NO_COLOR=1 run_resolved "$REACT_DOCTOR_RESOLVED" . --blocking error --no-telemetry --project docs
            if [ $? -ne 0 ]; then
                echo "❌ React Doctor 发现错误，请修复后重新提交。"
                echo "💡 运行 'pnpm doctor -- --verbose' 查看详细信息。"
                exit 1
            fi
        elif [ "$DLX_RUNNER" = "pnpm" ]; then
            # pnpm dlx 命中 pnpm 内容寻址缓存，后续调用零下载
            echo "🩺 正在运行 React Doctor (pnpm dlx 缓存)..."
            NO_COLOR=1 run_pnpm dlx -y react-doctor@latest . --blocking error --no-telemetry --project docs --yes
            if [ $? -ne 0 ]; then
                echo "❌ React Doctor 发现错误，请修复后重新提交。"
                echo "💡 运行 'pnpm doctor -- --verbose' 查看详细信息。"
                exit 1
            fi
        elif [ -n "$DLX_RUNNER" ]; then
            # 终极兜底：npx 每次都会重新下载（最慢路径）
            # 在非 Windows 系统上，cmd.exe 不可用，跳过 cmd shim 路径
            DLX_EXIT=0
            case "$DLX_RUNNER" in
                cmd:*)
                    if command -v cmd.exe >/dev/null 2>&1; then
                        echo "🩺 正在运行 React Doctor (npx 兜底)..."
                        NO_COLOR=1 cmd.exe /c "${DLX_RUNNER#cmd:}" -y react-doctor@latest . --blocking error --no-telemetry --project docs --yes
                        DLX_EXIT=$?
                    else
                        echo "⚠️  cmd.exe 不可用，跳过 React Doctor 检查。"
                    fi
                    ;;
                native:*)
                    echo "🩺 正在运行 React Doctor (npx 兜底)..."
                    NO_COLOR=1 "${DLX_RUNNER#native:}" -y react-doctor@latest . --blocking error --no-telemetry --project docs --yes
                    DLX_EXIT=$?
                    ;;
            esac
            if [ "$DLX_EXIT" -ne 0 ]; then
                echo "❌ React Doctor 发现错误，请修复后重新提交。"
                echo "💡 运行 'pnpm doctor -- --verbose' 查看详细信息。"
                exit 1
            fi
        else
            echo "⚠️  未找到 react-doctor / pnpm / npx，跳过 React Doctor 检查。"
        fi
    else
        echo "⏭️  无 .tsx 变更，跳过 React Doctor 检查。"
    fi
}
