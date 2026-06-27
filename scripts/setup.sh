#!/usr/bin/env bash
# ============================================================================
# Lingchu Bot — 跨平台项目初始化脚本
# Cross-platform project initialization script
#
# 支持操作系统:
#   - Linux (Debian/Ubuntu, Arch, Fedora)
#   - macOS (Intel & Apple Silicon)
#   - Windows (Git Bash / WSL2)
#
# 用法:
#   chmod +x scripts/setup.sh
#   ./scripts/setup.sh            # 交互模式（默认）
#   ./scripts/setup.sh --help     # 查看帮助
#   ./scripts/setup.sh --no-git   # 跳过 Git 初始化
#   ./scripts/setup.sh --quick    # 快速模式，跳过可选步骤
# ============================================================================

set -euo pipefail

# ── 版本与常量 ──────────────────────────────────────────────────────────────
SCRIPT_VERSION="1.0.0"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="lingchu-bot"
PYTHON_MIN_VERSION="3.13"
NODE_MIN_VERSION="20"
PNPM_REQUIRED_VERSION="9"

# ANSI 颜色 / Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'  # No Color

# ── 帮助信息 ─────────────────────────────────────────────────────────────────

show_help() {
    cat <<'HELP_EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                    Lingchu Bot 项目初始化脚本                            ║
║               Cross-platform Project Setup Script                        ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  用法 / Usage:                                                           ║
║     ./scripts/setup.sh                   交互模式执行全部步骤             ║
║     ./scripts/setup.sh --quick           快速模式（跳过可选步骤）         ║
║     ./scripts/setup.sh --no-git          跳过 Git 仓库初始化             ║
║     ./scripts/setup.sh --help            显示此帮助信息                   ║
║     ./scripts/setup.sh --version         显示版本号                       ║
║                                                                          ║
║  功能 / Features:                                                        ║
║     1. 检测操作系统与必要工具链                                           ║
║     2. 安装项目依赖（Python + Node.js）                                  ║
║     3. 生成环境变量配置文件                                               ║
║     4. 配置 Git 钩子（husky）                                            ║
║     5. 初始化 Git 仓库（可选）                                           ║
║     6. Playwright 浏览器安装（可选）                                     ║
║     7. 最终验证与启动指引                                                 ║
║                                                                          ║
║  系统要求 / Requirements:                                                ║
║     - Python ${PYTHON_MIN_VERSION}+ (推荐通过 uv 管理)                    ║
║     - Node.js ${NODE_MIN_VERSION}+                                        ║
║     - pnpm ${PNPM_REQUIRED_VERSION}+                                      ║
║     - Git 2.30+                                                          ║
║     - uv  (Python 包管理器)                                              ║
║                                                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
HELP_EOF
    exit 0
}

# ── 参数解析 ─────────────────────────────────────────────────────────────────

SKIP_GIT=false
QUICK_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)    show_help ;;
        --version|-V) echo "setup.sh version ${SCRIPT_VERSION}"; exit 0 ;;
        --no-git)     SKIP_GIT=true; shift ;;
        --quick)      QUICK_MODE=true; shift ;;
        *)            echo -e "${RED}未知选项: $1${NC}"; show_help ;;
    esac
done

# ── 工具函数 ─────────────────────────────────────────────────────────────────

log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()    { echo; echo -e "${CYAN}━━━ ${BOLD}$*${NC}${CYAN} ━━━${NC}"; }
log_substep() { echo -e "  ${DIM}→${NC} $*"; }

# 安全确认提示（需输入 y/yes 确认）
confirm() {
    local prompt="${1:-继续执行?} [y/N] "
    local answer
    echo -ne "${YELLOW}${prompt}${NC}"
    read -r answer
    case "${answer,,}" in
        y|yes) return 0 ;;
        *)     return 1 ;;
    esac
}

# 运行命令并检查退出码
run_with_check() {
    local desc="$1"
    shift
    log_substep "${desc}..."
    if "$@" 2>&1 | while IFS= read -r line; do log_substep "  ${line}"; done; then
        # Check exit code of the piped command — use ${PIPESTATUS[0]}
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            return 0
        fi
    fi
    return 1
}

