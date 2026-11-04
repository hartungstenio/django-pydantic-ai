"""Database models for Pydantic AI conversations."""

from __future__ import annotations

from typing import override

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta


class Message(models.Model):
    message = models.JSONField(
        verbose_name=_("serialized message"),
        help_text=_("JSON-serialized Pydantic AI model message."),
        db_comment="JSON-serialized Pydantic AI model message.",
    )

    @override
    def __str__(self) -> str:
        """Return this message's primary key.

        Returns:
            This message's primary key.
        """
        return f"Message {self.pk}"

    class Meta(TypedModelMeta):
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        db_table_comment = "Serialized Pydantic AI model messages."
        ordering = ["pk"]


class Entry(models.Model):
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        verbose_name=_("parent entry"),
        db_index=False,
        help_text=_("Previous entry in this conversation."),
        db_comment="Previous entry in this conversation.",
    )
    kind = models.CharField(
        verbose_name=_("entry kind"),
        default="message",
        db_default="message",
        help_text=_("Type of conversation entry, such as a message."),
        db_comment="Type of conversation entry, such as a message.",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name=_("message"),
        db_index=False,
        help_text=_("Message associated with this conversation entry."),
        db_comment="Message associated with this conversation entry.",
    )

    @override
    def __str__(self) -> str:
        """Return this entry's identifier and kind.

        Returns:
            This entry's identifier and kind.
        """
        return f"Conversation entry {self.pk} ({self.kind})"

    class Meta(TypedModelMeta):
        verbose_name = _("conversation entry")
        verbose_name_plural = _("conversation entries")
        db_table_comment = "Entries in persisted Pydantic AI conversation histories."
        ordering = ["pk"]
        indexes = [
            models.Index(fields=["parent"], name="%(app_label)s_%(class)s_parent_idx"),
            models.Index(fields=["message"], name="%(app_label)s_%(class)s_msg_idx"),
        ]


class Record(models.Model):
    conversation_id = models.TextField(
        verbose_name=_("conversation ID"),
        help_text=_("Unique identifier shared by all runs in this conversation."),
        db_comment="Unique identifier shared by all runs in this conversation.",
    )
    record = models.JSONField(
        verbose_name=_("Pydantic AI record"),
        help_text=_("JSON-serialized Pydantic AI conversation record."),
        db_comment="JSON-serialized Pydantic AI conversation record.",
    )
    head = models.ForeignKey(
        Entry,
        on_delete=models.PROTECT,
        verbose_name=_("head entry"),
        db_index=False,
        help_text=_("Latest entry in this conversation record."),
        db_comment="Latest entry in this conversation record.",
    )
    revision = models.CharField(
        verbose_name=_("revision"),
        help_text=_("Revision identifier for this conversation record."),
        db_comment="Revision identifier for this conversation record.",
    )
    scope = models.CharField(
        verbose_name=_("scope"),
        help_text=_("Scope used to isolate this conversation record."),
        db_comment="Scope used to isolate this conversation record.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("last updated"),
        help_text=_("Date and time this conversation record was last updated."),
        db_comment="Date and time this conversation record was last updated.",
    )

    @override
    def __str__(self) -> str:
        """Return this record's conversation, scope, and revision.

        Returns:
            This record's identifying conversation details.
        """
        return f"Conversation record {self.conversation_id} (scope={self.scope}, revision={self.revision})"

    class Meta(TypedModelMeta):
        verbose_name = _("conversation record")
        verbose_name_plural = _("conversation records")
        db_table_comment = "Current conversation heads and revision metadata."
        ordering = ["-updated_at", "pk"]
        indexes = [
            models.Index(fields=["head"], name="%(app_label)s_%(class)s_head_idx"),
            models.Index(fields=["scope", "updated_at"], name="%(app_label)s_%(class)s_s_upd_idx"),
            models.Index(fields=["updated_at"], name="%(app_label)s_%(class)s_upd_idx"),
        ]
