"""Complete NovelAI HTTP client built on NoneBot's shared HTTP session."""

from __future__ import annotations

import base64
from collections import OrderedDict
from collections.abc import AsyncIterator, Mapping
from dataclasses import replace
from hashlib import sha256
import json
from typing import TYPE_CHECKING, Any

from nonebot import get_driver
from nonebot.drivers import Request

from .auth import NovelAICredentials, derive_access_key, request_tracking_headers
from .constants import (
    ControlNetModel,
    DirectorTool,
    Emotion,
    EmotionLevel,
    Endpoint,
    Model,
    is_v4_model,
)
from .exceptions import (
    NovelAIAuthenticationError,
    NovelAIError,
    NovelAIProviderError,
    NovelAIResponseError,
    NovelAITimeoutError,
    NovelAITransportError,
)
from .imaging import parse_image
from .models import CharacterPrompt, GenerationRequest
from .payload import build_generation_payload
from .response import (
    GenerationEvent,
    MessagePackStreamParser,
    NovelAIImage,
    check_status,
    parse_messagepack_images,
    parse_zip_images,
)

if TYPE_CHECKING:
    from .config import NovelAIConfig
    from .models import NovelAIGenerationPlan

_SHARED_VIBE_CACHE: OrderedDict[str, str] = OrderedDict()


class MissingNovelAITokenError(NovelAIAuthenticationError):
    """No usable NovelAI credential is configured."""


def _content(response: object) -> bytes:
    content = getattr(response, "content", b"")
    if isinstance(content, str):
        return content.encode()
    if isinstance(content, bytes):
        return content
    raise NovelAIResponseError("NovelAI response has no binary content")


