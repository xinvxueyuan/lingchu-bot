# syntax=docker/dockerfile:1

# WebUI 前后端统一运行时单体镜像
# 从仓库根构建：docker build -f apps/webui/Dockerfile .
# 单进程：node dist/server/index.js 同时承载 /api（auth + 转发）与 静态 + SSR。
# 构建阶段产三份产物（build/client、build/server、dist/server），运行阶段仅生产依赖 + 产物。
#
# NPM_REGISTRY（build arg）：默认 npmmirror 镜像加速国内下载。
# 注意 pnpm 11 只认项目级 .npmrc（环境变量 npm_config_registry / --registry 参数均不生效）。
ARG NPM_REGISTRY=https://registry.npmmirror.com

# ── 构建阶段：安装 webui（含 dev）依赖并产出全部构建产物 ────────────────────
FROM node:24-alpine AS builder

WORKDIR /repo
ARG NPM_REGISTRY=https://registry.npmmirror.com

# 项目级 .npmrc 是 pnpm 一定读取的机制。
RUN echo "registry=${NPM_REGISTRY}" > .npmrc

# 先拷贝 workspace 清单与 lockfile（仅清单，不含源码）：
# workspace 共有 apps/docs、apps/lingc-cli、apps/webui、packages/typescript-config 四个包。
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY apps/webui/package.json apps/webui/package.json
COPY apps/lingc-cli/package.json apps/lingc-cli/package.json
COPY apps/docs/package.json apps/docs/package.json
COPY packages/typescript-config/package.json packages/typescript-config/package.json

# 移除 root devDependencies（gitnexus → @huggingface/transformers → onnxruntime-node/web
# 等数百 MB 二进制链，以及 turbo/prettier/gitmoji 等工具）——webui 依赖闭包完全独立于它们；
# 继而做非 frozen install：--frozen-lockfile 会强制 pull lockfile 固定版本
# （gitnexus@1.6.9 在 npmmirror 上同步滞后而 404），非 frozen 让 pnpm 在容器内重新解析，
# 跳过与 webui 无关的 root dev 依赖。fetch 参数容忍镜像网络抖动。
RUN node -e "const fs=require('fs');const p=JSON.parse(fs.readFileSync('package.json','utf8'));delete p.devDependencies;fs.writeFileSync('package.json',JSON.stringify(p,null,2))" \
    && corepack enable \
    && pnpm install --filter lingchu-bot-webui... --fetch-retries=6 --fetch-timeout=300000

# 拷贝 webui 源码后构建：
#   pnpm build        → build/client（静态资源）+ build/server（SSR 运行时）
#   pnpm build:server → dist/server（服务端编译产物）
# 注意：--exclude 必须显式排除宿主目录。Windows 宿主机上 pnpm 的 node_modules 是
# junction/symlink 结构，.dockerignore 的 **/node_modules/ 无法在 build context 打包时
# 完全过滤掉这些条目，COPY 会把宿主 node_modules 覆盖进容器、破坏上面刚完成的 install。
COPY --exclude="node_modules" --exclude="build" --exclude="dist" --exclude=".turbo" \
    apps/webui/ apps/webui/

# react-router build 和 tsc 需要 dev 依赖（vite / @react-router/dev / typescript），
# 上一层的 filter 安装已含 webui 自身 devDependencies。
RUN pnpm --filter lingchu-bot-webui run build \
    && pnpm --filter lingchu-bot-webui run build:server

# ── 运行阶段：仅生产依赖 + 构建产物，单进程启动 ─────────────────────────────
FROM node:24-alpine AS runtime

WORKDIR /app
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN echo "registry=${NPM_REGISTRY}" > .npmrc

# 与 builder 相同：拷全 workspace 清单，删 root devDeps，非 frozen --prod 安装。
# webui 生产闭包只有运行时依赖（hono、@hono/node-server、sharp 等），不携带任何构建工具。
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY apps/webui/package.json apps/webui/package.json
COPY apps/lingc-cli/package.json apps/lingc-cli/package.json
COPY apps/docs/package.json apps/docs/package.json
COPY packages/typescript-config/package.json packages/typescript-config/package.json

RUN node -e "const fs=require('fs');const p=JSON.parse(fs.readFileSync('package.json','utf8'));delete p.devDependencies;fs.writeFileSync('package.json',JSON.stringify(p,null,2))" \
    && corepack enable \
    && pnpm install --filter lingchu-bot-webui --prod --fetch-retries=6 --fetch-timeout=300000

# 只带构建产物，不携带构建工具（无 vite / react-router dev / typescript 等 dev 依赖）。
COPY --from=builder /repo/apps/webui/build apps/webui/build
COPY --from=builder /repo/apps/webui/dist apps/webui/dist

ENV NODE_ENV=production
EXPOSE 4173

WORKDIR /app/apps/webui
# 单进程统一运行时：/api 走 auth/转发，其余路径静态 + SSR（同一 Node 进程）
CMD ["node", "dist/server/index.js"]