# ── 步骤1: 操作系统检测 ─────────────────────────────────────────────────────

detect_os() {
    log_step "步骤 1/8: 环境检测 — 识别操作系统"

    local os=""
    local os_family=""
    local pkg_manager=""

    case "$(uname -s)" in
        Linux*)
            os="linux"
            if grep -qi microsoft /proc/version 2>/dev/null; then
                os_family="wsl2"
                log_info "检测到 WSL2 (Windows Subsystem for Linux)"
            else
                os_family="linux"
                log_info "检测到 Linux 操作系统"
            fi
            # 检测包管理器
            if command -v apt-get &>/dev/null; then
                pkg_manager="apt"
            elif command -v pacman &>/dev/null; then
                pkg_manager="pacman"
            elif command -v dnf &>/dev/null; then
                pkg_manager="dnf"
            elif command -v yum &>/dev/null; then
                pkg_manager="yum"
            elif command -v zypper &>/dev/null; then
                pkg_manager="zypper"
            else
                pkg_manager="unknown"
            fi
            ;;
        Darwin*)
            os="darwin"
            os_family="macos"
            pkg_manager="brew"
            log_info "检测到 macOS ($(uname -m))"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            os="windows"
            os_family="windows"
            pkg_manager="choco"
            log_info "检测到 Windows (Git Bash / MSYS2)"
            ;;
        *)
            log_warn "未知操作系统: $(uname -s)，可能部分功能不可用"
            os="unknown"
            os_family="unknown"
            pkg_manager="unknown"
            ;;
    esac

    # 导出供后续使用
    OS="$os"
    OS_FAMILY="$os_family"
    PKG_MANAGER="$pkg_manager"

    log_success "操作系统: ${os} (${os_family}) | 包管理器: ${pkg_manager}"
    echo
}

# ── 步骤2: 工具链检测 ───────────────────────────────────────────────────────

detect_toolchain() {
    log_step "步骤 2/8: 环境检测 — 验证工具链"

    local all_found=true
    local missing_tools=()

    # 检测 Git
    if command -v git &>/dev/null; then
        local git_ver
        git_ver="$(git --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "unknown")"
        log_success "Git ${git_ver}"
    else
        log_warn "Git 未安装"
        missing_tools+=("git")
        all_found=false
    fi

    # 检测 Python
    if command -v python3 &>/dev/null; then
        local py_ver
        py_ver="$(python3 --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1 || echo "unknown")"
        if [[ "$(printf '%s\n' "${PYTHON_MIN_VERSION}" "${py_ver}" | sort -V | head -1)" == "${PYTHON_MIN_VERSION}" ]]; then
            log_success "Python ${py_ver} (满足 >=${PYTHON_MIN_VERSION})"
        else
            log_warn "Python ${py_ver} 版本过低，需要 >=${PYTHON_MIN_VERSION}"
            all_found=false
        fi
    else
        log_warn "Python3 未安装"
        missing_tools+=("python3")
        all_found=false
    fi

    # 检测 uv
    if command -v uv &>/dev/null; then
        local uv_ver
        uv_ver="$(uv --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1 || echo "unknown")"
        log_success "uv ${uv_ver}"
    else
        log_warn "uv 未安装 — 推荐安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
        missing_tools+=("uv")
        all_found=false
    fi

    # 检测 Node.js
    if command -v node &>/dev/null; then
        local node_ver
        node_ver="$(node --version 2>/dev/null | sed 's/^v//' | cut -d. -f1 || echo "0")"
        if [[ "$node_ver" -ge "$NODE_MIN_VERSION" ]] 2>/dev/null; then
            log_success "Node.js $(node --version) (满足 >=${NODE_MIN_VERSION})"
        else
            log_warn "Node.js 版本过低 (当前: $(node --version))，需要 >=${NODE_MIN_VERSION}"
            all_found=false
        fi
    else
        log_warn "Node.js 未安装"
        missing_tools+=("node")
        all_found=false
    fi

    # 检测 pnpm
    if command -v pnpm &>/dev/null; then
        local pnpm_ver
        pnpm_ver="$(pnpm --version 2>/dev/null | cut -d. -f1 || echo "0")"
        if [[ "$pnpm_ver" -ge "$PNPM_REQUIRED_VERSION" ]] 2>/dev/null; then
            log_success "pnpm $(pnpm --version) (满足 >=${PNPM_REQUIRED_VERSION})"
        else
            log_warn "pnpm 版本过低 ($(pnpm --version))，需要 >=${PNPM_REQUIRED_VERSION}"
            log_substep "  升级: npm install -g pnpm@latest"
            all_found=false
        fi
    elif command -v npm &>/dev/null; then
        log_warn "pnpm 未安装。正在通过 npm 安装..."
        npm install -g pnpm 2>&1 | while IFS= read -r line; do log_substep "  ${line}"; done
        if command -v pnpm &>/dev/null; then
            log_success "pnpm $(pnpm --version) 已自动安装"
        else
            log_warn "pnpm 自动安装失败，请手动安装: npm install -g pnpm"
            missing_tools+=("pnpm")
            all_found=false
        fi
    else
        log_warn "npm/pnpm 均未安装"
        missing_tools+=("pnpm")
        all_found=false
    fi

    echo
    if [[ "$all_found" == false ]]; then
        log_warn "部分工具缺失，请先安装:"
        for tool in "${missing_tools[@]}"; do
            case "$tool" in
                git)      echo "    - Git:   https://git-scm.com/downloads" ;;
                python3)  echo "    - Python: https://www.python.org/downloads/" ;;
                uv)       echo "    - uv:    curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
                node)     echo "    - Node.js: https://nodejs.org/" ;;
                pnpm)     echo "    - pnpm:  npm install -g pnpm" ;;
            esac
        done
        echo
        if ! confirm "是否仍然继续执行？（部分功能可能不可用）"; then
            log_info "安装完成后请重新运行此脚本。退出。"
            exit 1
        fi
    else
        log_success "所有工具链检查通过"
    fi
}

