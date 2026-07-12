"""Small child-owned message catalog."""

from ..contracts import get_configured_locale

MESSAGES = {
    "disabled": {
        "zh": "NovelAI 生图已禁用",
        "en": "NovelAI image generation is disabled",
    },
    "empty": {
        "zh": "生图描述不能为空",
        "en": "The image description cannot be empty",
    },
    "prompt_failed": {
        "zh": "提示词转换暂时不可用，请稍后再试",
        "en": "Prompt conversion is temporarily unavailable",
    },
    "parameter_invalid": {
        "zh": "生图参数无效，请检查后重试",
        "en": "Invalid image parameters",
    },
    "token_missing": {
        "zh": "未配置 NovelAI Token",
        "en": "NovelAI token is not configured",
    },
    "generation_failed": {
        "zh": "NovelAI 生图暂时不可用，请稍后再试",
        "en": "NovelAI image generation is temporarily unavailable",
    },
}


def translate(key: str) -> str:
    language = "en" if get_configured_locale().lower().startswith("en") else "zh"
    return MESSAGES[key][language]
