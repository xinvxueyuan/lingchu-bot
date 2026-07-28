"""User-facing input-validation enums for the NovelAI image subplugin.

These enums are kept solely for handler-level input validation (e.g. parsing
Director tool names, emotion presets, and ControlNet model selections). All
NovelAI API DTOs, endpoints, model identifiers, samplers, quality tags, and UC
presets are now owned by the NovelAI-Image-MCP server.
"""

from enum import IntEnum, StrEnum


class ControlNetModel(StrEnum):
    PALETTE_SWAP = "hed"
    FORM_LOCK = "midas"
    SCRIBBLER = "fake_scribble"
    BUILDING_CONTROL = "mlsd"
    LANDSCAPER = "uniformer"


class DirectorTool(StrEnum):
    LINE_ART = "lineart"
    SKETCH = "sketch"
    BACKGROUND_REMOVAL = "bg-removal"
    DECLUTTER = "declutter"
    COLORIZE = "colorize"
    EMOTION = "emotion"


class Emotion(StrEnum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SCARED = "scared"
    SURPRISED = "surprised"
    TIRED = "tired"
    EXCITED = "excited"
    NERVOUS = "nervous"
    THINKING = "thinking"
    CONFUSED = "confused"
    SHY = "shy"
    DISGUSTED = "disgusted"
    SMUG = "smug"
    BORED = "bored"
    LAUGHING = "laughing"
    IRRITATED = "irritated"
    AROUSED = "aroused"
    EMBARRASSED = "embarrassed"
    WORRIED = "worried"
    LOVE = "love"
    DETERMINED = "determined"
    HURT = "hurt"
    PLAYFUL = "playful"


class EmotionLevel(IntEnum):
    NORMAL = 0
    SLIGHTLY_WEAK = 1
    WEAK = 2
    EVEN_WEAKER = 3
    VERY_WEAK = 4
    WEAKEST = 5