# ── 步骤3: 安装系统依赖（按操作系统） ─────────────────────────────────────────

install_system_deps() {
    log_step "步骤 3/8: 系统依赖安装"

    case "$OS_FAMILY" in
        linux|wsl2)
            case "$PKG_MANAGER" in
                apt)
                    log_substep "检测到 apt 包管理器 (Debian/Ubuntu)"
                    if confirm "是否安装 Playwright 系统依赖（libnss3, libatk等）?"; then
                        sudo apt-get update -qq 2>/dev/null || true
                        sudo apt-get install -y -qq \
                            libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
                            libgbm1 libasound2 2>&1 | tail -5
                        log_success "系统依赖安装完成"
                    else
                        log_info "跳过系统依赖安装"
                    fi
                    ;;
                pacman)
                    log_substep "检测到 pacman 包管理器 (Arch Linux)"
                    if confirm "是否安装 Playwright 系统依赖?"; then
                        sudo pacman -S --noconfirm \
                            nss atk at-spi2-atk libdrm libxkbcommon \
                            alsa-lib 2>&1 | tail -3
                        log_success "系统依赖安装完成"
                    else
                        log_info "跳过系统依赖安装"
                    fi
                    ;;
                dnf|yum)
                    log_substep "检测到 RPM 包管理器 (Fedora/RHEL)"
                    if confirm "是否安装 Playwright 系统依赖?"; then
                        sudo "$PKG_MANAGER" install -y \
                            nss atk at-spi2-atk libdrm libxkbcommon \
                            alsa-lib 2>&1 | tail -3
                        log_success "系统依赖安装完成"
                    else
                        log_info "跳过系统依赖安装"
                    fi
                    ;;
                *)
                    log_warn "不支持的包管理器 (${PKG_MANAGER})，请手动安装 Playwright 系统依赖"
                    ;;
            esac
            ;;
        macos)
            if command -v brew &>/dev/null; then
                if confirm "是否安装 Playwright 系统依赖?"; then
                    brew install --cask playwright 2>/dev/null || true
                    log_success "系统依赖安装完成"
                else
                    log_info "跳过系统依赖安装"
                fi
            else
                log_info "未检测到 Homebrew，跳过系统依赖安装"
            fi
            ;;
        windows)
            log_info "Windows 环境：Playwright 依赖已内置，无需额外安装"
            ;;
        *)
            log_warn "未知操作系统，跳过系统依赖安装"
            ;;
    esac
    echo
}

