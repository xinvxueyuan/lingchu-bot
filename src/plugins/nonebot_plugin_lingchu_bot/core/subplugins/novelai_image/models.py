"""Pure value objects shared by the NovelAI generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import re

_MIN_COORD = 0.1
_MAX_COORD = 0.9
_MAX_SEED = 2**32 - 1
_NEGATIVE_SEPARATOR = re.compile(r"[,\n]+")


def _as_tuple[T](values: tuple[T, ...]) -> tuple[T, ...]:
    return tuple(values)


def normalize_tags(values: tuple[str, ...]) -> tuple[str, ...]:
    """Trim tags and remove case-insensitive duplicates while preserving order."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return tuple(result)


def normalize_negative_prompt(value: str | None) -> tuple[str, ...]:
    """Split comma/newline negative prompt text into normalized tags."""
    if not value:
        return ()
    return normalize_tags(tuple(_NEGATIVE_SEPARATOR.split(value)))


def _validate_seed(seed: int | None) -> None:
    if seed is not None and not 0 <= seed <= _MAX_SEED:
        raise ValueError("seed must be an unsigned 32-bit integer")


@dataclass(frozen=True, slots=True)
class PositionCoord:
    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", max(_MIN_COORD, min(_MAX_COORD, self.x)))
        object.__setattr__(self, "y", max(_MIN_COORD, min(_MAX_COORD, self.y)))


@dataclass(frozen=True, slots=True)
class CharacterIntent:
    description: str
    tags: tuple[str, ...]
    negative_tags: tuple[str, ...]
    center: PositionCoord

    def __post_init__(self) -> None:
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "tags", normalize_tags(tuple(self.tags)))
        object.__setattr__(
            self,
            "negative_tags",
            normalize_tags(tuple(self.negative_tags)),
        )


@dataclass(frozen=True, slots=True)
class GenerationHints:
    width: int | None = None
    height: int | None = None
    steps: int | None = None
    scale: float | None = None
    sampler: str | None = None
    seed: int | None = None
    negative_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "negative_tags",
            normalize_tags(tuple(self.negative_tags)),
        )


@dataclass(frozen=True, slots=True)
class PromptIntent:
    source_language: str
    english_description: str
    base_tags: tuple[str, ...]
    generation: GenerationHints
    characters: tuple[CharacterIntent, ...]
    search_required: bool
    search_query: str | None
    search_reason: str | None

    def __post_init__(self) -> None:
        description = self.english_description.strip()
        if not description:
            raise ValueError("english_description must not be empty")
        object.__setattr__(self, "source_language", self.source_language.strip())
        object.__setattr__(self, "english_description", description)
        object.__setattr__(self, "base_tags", normalize_tags(tuple(self.base_tags)))
        object.__setattr__(self, "characters", tuple(self.characters))


@dataclass(frozen=True, slots=True)
class VisualResearch:
    facts: tuple[str, ...]
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "facts", normalize_tags(tuple(self.facts)))
        object.__setattr__(self, "sources", normalize_tags(tuple(self.sources)))


@dataclass(frozen=True, slots=True)
class TipoRequest:
    description: str
    tags: tuple[str, ...]
    visual_facts: tuple[str, ...]
    seed: int

    def __post_init__(self) -> None:
        _validate_seed(self.seed)
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "tags", normalize_tags(tuple(self.tags)))
        object.__setattr__(
            self,
            "visual_facts",
            normalize_tags(tuple(self.visual_facts)),
        )


@dataclass(frozen=True, slots=True)
class TipoPrompt:
    natural_language: str
    tags: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "natural_language", self.natural_language.strip())
        object.__setattr__(self, "tags", normalize_tags(tuple(self.tags)))


@dataclass(frozen=True, slots=True)
class GenerationOverrides:
    width: int | None = None
    height: int | None = None
    steps: int | None = None
    scale: float | None = None
    sampler: str | None = None
    seed: int | None = None
    negative_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class NovelAIGenerationPlan:
    prompt: str
    negative_prompt: str
    width: int
    height: int
    steps: int
    scale: float
    sampler: str
    seed: int
    base_caption: str
    char_captions: tuple[dict[str, object], ...]
    character_prompts: tuple[dict[str, object], ...]
    use_coords: bool

    def __post_init__(self) -> None:
        _validate_seed(self.seed)
        object.__setattr__(self, "char_captions", _as_tuple(self.char_captions))
        object.__setattr__(
            self,
            "character_prompts",
            _as_tuple(self.character_prompts),
        )
