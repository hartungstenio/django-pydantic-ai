from django_pydantic_ai.conversations.models import Entry, Message, Record


class TestMessage:
    def test_str_uses_primary_key(self) -> None:
        message = Message(pk=1, message={})

        assert str(message) == "Message 1"


class TestEntry:
    def test_str_uses_local_fields_without_loading_foreign_keys(self) -> None:
        entry = Entry(pk=2, parent_id=1, message_id=1, kind="message")

        assert str(entry) == "Conversation entry 2 (message)"


class TestRecord:
    def test_str_uses_local_fields_without_loading_foreign_keys(self) -> None:
        record = Record(
            pk=3,
            conversation_id="conversation-1",
            head_id=2,
            revision="revision-4",
            scope="tenant-1",
        )

        assert str(record) == "Conversation record conversation-1 (scope=tenant-1, revision=revision-4)"
