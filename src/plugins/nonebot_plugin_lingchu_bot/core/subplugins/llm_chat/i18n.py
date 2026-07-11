"""Child-owned message catalog for LLM chat."""

from ..contracts import get_configured_locale

MESSAGES = {
    "disabled": {
        "zh": "该功能已禁用",
        "en": "This feature is disabled",
    },
    "llm_error": {
        "zh": "LLM 服务暂时不可用，请稍后再试",
        "en": "LLM service is temporarily unavailable, please try again later",
    },
}


def translate(key: str) -> str:
    language = "en" if get_configured_locale().lower().startswith("en") else "zh"
    return MESSAGES[key][language]
