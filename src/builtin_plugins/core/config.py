import platform
from pathlib import Path
from typing import Any, Literal, cast

import nonebot
from nonebot_plugin_localstore import (
    get_plugin_cache_dir,
    get_plugin_config_dir,
    get_plugin_data_dir,
)
from pydantic import BaseModel, Field


class ConfigError(TypeError):
    """配置错误异常"""


class InvalidInContainersError(ConfigError):
    """in_containers 配置格式错误"""

    def __init__(self, value: Any) -> None:
        self.value = value
        super().__init__(
            f"in_containers 配置错误：\n"
            f"收到字符串值: {value!r}\n"
            f"NoneBot2 的 .env 配置文件只接受小写的 true 或 false 作为 bool 值\n"
            f"请将配置改为: IN_CONTAINERS=true 或 IN_CONTAINERS=false\n"
            f"不要使用大写的 True/False 或其他格式。"
        )


class UnexpectedInContainersTypeError(ConfigError):
    """in_containers 类型错误"""

    def __init__(self, value: Any, value_type: type) -> None:
        self.value = value
        self.value_type = value_type
        super().__init__(
            f"in_containers 配置错误：\n"
            f"期望布尔值，但收到 {value_type.__name__}: {value!r}\n"
            f"请检查 NoneBot2 配置文件。"
        )


class Config(BaseModel):
    core_version: str = "0.0.0-dev0"
    superuser_key: str = "123456789abcdef"
    data_dir: Path = Field(default_factory=get_plugin_data_dir)
    config_dir: Path = Field(default_factory=get_plugin_config_dir)
    cache_dir: Path = Field(default_factory=get_plugin_cache_dir)

    @property
    def in_containers(self) -> bool:
        """
        获取 in_containers 配置，严格要求为布尔值。
        NoneBot2 只接受 JSON 标准的小写 true/false 并自动解析为 bool，
        任何其他格式（如大写 True/False、字符串 "true" 等）都会被视为 str 传入，
        此时将抛出错误而非尝试转换。
        如果配置缺失（None），默认返回 False。
        """
        raw_value = nonebot.get_driver().config.in_containers
        if raw_value is None:
            return False
        if isinstance(raw_value, bool):
            return raw_value

        if isinstance(raw_value, str):
            raise InvalidInContainersError(raw_value)

        raise UnexpectedInContainersTypeError(raw_value, type(raw_value))

    @property
    def system_type(self) -> Literal["Windows", "Linux", "Darwin", "Other"]:
        system: str = platform.system()
        if system in ["Windows", "Linux", "Darwin"]:
            return cast(typ="Literal['Windows', 'Linux', 'Darwin']", val=system)
        return "Other"

    @property
    def is_windows(self) -> bool:
        """是否为 Windows 系统"""
        return self.system_type == "Windows"

    @property
    def is_linux(self) -> bool:
        """是否为 Linux 系统"""
        return self.system_type == "Linux"

    @property
    def is_macos(self) -> bool:
        """是否为 macOS 系统"""
        return self.system_type == "Darwin"

    def get_platform_info(self) -> dict:
        """获取详细的系统平台信息"""
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
