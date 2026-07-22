"""NoneBot-resolved Lingchu deployment configuration and platform helpers."""

from __future__ import annotations

from pathlib import Path
import platform
from typing import Any, Final, Literal

from _lingchu_bot_contracts import DeploymentSettings
from nonebot import get_driver, get_plugin_config, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import (
    get_plugin_cache_dir,
    get_plugin_config_dir,
    get_plugin_data_dir,
)
from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    field_validator,
)

from ..i18n import _
from .handle_config_defaults import HANDLE_DEFAULTS_REGISTRY
from .handle_config_manager import HandleConfigManager

# 不写入TOML默认文件的基础设施字段（由localstore/env管理，非运行时配置）
_NON_TOML_FIELDS: Final = frozenset({
    "core_version",
    "data_dir",
    "config_dir",
    "cache_dir",
    "announcement_image_cache_dir",
    "announcement_image_protocol_dir",
    "in_containers",
})


class ConfigError(TypeError):
    """配置错误异常基类。

    用于表示插件配置过程中发生的各类错误。

    """


class InvalidInContainersError(ConfigError):
    """in_containers配置格式错误。

    当in_containers配置值为字符串而不是布尔值时抛出此异常。
    NoneBot2只接受JSON标准的小写true/false，不支持大写True/False或其他格式。

    Args:
        value: 收到的配置值。

    """

    def __init__(self, value: Any) -> None:
        """初始化异常，生成详细的错误提示信息。

        Args:
            value: 收到的配置值。

        """
        self.value = value
        super().__init__(
            _(
                "in_containers 配置错误：\n"
                "收到字符串值: {value!r}\n"
                "NoneBot2 的 .env 配置文件只接受小写的 true 或 false 作为 bool 值\n"
                "请将配置改为: LINGCHU_IN_CONTAINERS=true 或"
                " LINGCHU_IN_CONTAINERS=false\n"
                "不要使用大写的 True/False 或其他格式。"
            ).format(value=value)
        )


class UnexpectedInContainersTypeError(ConfigError):
    """in_containers类型错误。

    当in_containers配置值的类型既不是bool也不是str时抛出此异常。

    Args:
        value: 收到的配置值。
        value_type: 收到的值的类型。

    """

    def __init__(self, value: Any, value_type: type) -> None:
        """初始化异常，生成详细的错误提示信息。

        Args:
            value: 收到的配置值。
            value_type: 收到的值的类型。

        """
        self.value = value
        self.value_type = value_type
        super().__init__(
            _(
                "in_containers 配置错误：\n"
                "期望布尔值，但收到 {value_type}: {value!r}\n"
                "请检查 NoneBot2 配置文件。"
            ).format(value_type=value_type.__name__, value=value)
        )