# ── 步骤4: 安装项目依赖 ─────────────────────────────────────────────────────

install_deps() {
    log_step "步骤 4/8: 项目依赖安装"

    # 4a. Python 依赖 (uv sync)
    if command -v uv &>/dev/null; then
        log_substep "安装 Python 依赖 (uv sync --frozen)..."
        log_info "Python 依赖包数量较多，首次安装可能需要 1-3 分钟"
        if uv sync --frozen 2>&1; then
            log_success "Python 依赖安装完成"
        else
            log_error "Python 依赖安装失败"
            log_substep "尝试: uv sync (不锁定版本)"
            if uv sync 2>&1; then
                log_success "Python 依赖安装完成（非锁定模式）"
            else
                log_error "Python 依赖安装失败，请检查网络连接"
                return 1
            fi
        fi
    else
        log_warn "uv 未安装，跳过 Python 依赖安装"
    fi
    echo

    # 4b. Node.js 依赖 (pnpm install)
    if command -v pnpm &>/dev/null; then
        log_substep "安装 Node.js 依赖 (pnpm install)"
        log_info "Node.js 依赖包数量较多，首次安装可能需要 2-5 分钟"
        if pnpm install 2>&1 | tail -5; then
            log_success "Node.js 依赖安装完成"
        else
            log_error "Node.js 依赖安装失败，请检查网络连接和 npm 注册表"
            return 1
        fi
    else
        log_warn "pnpm 未安装，跳过 Node.js 依赖安装"
    fi
    echo

    # 4c. Git hooks (husky)
    if [[ -f "$PROJECT_ROOT/package.json" ]] && command -v pnpm &>/dev/null; then
        log_substep "配置 Git 钩子 (husky)..."
        if pnpm exec husky 2>&1 | tail -3; then
            log_success "Git 钩子配置完成"
        else
            log_warn "husky 配置可能未完全成功，不影响主要功能"
        fi
    fi
    echo
}

# ── 步骤5: 环境变量配置 ───────────────────────────────────────────────────────

setup_env() {
    log_step "步骤 5/8: 环境变量配置"

    local env_example="$PROJECT_ROOT/.env.example"
    local env_file="$PROJECT_ROOT/.env"
    local env_dev="$PROJECT_ROOT/.env.development"
    local env_test="$PROJECT_ROOT/.env.test"
    local env_prod="$PROJECT_ROOT/.env.production"

    # 从 .env.example 生成 .env
    if [[ -f "$env_example" ]]; then
        if [[ ! -f "$env_file" ]]; then
            cp "$env_example" "$env_file"
            log_success "已创建 ${env_file}（基于 .env.example）"
            log_substep "请根据实际环境编辑 ${env_file} 中的配置"
        else
            log_info "${env_file} 已存在，跳过创建"
            log_substep "如需重新生成，请先删除: rm ${env_file}"
        fi
    else
        log_warn ".env.example 不存在，跳过 .env 生成"
    fi

    # 生成 .env.development
    if [[ ! -f "$env_dev" ]]; then
        cat > "$env_dev" <<'ENV_DEV'
# ── 开发环境配置 ────────────────────────────────────────────────────────────
ENVIRONMENT=development
HOST=127.0.0.1
PORT=8080
LOG_LEVEL=DEBUG
LOCALSTORE_USE_CWD=true
ALEMBIC_STARTUP_CHECK=false
COMMAND_START=["/", ""]
COMMAND_SEP=[".", " "]
DRIVER=~fastapi+~httpx+~websockets
ENV_DEV
        log_success "已创建 ${env_dev}"
    else
        log_info "${env_dev} 已存在，跳过"
    fi

    # 生成 .env.test
    if [[ ! -f "$env_test" ]]; then
        cat > "$env_test" <<'ENV_TEST'
# ── 测试环境配置 ────────────────────────────────────────────────────────────
ENVIRONMENT=test
HOST=127.0.0.1
PORT=8080
LOG_LEVEL=DEBUG
LOCALSTORE_USE_CWD=true
ALEMBIC_STARTUP_CHECK=false
COMMAND_START=["/", ""]
COMMAND_SEP=[".", " "]
DRIVER=~fastapi+~httpx+~websockets
ENV_TEST
        log_success "已创建 ${env_test}"
    else
        log_info "${env_test} 已存在，跳过"
    fi

    # 生成 .env.production
    if [[ ! -f "$env_prod" ]]; then
        cat > "$env_prod" <<'ENV_PROD'
# ── 生产环境配置 ────────────────────────────────────────────────────────────
ENVIRONMENT=production
HOST=0.0.0.0
PORT=8080
LOG_LEVEL=INFO
LOCALSTORE_USE_CWD=false
ALEMBIC_STARTUP_CHECK=true
COMMAND_START=["/", ""]
COMMAND_SEP=[".", " "]
DRIVER=~fastapi+~httpx+~websockets
ENV_PROD
        log_success "已创建 ${env_prod}"
    else
        log_info "${env_prod} 已存在，跳过"
    fi

    # 确保 .env 文件不被 Git 跟踪（已在 .gitignore 中配置）
    echo
    log_substep "验证 .gitignore 配置..."
    if grep -q '^.env$' "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
        log_success ".gitignore 已正确忽略 .env 文件"
    else
        log_warn ".gitignore 中未找到 .env 忽略规则，建议手动添加"
    fi
    echo
}

