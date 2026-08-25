"""Shared constants for Lingc CLI."""

from __future__ import annotations

import sys

PROG = "lc"
WINDOWS = sys.platform.startswith("win")
REQUIRES_PYTHON = (3, 13)
DEFAULT_STARTUP_TIMEOUT = 30
STARTUP_MARKER = "Application startup complete."

# lc-host 运行时标识: 注入被监督子进程(worker)环境, 使其可识别宿主会话。
LC_HOST_RUNTIME_ID_ENV = "LC_HOST_RUNTIME_ID"
LC_HOST_PID_ENV = "LC_HOST_PID"
# 重启请求哨兵文件路径: worker 创建该文件即请求宿主重启自身应用。
LC_HOST_RESTART_REQUEST_ENV = "LC_HOST_RESTART_REQUEST"
