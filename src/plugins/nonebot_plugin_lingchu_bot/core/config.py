"""核心配置模块。

此模块定义了NoneBot插件的配置结构和系统检测功能。
主要包含：
- ConfigError: 配置错误的基类异常
- InvalidInContainersError: in_containers配置格式错误异常
- UnexpectedInContainersTypeError: in_containers类型错误异常
- Config: 主配置类，包含插件版本、密钥、路径及平台检测方法

"""

import platform
from pathlib import Path
from typing import Any, Literal, cast

from nonebot import get_driver, get_plugin_config, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import (
    get_plugin_cache_dir,
    get_plugin_config_dir,
    get_plugin_data_dir,
)
from pydantic import AliasChoices, BaseModel, Field, field_validator

from ..i18n import _


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


class Config(BaseModel):
    """lingchu-bot核心配置类。

    管理插件的版本、认证密钥、数据存储路径及系统平台信息。

    Attributes:
        core_version: 核心插件版本号。
        data_dir: 数据存储目录路径。
        config_dir: 配置文件存储目录路径。
        cache_dir: 缓存文件存储目录路径。

    """

    core_version: str = "0.0.0.dev40"
    data_dir: Path = Field(default_factory=get_plugin_data_dir)
    config_dir: Path = Field(default_factory=get_plugin_config_dir)
    cache_dir: Path = Field(default_factory=get_plugin_cache_dir)
    announcement_image_cache_dir: Path = Field(
        default_factory=lambda: get_plugin_cache_dir() / "announcement_images",
        validation_alias=AliasChoices(
            "LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR",
            "ANNOUNCEMENT_IMAGE_CACHE_DIR",
        ),
    )
    announcement_image_protocol_dir: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LINGCHU_ANNOUNCEMENT_IMAGE_PROTOCOL_DIR",
            "ANNOUNCEMENT_IMAGE_PROTOCOL_DIR",
        ),
    )
    in_containers: bool = Field(
        default=False,
        validation_alias=AliasChoices("LINGCHU_IN_CONTAINERS", "IN_CONTAINERS"),
    )

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

    @property
    def superuser_key(self) -> str:
        """Return the runtime superuser key from lightweight config."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().superuser_key

    @property
    def message_store_enabled(self) -> bool:
        """Return whether message storage hooks are enabled."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().message_store_enabled

    @property
    def message_store_retention_days(self) -> int:
        """Return message record retention days."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().message_store_retention_days

    @property
    def message_store_summary_limit(self) -> int:
        """Return message summary truncation limit."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().message_store_summary_limit

    @property
    def message_store_record_api_calls(self) -> bool:
        """Return whether platform API call summaries are recorded."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().message_store_record_api_calls

    @property
    def message_store_cleanup_enabled(self) -> bool:
        """Return whether expired message cleanup is enabled."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().message_store_cleanup_enabled

    @property
    def lingchu_superusers(self) -> dict[str, dict[str, str | int]] | None:
        """Return structured Lingchu SUPERUSERS platform account bindings."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().lingchu_superusers

    @property
    def lingchu_adapter(self) -> str | list[str] | None:
        """Return configured adapter selection from lightweight config."""
        from .runtime_config import get_runtime_config

        return get_runtime_config().lingchu_adapter

    @property
    def system_type(self) -> Literal["Windows", "Linux", "Darwin", "Other"]:
        """获取当前系统类型。

        Returns:
            Literal["Windows", "Linux", "Darwin", "Other"]: 系统类型标识。
                Windows、Linux、Darwin分别表示对应的操作系统，
                Other表示其他未知系统。

        """
        system: str = platform.system()
        if system in ["Windows", "Linux", "Darwin"]:
            return cast(typ="Literal['Windows', 'Linux', 'Darwin']", val=system)
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

    model_config = {"arbitrary_types_allowed": True}


# 配置加载
plugin_config: Config = get_plugin_config(Config)
global_config = get_driver().config

# 全局名称
NICKNAME: str = next(iter(global_config.nickname), "")