class Config(DeploymentSettings):
    """lingchu-bot核心配置类。

    管理插件版本、认证密钥、localstore 路径、部署配置及系统平台信息。
    部署字段仅通过 NoneBot ``get_plugin_config`` 解析；在线可编辑设置由
    ``core.mutable_settings`` 独立管理。

    Attributes:
        core_version: 核心插件版本号。
        data_dir: 数据存储目录路径。
        config_dir: 配置文件存储目录路径。
        cache_dir: 缓存文件存储目录路径。
        superuser_key: 运行时超级用户密钥。
        message_store_enabled: 是否启用消息存储。
        lingchu_superusers: 结构化超级用户平台账号绑定。
        lingchu_adapter: 适配器选择配置。

    """

    # --- 基础设施字段（来自原Config，不写入TOML） ---
    core_version: str = "0.0.0.dev40"
    data_dir: Path = Field(default_factory=get_plugin_data_dir)
    config_dir: Path = Field(default_factory=get_plugin_config_dir)
    cache_dir: Path = Field(default_factory=get_plugin_cache_dir)
    announcement_image_cache_dir: Path = Field(
        default_factory=lambda: get_plugin_cache_dir() / "announcement_images",
        validation_alias=AliasChoices("LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR"),
    )
    announcement_image_protocol_dir: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LINGCHU_ANNOUNCEMENT_IMAGE_PROTOCOL_DIR"),
    )
    in_containers: bool = Field(
        default=False,
        validation_alias=AliasChoices("LINGCHU_IN_CONTAINERS"),
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    # --- Validators ---

    @field_validator("in_containers", mode="before")
    @classmethod
    def _validate_in_containers(cls, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            raise InvalidInContainersError(value)
        raise UnexpectedInContainersTypeError(value, type(value))

    # --- 平台检测 Properties ---

    @property
    def system_type(self) -> Literal["Windows", "Linux", "Darwin", "Other"]:
        """获取当前系统类型。

        Returns:
            Literal["Windows", "Linux", "Darwin", "Other"]: 系统类型标识。
                Windows、Linux、Darwin分别表示对应的操作系统，
                Other表示其他未知系统。

        """
        system: str = platform.system()
        if system in ("Windows", "Linux", "Darwin"):
            return system
        return "Other"

    @property
    def is_windows(self) -> bool:
        """检查是否为Windows系统。

        Returns:
            bool: 若当前系统为Windows则返回True，否则返回False。

        """
        return self.system_type == "Windows"

    @property
    def is_linux(self) -> bool:
        """检查是否为Linux系统。

        Returns:
            bool: 若当前系统为Linux则返回True，否则返回False。

        """
        return self.system_type == "Linux"

    @property
    def is_macos(self) -> bool:
        """检查是否为macOS系统。

        Returns:
            bool: 若当前系统为macOS(Darwin)则返回True，否则返回False。

        """
        return self.system_type == "Darwin"

    def get_platform_info(self) -> dict[str, Any]:
        """获取详细的系统平台信息。

        Returns:
            dict[str, Any]: 包含系统类型、版本、处理器、Python版本和容器状态的字典。
                键包括：
                - system: 系统类型
                - release: 系统发行版本
                - version: 系统详细版本
                - machine: 机器架构
                - processor: 处理器型号
                - python_version: Python解释器版本
                - in_containers: 是否运行在容器环境

        """
        return {
            "system": self.system_type,
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "in_containers": self.in_containers,
        }


def get_runtime_config() -> Config:
    """Return deployment settings resolved by NoneBot configuration."""
    return get_plugin_config(Config)


# 配置加载（合并后的singleton，使用TOML-aware加载器）
plugin_config: Config = get_runtime_config()
global_config = get_driver().config

# 全局名称
NICKNAME: str = next(iter(global_config.nickname), "")


# --- HandleConfigManager 单例 ---
# 放在文件末尾以避免模块导入时触发初始化

_handle_config_manager: HandleConfigManager | None = None


def get_handle_config_manager() -> HandleConfigManager:
    """Get the global handle configuration manager singleton.

    Uses lazy initialization: creates the HandleConfigManager instance on
    first call and caches it for subsequent calls.

    Returns:
        HandleConfigManager: The global singleton instance for managing
            handle-level configurations.

    Note:
        This function is safe to call multiple times; it always returns
        the same instance after the first initialization.

    Example:
        >>> manager = get_handle_config_manager()
        >>> config = await manager.get_config("kick_member")
    """
    global _handle_config_manager
    if _handle_config_manager is None:
        _handle_config_manager = HandleConfigManager()
    return _handle_config_manager


async def initialize_handle_config_manager() -> None:
    """Initialize the handle configuration manager during startup.

    This function ensures all handle configuration files exist and preloads
    them into the memory cache. It should be called during the bot startup
    phase to prepare the configuration system.

    The initialization process:
    1. Ensures configuration files exist for all registered handles
    2. Loads all configurations into memory cache

    Raises:
        No exceptions are raised; errors are logged and non-fatal.

    Note:
        This function is non-blocking and safe to call from async context.
        If files cannot be created or loaded, the manager falls back to
        defaults from HANDLE_DEFAULTS_REGISTRY.

    Example:
        >>> async def startup():
        >>>     await initialize_handle_config_manager()
        >>>     # All handle configs are now ready
    """
    manager = get_handle_config_manager()
    await manager.ensure_config_files()
    # Preload all configs into cache
    await manager.get_all_configs()


__all__ = [
    "HANDLE_DEFAULTS_REGISTRY",
    "NICKNAME",
    "Config",
    "ConfigError",
    "InvalidInContainersError",
    "UnexpectedInContainersTypeError",
    "get_handle_config_manager",
    "get_runtime_config",
    "global_config",
    "initialize_handle_config_manager",
    "plugin_config",
]
