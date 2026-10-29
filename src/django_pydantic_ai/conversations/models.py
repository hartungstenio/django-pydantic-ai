"""Database models for Pydantic AI conversations."""

from __future__ import annotations

from dataclasses import fields
from typing import ClassVar, override

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta
from pydantic_ai.conversation import Conversation as PydanticConversation
from pydantic_ai.conversation import ConversationTypeAdapter
from pydantic_ai.usage import RunUsage


class ConversationManager(models.Manager["Conversation"]):
    """Retrieve Pydantic AI conversations from persistent storage."""

    def get_conversation(self, conversation_id: str) -> PydanticConversation:
        """Return the Pydantic AI conversation identified by its ID.

        Args:
            conversation_id: Identifier of the stored conversation.

        Returns:
            The reconstructed Pydantic AI conversation.

        Raises:
            Conversation.DoesNotExist: If no conversation has this ID.
            pydantic.ValidationError: If stored JSON cannot be parsed as a conversation.
        """
        instance = self.get_queryset().get(conversation_id=conversation_id)
        model_field_names = {field.name for field in instance._meta.concrete_fields}
        return ConversationTypeAdapter.validate_python(
            {
                "messages": instance.messages,
                "usage": RunUsage(
                    **{
                        field.name: getattr(instance, field.name)
                        for field in fields(RunUsage)
                        if field.name in model_field_names
                    }
                ),
                "conversation_id": instance.conversation_id,
                "deferred_tool_requests": instance.deferred_tool_requests,
            }
        )


class Conversation(models.Model):
    """Persisted Pydantic AI conversation state."""

    conversation_id = models.TextField(
        verbose_name=_("conversation ID"),
        help_text=_("Unique identifier shared by all runs in this conversation."),
        db_comment="Unique identifier shared by all runs in this conversation.",
    )
    messages = models.JSONField(
        default=list,
        verbose_name=_("messages"),
        help_text=_("JSON-serialized message history for this conversation."),
        db_comment="JSON-serialized message history for this conversation.",
    )
    input_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("input tokens"),
        help_text=_("Accumulated number of input tokens."),
        db_comment="Accumulated number of input tokens.",
    )
    cache_write_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("cache write tokens"),
        help_text=_("Accumulated number of cache-write tokens."),
        db_comment="Accumulated number of cache-write tokens.",
    )
    cache_write_1h_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("one-hour cache write tokens"),
        help_text=_("Accumulated number of one-hour cache-write tokens."),
        db_comment="Accumulated number of one-hour cache-write tokens.",
    )
    cache_read_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("cache read tokens"),
        help_text=_("Accumulated number of cache-read tokens."),
        db_comment="Accumulated number of cache-read tokens.",
    )
    output_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("output tokens"),
        help_text=_("Accumulated number of output tokens."),
        db_comment="Accumulated number of output tokens.",
    )
    unmeasured_requests = models.BigIntegerField(
        default=0,
        verbose_name=_("unmeasured requests"),
        help_text=_("Accumulated number of requests with unmeasured usage."),
        db_comment="Accumulated number of requests with unmeasured usage.",
    )
    output_reasoning_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("output reasoning tokens"),
        help_text=_("Accumulated number of output reasoning tokens."),
        db_comment="Accumulated number of output reasoning tokens.",
    )
    input_audio_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("input audio tokens"),
        help_text=_("Accumulated number of input audio tokens."),
        db_comment="Accumulated number of input audio tokens.",
    )
    cache_audio_read_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("cached audio read tokens"),
        help_text=_("Accumulated number of cached audio read tokens."),
        db_comment="Accumulated number of cached audio read tokens.",
    )
    output_audio_tokens = models.BigIntegerField(
        default=0,
        verbose_name=_("output audio tokens"),
        help_text=_("Accumulated number of output audio tokens."),
        db_comment="Accumulated number of output audio tokens.",
    )
    audio_seconds = models.FloatField(
        default=0.0,
        verbose_name=_("audio seconds"),
        help_text=_("Accumulated duration of audio processed in seconds."),
        db_comment="Accumulated duration of audio processed in seconds.",
    )
    details = models.JSONField(
        default=dict,
        verbose_name=_("usage details"),
        help_text=_("Additional usage detail counters."),
        db_comment="Additional usage detail counters.",
    )
    cost = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        null=True,
        blank=True,
        verbose_name=_("usage cost"),
        help_text=_("Accumulated cost of this conversation, if reported."),
        db_comment="Accumulated cost of this conversation, if reported.",
    )
    requests = models.BigIntegerField(
        default=0,
        verbose_name=_("requests"),
        help_text=_("Accumulated number of model requests."),
        db_comment="Accumulated number of model requests.",
    )
    tool_calls = models.BigIntegerField(
        default=0,
        verbose_name=_("tool calls"),
        help_text=_("Accumulated number of tool calls."),
        db_comment="Accumulated number of tool calls.",
    )
    deferred_tool_requests = models.JSONField(
        default=None,
        null=True,
        verbose_name=_("deferred tool requests"),
        help_text=_("JSON-serialized tool requests awaiting a result, if any."),
        db_comment="JSON-serialized tool requests awaiting a result, if any.",
    )

    objects = ConversationManager()

    class Meta(TypedModelMeta):
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        db_table_comment = "Persisted Pydantic AI conversation state."
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["conversation_id"],
                name="%(app_label)s_%(class)s_id_unq",
            )
        ]

    @override
    def __str__(self) -> str:
        """Return this conversation's identifier.

        Returns:
            The unique identifier of this conversation.
        """
        return self.conversation_id
