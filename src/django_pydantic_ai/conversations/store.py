from collections.abc import Sequence
from typing import override

from pydantic import TypeAdapter
from pydantic_ai import ModelMessage
from pydantic_ai.conversation_store import (
    ConversationConflict,
    ConversationEntry,
    ConversationRecord,
    ConversationStore,
)

from .models import Entry, Record

ModelMessageTypeAdapter = TypeAdapter(ModelMessage)
ConversationRecordTypeAdapter = TypeAdapter(ConversationRecord)


class DjangoConversationStore(ConversationStore):
    @override
    async def read_record(self, conversation_id: str) -> ConversationRecord | None:
        """The record for a conversation, or `None` if the store doesn't have it."""
        try:
            record = await Record.objects.aget(conversation_id=conversation_id)
        except Record.DoesNotExist:
            return None
        else:
            return ConversationRecordTypeAdapter.validate_python(record.record)

    @override
    async def read_records(self, *, scope: str | None = None, limit: int | None = None) -> Sequence[ConversationRecord]:
        """The stored records, or those with the given `scope`, newest `updated_at` first, and at most `limit` of them."""
        qs = Record.objects.order_by("-updated_at")
        if scope is not None:
            qs = qs.filter(scope=scope)
        if limit is not None:
            qs = qs[:limit]

        return [ConversationRecordTypeAdapter.validate_python(record.record) async for record in qs]

    @override
    async def write_record(
        self,
        record: ConversationRecord,
        *,
        new_entries: Sequence[ConversationEntry] = (),
        expected_revision: str | None,
    ) -> None:
        """Store a record and the new entries its history adds, replacing the record with `expected_revision`.

        `new_entries` are in order, each after the one it points at. A backend that can should
        store them and the record together, so a conflict leaves neither behind.

        Raises:
            ConversationConflict: If the stored record's revision isn't `expected_revision`, a record
                exists when `expected_revision` is `None`, or `record.head_id` names an entry that
                neither the store nor `new_entries` has, because a concurrent delete or rewrite of
                the conversation a fork points into released it.
        """
        raise NotImplementedError

    @override
    async def delete_record(self, conversation_id: str, *, expected_revision: str) -> None:
        """Delete a conversation's record, and, where the backend can do so safely, the entries no remaining record's history reaches.

        A backend that keeps those entries, say because it can't tell them from ones a concurrent
        save is about to use, should say so in its documentation.

        Raises:
            ConversationConflict: If no record with `expected_revision` is stored, because the
                conversation was saved, replaced or deleted since it was read.
        """
        existing, _ = await Record.objects.filter(conversation_id=conversation_id, revision=expected_revision).adelete()
        if not existing:
            raise ConversationConflict(conversation_id)

    @override
    async def read_entry(self, entry_id: str) -> ConversationEntry:
        """The entry with this identifier.

        Backends that can read a whole history in one query should override
        [`read_history`][pydantic_ai.conversation_store.ConversationStore.read_history] instead of
        relying on one call per entry.
        """
        try:
            entry = await Entry.objects.select_related("message").aget(pk=entry_id)
        except Entry.DoesNotExist as exc:
            raise KeyError(entry_id) from exc
        else:
            return ConversationEntry(
                id=str(entry.pk),
                parent_id=str(entry.parent_id),
                message=ModelMessageTypeAdapter.validate_python(entry.message.message),
            )
