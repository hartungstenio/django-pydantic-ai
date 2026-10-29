from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.db import IntegrityError
from pydantic_ai.conversation import Conversation as PydanticConversation
from pydantic_ai.conversation import ConversationTypeAdapter
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.tools import DeferredToolRequests
from pydantic_ai.usage import RunUsage

import django_pydantic_ai.conversations.models as conversation_models
from django_pydantic_ai.conversations.models import Conversation


class TestConversationManager:
    @pytest.mark.django_db
    def test_get_conversation_reconstructs_pydantic_conversation(self) -> None:
        conversation = PydanticConversation(
            messages=[
                ModelRequest(parts=[UserPromptPart(content="hello")]),
                ModelResponse(parts=[TextPart(content="hi")]),
            ],
            usage=RunUsage(
                input_tokens=12,
                output_tokens=3,
                requests=1,
                details={"custom": 2},
                cost=Decimal("0.12"),
            ),
            conversation_id="round-trip",
            deferred_tool_requests=DeferredToolRequests(
                calls=[ToolCallPart(tool_name="lookup", args={"query": "hello"}, tool_call_id="call-1")]
            ),
        )
        conversation_data = ConversationTypeAdapter.dump_python(conversation, mode="json")
        usage = conversation_data.pop("usage")
        stored = Conversation.objects.create(**conversation_data, **usage)

        restored = Conversation.objects.get_conversation(conversation.conversation_id)

        assert restored == conversation
        assert isinstance(restored, PydanticConversation)
        assert stored.input_tokens == conversation.usage.input_tokens
        assert stored.output_tokens == conversation.usage.output_tokens
        assert stored.details == {"custom": 2}

    @pytest.mark.django_db
    def test_usage_fields_can_be_filtered_in_database(self) -> None:
        Conversation.objects.create(conversation_id="small", input_tokens=99)
        Conversation.objects.create(conversation_id="large", input_tokens=1000)

        assert list(Conversation.objects.filter(input_tokens__gte=1000).values_list("conversation_id", flat=True)) == [
            "large"
        ]

    @pytest.mark.django_db
    def test_get_conversation_raises_for_unknown_id(self) -> None:
        with pytest.raises(Conversation.DoesNotExist):
            Conversation.objects.get_conversation("unknown")

    @pytest.mark.django_db
    def test_get_conversation_ignores_usage_fields_not_on_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        Conversation.objects.create(conversation_id="future-usage-field")
        original_fields = conversation_models.fields

        def fields_with_future_usage_field(dataclass_type: type[RunUsage]) -> tuple[object, ...]:
            return (*original_fields(dataclass_type), SimpleNamespace(name="future_usage_field"))

        monkeypatch.setattr(conversation_models, "fields", fields_with_future_usage_field)

        conversation = Conversation.objects.get_conversation("future-usage-field")

        assert conversation.usage == RunUsage()


class TestConversation:
    @pytest.mark.django_db
    def test_conversation_id_is_unique(self) -> None:
        Conversation.objects.create(conversation_id="duplicate")

        with pytest.raises(IntegrityError):
            Conversation.objects.create(conversation_id="duplicate")