def _json_object(content: bytes) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise NovelAIResponseError("NovelAI returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise NovelAIResponseError("NovelAI returned a non-object JSON response")
    return value


def _first_image(content: bytes, *, filename: str) -> NovelAIImage:
    if content.startswith(b"PK"):
        images = parse_zip_images(content)
        if not images:
            raise NovelAIResponseError("NovelAI returned an empty image archive")
        return replace(images[0], filename=filename)
    return NovelAIImage(filename=filename, data=content)


class NovelAIClient:
    """Project-owned client for generation, tools, utilities, and account APIs."""

    def __init__(
        self,
        credentials: NovelAICredentials,
        *,
        image_base_url: str = "https://image.novelai.net",
        account_base_url: str = "https://api.novelai.net",
        timeout: float = 120.0,
        vibe_cache_entries: int = 64,
    ) -> None:
        self.credentials = credentials
        self.image_base_url = image_base_url.rstrip("/")
        self.account_base_url = account_base_url.rstrip("/")
        self.timeout = timeout
        self.vibe_cache_entries = vibe_cache_entries
        self._access_token: str | None = credentials.token
        self._vibe_cache = _SHARED_VIBE_CACHE

    async def _request(
        self,
        method: str,
        url: str,
        *,
        authenticated: bool = True,
        json_body: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> bytes:
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://novelai.net",
            "Referer": "https://novelai.net",
        } | request_tracking_headers()
        if authenticated:
            headers["Authorization"] = f"Bearer {await self.get_access_token()}"
        request = Request(
            method,
            url,
            headers=headers,
            json=dict(json_body) if json_body is not None else None,
            params=dict(params) if params is not None else None,
            timeout=self.timeout,
        )
        get_session = getattr(get_driver(), "get_session", None)
        if get_session is None:
            raise NovelAITransportError("NoneBot HTTP client is unavailable")
        try:
            async with get_session() as session:
                response = await session.request(request)
        except NovelAIError:
            raise
        except TimeoutError as exc:
            raise NovelAITimeoutError("NovelAI request timed out") from exc
        except Exception as exc:
            raise NovelAITransportError("NovelAI request transport failed") from exc
        content = _content(response)
        check_status(response.status_code, content)
        return content

    async def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        payload = {"key": derive_access_key(self.credentials)}
        content = await self._request(
            "POST",
            f"{self.account_base_url}{Endpoint.LOGIN}",
            authenticated=False,
            json_body=payload,
        )
        token = _json_object(content).get("accessToken")
        if not isinstance(token, str) or not token:
            raise NovelAIResponseError("NovelAI login did not return an access token")
        self._access_token = token
        return token

    async def encode_vibe(
        self,
        reference: str,
        *,
        information_extracted: float,
        model: Model,
    ) -> str:
        key = sha256(
            (
                f"{self.image_base_url}\0{reference}\0"
                f"{information_extracted}\0{model.value}"
            ).encode()
        ).hexdigest()
        cached = self._vibe_cache.get(key)
        if cached is not None:
            self._vibe_cache.move_to_end(key)
            return cached
        content = await self._request(
            "POST",
            f"{self.image_base_url}{Endpoint.ENCODE_VIBE}",
            json_body={
                "image": reference,
                "information_extracted": information_extracted,
                "model": model.value,
            },
        )
        token = base64.b64encode(content).decode("ascii")
        self._vibe_cache[key] = token
        while len(self._vibe_cache) > self.vibe_cache_entries:
            self._vibe_cache.popitem(last=False)
        return token

    async def _prepare_references(
        self, request: GenerationRequest
    ) -> GenerationRequest:
        if not is_v4_model(request.model) or not request.references:
            return request
        information = request.reference_information or tuple(
            1.0 for _ in request.references
        )
        encoded = tuple([
            await self.encode_vibe(
                reference,
                information_extracted=information[index],
                model=request.model,
            )
            for index, reference in enumerate(request.references)
        ])
        return replace(request, references=encoded, reference_information=())

    async def generate(
        self,
        request: GenerationRequest,
    ) -> tuple[NovelAIImage, ...]:
        prepared = await self._prepare_references(request)
        endpoint = (
            Endpoint.IMAGE_STREAM if is_v4_model(prepared.model) else Endpoint.IMAGE
        )
        content = await self._request(
            "POST",
            f"{self.image_base_url}{endpoint}",
            json_body=build_generation_payload(prepared),
        )
        if is_v4_model(prepared.model):
            return parse_messagepack_images(content)
        return parse_zip_images(content)

    async def stream_generation(
        self,
        request: GenerationRequest,
    ) -> AsyncIterator[GenerationEvent]:
        """Yield V4/V4.5 events as the active driver produces HTTP chunks."""
        prepared = await self._prepare_references(request)
        if not is_v4_model(prepared.model):
            raise ValueError("real-time generation requires a V4/V4.5 model")
        http_request = Request(
            "POST",
            f"{self.image_base_url}{Endpoint.IMAGE_STREAM}",
            headers={
                "Authorization": f"Bearer {await self.get_access_token()}",
                "Accept": "application/x-msgpack",
                "Content-Type": "application/json",
            }
            | request_tracking_headers(),
            json=build_generation_payload(prepared),
            timeout=self.timeout,
        )
        get_session = getattr(get_driver(), "get_session", None)
        if get_session is None:
            raise NovelAITransportError("NoneBot HTTP client is unavailable")
        parser = MessagePackStreamParser()
        try:
            async with get_session() as session:
                stream_request = getattr(session, "stream_request", None)
                if stream_request is None:
                    response = await session.request(http_request)
                    content = _content(response)
                    check_status(response.status_code, content)
                    for event in parser.feed(content):
                        yield event
                else:
                    async for response in stream_request(http_request):
                        content = _content(response)
                        check_status(response.status_code, content)
                        for event in parser.feed(content):
                            yield event
            parser.finish()
        except NovelAIError:
            raise
        except TimeoutError as exc:
            raise NovelAITimeoutError("NovelAI streaming request timed out") from exc
        except Exception as exc:
            raise NovelAITransportError("NovelAI streaming transport failed") from exc

    async def director(
        self,
        tool: DirectorTool,
        image: bytes,
        *,
        prompt: str = "",
        defry: int = 0,
        emotion: Emotion | None = None,
        emotion_level: EmotionLevel = EmotionLevel.NORMAL,
    ) -> NovelAIImage:
        parsed = parse_image(image)
        if tool is DirectorTool.EMOTION:
            if emotion is None:
                raise ValueError("emotion tool requires an emotion")
            prompt = f"{emotion.value};;{prompt + ',' if prompt else ''}"
            defry = int(emotion_level)
        content = await self._request(
            "POST",
            f"{self.image_base_url}{Endpoint.DIRECTOR}",
            json_body={
                "req_type": tool.value,
                "width": parsed.width,
                "height": parsed.height,
                "image": parsed.base64,
                "prompt": prompt,
                "defry": defry,
            },
        )
        return _first_image(content, filename=f"{tool.value}.png")

    async def upscale(self, image: bytes, *, factor: int = 4) -> NovelAIImage:
        if factor not in {2, 4}:
            raise ValueError("upscale factor must be 2 or 4")
        parsed = parse_image(image)
        content = await self._request(
            "POST",
            f"{self.account_base_url}{Endpoint.UPSCALE}",
            json_body={
                "image": parsed.base64,
                "width": parsed.width,
                "height": parsed.height,
                "scale": factor,
            },
        )
        return _first_image(content, filename="upscaled.png")

    async def annotate(
        self,
        image: bytes,
        model: ControlNetModel,
    ) -> NovelAIImage:
        parsed = parse_image(image)
        content = await self._request(
            "POST",
            f"{self.account_base_url}{Endpoint.ANNOTATE}",
            json_body={"model": model.value, "parameters": {"image": parsed.base64}},
        )
        return _first_image(content, filename=f"{model.value}.png")

    async def suggest_tags(
        self,
        prompt: str,
        *,
        model: Model = Model.V4_5,
        language: str = "en",
    ) -> tuple[dict[str, Any], ...]:
        content = await self._request(
            "GET",
            f"{self.image_base_url}{Endpoint.SUGGEST_TAGS}",
            params={"model": model.value, "prompt": prompt, "lang": language},
        )
        tags = _json_object(content).get("tags", [])
        if not isinstance(tags, list) or not all(
            isinstance(item, dict) for item in tags
        ):
            raise NovelAIResponseError("NovelAI returned invalid tag suggestions")
        return tuple(tags)

    async def get_subscription(self) -> dict[str, Any]:
        content = await self._request(
            "GET",
            f"{self.account_base_url}{Endpoint.SUBSCRIPTION}",
        )
        return _json_object(content)

    async def get_user_data(self) -> dict[str, Any]:
        content = await self._request(
            "GET",
            f"{self.account_base_url}{Endpoint.USER_DATA}",
        )
        return _json_object(content)


def _process_event(event: object) -> tuple[str, bytes | None, str | None]:
    """Compatibility helper retained for existing parser tests."""
    if not isinstance(event, dict):
        return (type(event).__name__, None, None)
    event_type = str(event.get("event_type"))
    if event_type == "final":
        image = event.get("image")
        if isinstance(image, bytes):
            return (event_type, image, None)
        if isinstance(image, str):
            try:
                return (event_type, base64.b64decode(image, validate=True), None)
            except ValueError:
                return (event_type, None, "Invalid final image value")
        return (event_type, None, "Invalid final image value")
    if event_type == "error":
        return (
            event_type,
            None,
            f"NovelAI error (code={event.get('code', 'unknown')}): "
            f"{event.get('message', 'unknown error')}",
        )
    return (event_type, None, None)


def extract_final_image(content: bytes) -> bytes:
    try:
        images = parse_messagepack_images(content)
    except NovelAIProviderError as exc:
        raise NovelAIResponseError(str(exc)) from exc
    if not images:
        raise NovelAIResponseError("No final image in stream")
    return images[-1].data


def _coordinate(value: object, *, default: float = 0.5) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


async def generate_image(
    plan: NovelAIGenerationPlan,
    *,
    config: NovelAIConfig,
) -> bytes:
    """Compatibility entry point for the existing intelligent prompt handler."""
    if not config.token and not (config.username and config.password):
        raise MissingNovelAITokenError("NovelAI credentials are not configured")
    characters: list[CharacterPrompt] = []
    for raw_character in plan.character_prompts:
        center = raw_character.get("center", {})
        center_values = center if isinstance(center, dict) else {}
        characters.append(
            CharacterPrompt(
                prompt=str(raw_character.get("prompt", "")),
                negative_prompt=str(raw_character.get("uc", "")),
                x=_coordinate(center_values.get("x")),
                y=_coordinate(center_values.get("y")),
                enabled=bool(raw_character.get("enabled", True)),
            )
        )
    request = GenerationRequest(
        prompt=plan.prompt,
        base_caption=plan.base_caption,
        negative_prompt=plan.negative_prompt,
        model=Model(config.model),
        width=plan.width,
        height=plan.height,
        steps=plan.steps,
        scale=plan.scale,
        sampler=plan.sampler,
        seed=plan.seed,
        n_samples=config.n_samples,
        quality=config.quality,
        uc_preset=config.uc_preset,
        noise_schedule=config.noise_schedule,
        cfg_rescale=config.cfg_rescale,
        dynamic_thresholding=config.dynamic_thresholding,
        auto_smea=config.auto_smea,
        prefer_brownian=config.prefer_brownian,
        character_prompts=tuple(characters),
        use_coords=plan.use_coords,
    )
    images = await NovelAIClient(
        NovelAICredentials(
            token=config.token,
            username=config.username,
            password=config.password,
        ),
        image_base_url=config.base_url,
        account_base_url=config.account_base_url,
        timeout=config.timeout,
        vibe_cache_entries=config.vibe_cache_entries,
    ).generate(request)
    if not images:
        raise NovelAIResponseError("NovelAI returned no final images")
    return images[-1].data


__all__ = [
    "MissingNovelAITokenError",
    "NovelAIClient",
    "NovelAIError",
    "NovelAIProviderError",
    "NovelAIResponseError",
    "NovelAITimeoutError",
    "NovelAITransportError",
    "extract_final_image",
    "generate_image",
]