# ── 步骤6: 项目结构创建 ───────────────────────────────────────────────────────

create_project_structure() {
    log_step "步骤 6/8: 项目目录结构确认"

    local required_dirs=(
        "$PROJECT_ROOT/src/plugins/nonebot_plugin_lingchu_bot"
        "$PROJECT_ROOT/tests"
        "$PROJECT_ROOT/apps/docs"
        "$PROJECT_ROOT/config"
        "$PROJECT_ROOT/data"
    )

    local all_exist=true
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_success "目录存在: ${dir#$PROJECT_ROOT/}"
        else
            log_warn "目录不存在: ${dir#$PROJECT_ROOT/}"
            all_exist=false
        fi
    done

    # 创建本地运行所需的临时数据目录（.gitignore 已忽略）
    local runtime_dirs=(
        "$PROJECT_ROOT/.local"
    )
    for dir in "${runtime_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "已创建运行时目录: ${dir#$PROJECT_ROOT/}"
        fi
    done

    if [[ "$all_exist" == true ]]; then
        log_success "所有必需目录已就绪"
    else
        log_warn "部分目录缺失，建议重新克隆完整代码库"
        log_substep "  git clone https://github.com/xinvxueyuan/lingchu-bot.git"
    fi
    echo
}

# ── 步骤7: Git 仓库初始化与 Playwright 安装 ──────────────────────────────────

setup_git_and_playwright() {
    log_step "步骤 7/8: 可选配置"

    # 7a. Git 仓库初始化
    if [[ "$SKIP_GIT" == false ]]; then
        if [[ -d "$PROJECT_ROOT/.git" ]]; then
            log_success "Git 仓库已存在"
            local current_branch
            current_branch="$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
            log_substep "当前分支: ${current_branch}"
        else
            if confirm "初始化 Git 仓库?"; then
                log_substep "初始化 Git 仓库..."
                git -C "$PROJECT_ROOT" init
                log_success "Git 仓库已初始化"

                log_substep "创建初始提交..."
                git -C "$PROJECT_ROOT" add -A
                git -C "$PROJECT_ROOT" commit -m "🎉 feat: 初始项目设置" 2>/dev/null && \
                    log_success "初始提交已创建" || \
                    log_warn "初始提交创建失败（可能无变更）"
            else
                log_info "跳过 Git 仓库初始化"
            fi
        fi
    else
        log_info "跳过 Git 仓库初始化 (--no-git)"
    fi

    # 7b. Playwright 浏览器安装
    if command -v pnpm &>/dev/null && [[ -f "$PROJECT_ROOT/apps/docs/package.json" ]]; then
        if [[ "$QUICK_MODE" == false ]] && confirm "是否安装 Playwright 浏览器（用于文档测试）?"; then
            log_substep "安装 Playwright Chromium 浏览器..."
            if pnpm --dir "$PROJECT_ROOT/apps/docs" exec playwright install chromium 2>&1 | tail -3; then
                log_success "Playwright Chromium 安装完成"
            else
                log_warn "Playwright 安装失败，请手动运行: pnpm --filter docs exec playwright install"
            fi
        else
            log_info "跳过 Playwright 浏览器安装"
            log_substep "如需后续安装: pnpm --filter docs exec playwright install"
        fi
    fi
    echo
}

# ── 步骤8: 最终验证与指引 ────────────────────────────────────────────────────

final_verify() {
    log_step "步骤 8/8: 验证与后续指引"

    local all_pass=true

    echo -e "  ${BOLD}── 依赖验证 ──${NC}"

    # 验证 Python 环境
    if command -v uv &>/dev/null; then
        local uv_venv="$PROJECT_ROOT/.venv"
        if [[ -f "$uv_venv/bin/python" ]]; then
            local py_ver
            py_ver="$("$uv_venv/bin/python" --version 2>/dev/null || echo "unknown")"
            log_success "Python 虚拟环境: ${py_ver}"
        else
            log_warn "Python 虚拟环境未找到 (预期: .venv/)"
            log_substep "  运行: uv sync"
        fi
    fi

    # 验证 Node.js 依赖
    if command -v pnpm &>/dev/null; then
        if [[ -d "$PROJECT_ROOT/node_modules" ]]; then
            log_success "Node.js 依赖已安装 (node_modules/)"
        else
            log_warn "Node.js 依赖未安装"
            log_substep "  运行: pnpm install"
        fi
    fi

    # 验证 Git hooks
    if [[ -x "$PROJECT_ROOT/.husky/pre-commit" ]]; then
        log_success "Git 钩子已配置 (.husky/)"
    else
        log_warn "Git 钩子未配置"
        log_substep "  运行: pnpm exec husky"
    fi

    # 验证环境变量
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        log_success "环境变量文件已配置 (.env)"
    else
        log_warn "环境变量文件未配置"
        log_substep "  运行: cp .env.example .env"
    fi

    echo
    echo -e "  ${BOLD}── 快速启动命令 ──${NC}"
    echo
    if command -v uv &>/dev/null; then
        echo -e "    ${GREEN}uv run nb run${NC}              启动机器人"
    fi
    echo -e "    ${GREEN}cd apps/docs${NC}"
    echo -e "    ${GREEN}pnpm dev${NC}                    启动文档站点"
    echo
    echo -e "    ${GREEN}task check${NC}                   运行全部静态检查"
    echo -e "    ${GREEN}task test${NC}                    运行全部测试"
    echo -e "    ${GREEN}task i18n${NC}                    更新国际化翻译"
    echo

    echo -e "  ${BOLD}── 项目资源 ──${NC}"
    echo
    echo -e "    文档站点:     https://lingchu-bot.vercel.app"
    echo -e "    源码仓库:     https://github.com/xinvxueyuan/lingchu-bot"
    echo -e "    问题反馈:     https://github.com/xinvxueyuan/lingchu-bot/issues"
    echo

    if [[ "$all_pass" == true ]]; then
        echo -e "${GREEN}${BOLD}"
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║              🎉 项目初始化完成！Setup complete!              ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
}

# ── 主流程 ────────────────────────────────────────────────────────────────────

main() {
    echo
    echo -e "${BLUE}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║              Lingchu Bot 项目初始化脚本 v${SCRIPT_VERSION}              ║"
    echo "║            Cross-platform Project Setup Script               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "  项目目录: ${CYAN}${PROJECT_ROOT}${NC}"
    echo -e "  目标系统: ${CYAN}Linux / macOS / Windows${NC}"
    echo

    if ! confirm "开始执行 Lingchu Bot 项目初始化流程?"; then
        log_info "用户取消，退出。"
        exit 0
    fi

    detect_os
    detect_toolchain
    install_system_deps
    install_deps
    setup_env
    create_project_structure
    setup_git_and_playwright
    final_verify
}

# ── 入口 ──────────────────────────────────────────────────────────────────────
main
