from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    CapabilityScope,
    ConnectedBotSummary,
    ContractError,
    ConversationAddress,
    ErrorCode,
    ImageSegment,
    ListRecentMessagesRequest,
    ListRecentMessagesResult,
    MessageAction,
    MessageCursor,
    MessageEnvelope,
    MessageProvider,
    MessageQuery,
    OperationStatus,
    ResourceGrant,
    SendMessageRequest,
    SendMessageResult,
    ServicePrincipal,
    TextSegment,
)


def test_bot_address_rejects_blank_identifiers_with_stable_error_code() -> None:
    with pytest.raises(ContractError) as caught:
        BotAddress(
            platform_id="qq",
            adapter_id="onebot11",
            protocol_id="onebot11",
            bot_id=" ",
        )

    assert caught.value.code is ErrorCode.INVALID_IDENTIFIER


def test_send_request_is_immutable_and_preserves_segment_order() -> None:
    request = SendMessageRequest(
        bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
        conversation=ConversationAddress("group", "20002"),
        segments=(
            TextSegment("first"),
            ImageSegment("https://cdn.example/image.png"),
            TextSegment("last"),
        ),
        idempotency_key="request-1",
    )

    assert tuple(type(segment) for segment in request.segments) == (
        TextSegment,
        ImageSegment,
        TextSegment,
    )
    attribute = "idempotency_key"
    with pytest.raises(FrozenInstanceError):
        setattr(request, attribute, "changed")


@pytest.mark.parametrize(
    ("factory", "error_code"),
    [
        (lambda: TextSegment(""), ErrorCode.INVALID_MESSAGE_SEGMENT),
        (
            lambda: SendMessageRequest(
                bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
                conversation=ConversationAddress("group", "20002"),
                segments=(),
                idempotency_key="request-1",
            ),
            ErrorCode.EMPTY_MESSAGE,
        ),
    ],
)
def test_send_contract_rejects_invalid_messages(
    factory: Callable[[], object],
    error_code: ErrorCode,
) -> None:
    with pytest.raises(ContractError) as caught:
        factory()

    assert caught.value.code is error_code


def test_message_envelope_contains_only_normalized_immutable_data() -> None:
    envelope = MessageEnvelope(
        record_id="record-1",
        message_id="platform-message-1",
        received_at=datetime(2026, 7, 18, tzinfo=UTC),
        bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
        conversation=ConversationAddress("group", "20002"),
        sender_id="30003",
        segments=(TextSegment("hello"), ImageSegment("https://cdn.example/i.png")),
        processing_status="stored",
    )

    assert envelope.sender_id == "30003"
    assert not hasattr(envelope, "raw_event")
    assert not hasattr(envelope, "raw_message")
    attribute = "sender_id"
    with pytest.raises(FrozenInstanceError):
        setattr(envelope, attribute, "changed")


def test_list_recent_request_enforces_page_limit() -> None:
    with pytest.raises(ContractError) as caught:
        ListRecentMessagesRequest(
            bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
            conversation=ConversationAddress("group", "20002"),
            limit=201,
        )

    assert caught.value.code is ErrorCode.INVALID_LIMIT


def test_identity_grant_and_results_use_stable_domain_values() -> None:
    principal = ServicePrincipal(
        "principal-1",
        "orders-service",
        enabled=True,
    )
    grant = ResourceGrant(
        grant_id="grant-1",
        principal_id=principal.principal_id,
        bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
        conversation=ConversationAddress("group", "20002"),
        revision=3,
    )
    cursor = MessageCursor("opaque-token")
    send_result = SendMessageResult(
        operation_id="operation-1",
        status=OperationStatus.SUCCEEDED,
        platform_message_id="message-1",
    )
    list_result = ListRecentMessagesResult(messages=(), next_cursor=cursor)
    bot = ConnectedBotSummary(grant.bot, "Lingchu", connected=True)

    assert CapabilityScope.MESSAGES_SEND == "messages:send"
    assert grant.revision == 3
    assert send_result.status == "succeeded"
    assert list_result.next_cursor is cursor
    assert bot.connected is True


def test_service_protocols_only_reference_domain_contracts() -> None:
    for protocol, method_name in (
        (MessageQuery, "list_recent"),
        (MessageAction, "send_message"),
        (MessageProvider, "send_message"),
    ):
        annotations = get_type_hints(getattr(protocol, method_name))
        rendered = " ".join(str(annotation) for annotation in annotations.values())
        assert "mcp." not in rendered
        assert "nonebot.adapters.onebot" not in rendered.lower()


def test_segment_collections_are_snapshotted_at_construction() -> None:
    source = [TextSegment("original")]
    typed_source = cast("tuple[TextSegment | ImageSegment, ...]", source)
    bot = BotAddress("qq", "onebot11", "onebot11", "10001")
    conversation = ConversationAddress("group", "20002")
    request = SendMessageRequest(
        bot=bot,
        conversation=conversation,
        segments=typed_source,
        idempotency_key="request-1",
    )
    envelope = MessageEnvelope(
        record_id="record-1",
        message_id="message-1",
        received_at=datetime(2026, 7, 18, tzinfo=UTC),
        bot=bot,
        conversation=conversation,
        sender_id="30003",
        segments=typed_source,
        processing_status="stored",
    )

    source.append(TextSegment("mutated"))

    assert request.segments == (TextSegment("original"),)
    assert envelope.segments == (TextSegment("original"),)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SendMessageRequest(
            bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
            conversation=ConversationAddress("group", "20002"),
            segments=cast("tuple[TextSegment | ImageSegment, ...]", (object(),)),
            idempotency_key="request-1",
        ),
        lambda: MessageEnvelope(
            record_id="record-1",
            message_id="message-1",
            received_at=datetime(2026, 7, 18, tzinfo=UTC),
            bot=BotAddress("qq", "onebot11", "onebot11", "10001"),
            conversation=ConversationAddress("group", "20002"),
            sender_id="30003",
            segments=cast("tuple[TextSegment | ImageSegment, ...]", (object(),)),
            processing_status="stored",
        ),
    ],
)
def test_segment_collections_reject_arbitrary_objects(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ContractError) as caught:
        factory()

    assert caught.value.code is ErrorCode.INVALID_MESSAGE_SEGMENT
