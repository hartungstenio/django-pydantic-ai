import hashlib

import pytest
from asgiref.sync import async_to_sync
from pydantic_ai_harness.memory import MemoryConflictError, MemoryOperation, MemoryOperationConflictError

from django_pydantic_ai.memory.models import Directory, StoredMemoryFile
from django_pydantic_ai.memory.store import DjangoModelStore


def content_version(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class TestDjangoModelStore:
    @pytest.mark.django_db
    def test_read_returns_file_and_truncates_content(self) -> None:
        directory = Directory.objects.create(name="read-scope")
        store = DjangoModelStore(directory)

        StoredMemoryFile.objects.create(
            directory=directory,
            path="notes/readme.md",
            content="hello world",
            version=content_version("hello world"),
        )

        result = async_to_sync(store.read)("notes/readme.md", max_chars=5)

        assert result is not None
        assert result.content == "hello"
        assert result.version == content_version("hello world")
        assert result.truncated is True

    @pytest.mark.django_db
    def test_read_returns_none_for_missing_file(self) -> None:
        directory = Directory.objects.create(name="missing-scope")

        result = async_to_sync(DjangoModelStore(directory).read)("missing.md", max_chars=10)

        assert result is None

    @pytest.mark.django_db
    def test_get_operation_returns_replayed_mutation_and_validates_fingerprint(self) -> None:
        directory = Directory.objects.create(name="operation-scope")
        store = DjangoModelStore(directory)
        operation = MemoryOperation(id="op-1", fingerprint="abc")

        mutation = async_to_sync(store.write)("notes/alpha.md", "initial", expected_version=None, operation=operation)
        replayed = async_to_sync(store.get_operation)(operation)

        assert mutation.replayed is False
        assert mutation.existed is False
        assert replayed is not None
        assert replayed.version == mutation.version == content_version("initial")
        assert replayed.replayed is True
        assert replayed.existed == mutation.existed

        with pytest.raises(MemoryOperationConflictError, match="different arguments"):
            async_to_sync(store.write)(
                "notes/alpha.md",
                "changed",
                expected_version=None,
                operation=MemoryOperation(id="op-1", fingerprint="xyz"),
            )

    @pytest.mark.django_db
    def test_write_creates_new_file_and_tracks_operation(self) -> None:
        directory = Directory.objects.create(name="write-scope")
        store = DjangoModelStore(directory)
        operation = MemoryOperation(id="write-op", fingerprint="write")

        mutation = async_to_sync(store.write)("notes/new.md", "created", expected_version=None, operation=operation)
        file = async_to_sync(store.read)("notes/new.md", max_chars=100)

        assert mutation.version == content_version("created")
        assert mutation.replayed is False
        assert mutation.existed is False
        assert file is not None
        assert file.content == "created"
        assert file.operation_id == operation.id
        assert file.version == mutation.version

    @pytest.mark.django_db
    def test_write_rejects_conflicting_expected_version(self) -> None:
        directory = Directory.objects.create(name="write-conflict-scope")
        store = DjangoModelStore(directory)
        async_to_sync(store.write)("notes/locked.md", "original", expected_version=None)

        with pytest.raises(MemoryConflictError, match="changed before it could be written"):
            async_to_sync(store.write)("notes/locked.md", "replacement", expected_version="999")

    @pytest.mark.django_db
    def test_write_replays_matching_operation_idempotently(self) -> None:
        directory = Directory.objects.create(name="replay-write-scope")
        store = DjangoModelStore(directory)
        operation = MemoryOperation(id="op-replay", fingerprint="same")

        first = async_to_sync(store.write)("notes/replay.md", "value", expected_version=None, operation=operation)
        second = async_to_sync(store.write)("notes/replay.md", "other", expected_version=None, operation=operation)

        assert first.replayed is False
        assert second.replayed is True
        assert first.version == second.version == content_version("value")
        assert first.existed is second.existed is False
        assert async_to_sync(store.read)("notes/replay.md", max_chars=100) is not None

    @pytest.mark.django_db
    def test_versions_are_content_hashes_and_not_directory_scoped(self) -> None:
        first_directory = Directory.objects.create(name="version-first")
        second_directory = Directory.objects.create(name="version-second")
        first_store = DjangoModelStore(first_directory)
        second_store = DjangoModelStore(second_directory)

        first_mutation = async_to_sync(first_store.write)("notes/first.md", "value", expected_version=None)
        second_mutation = async_to_sync(second_store.write)("notes/second.md", "value", expected_version=None)

        assert first_mutation.version == second_mutation.version == content_version("value")

        follow_up = async_to_sync(first_store.write)(
            "notes/first.md", "updated", expected_version=first_mutation.version
        )

        assert follow_up.version == content_version("updated")

    @pytest.mark.django_db
    def test_delete_removes_file_and_records_receipt(self) -> None:
        directory = Directory.objects.create(name="delete-scope")
        store = DjangoModelStore(directory)
        initial = async_to_sync(store.write)("notes/delete.md", "payload", expected_version=None)

        mutation = async_to_sync(store.delete)("notes/delete.md", expected_version=initial.version)

        assert mutation.existed is True
        assert mutation.replayed is False
        assert mutation.version is None
        assert async_to_sync(store.read)("notes/delete.md", max_chars=10) is None

    @pytest.mark.django_db
    def test_delete_rejects_conflicting_expected_version(self) -> None:
        directory = Directory.objects.create(name="delete-conflict-scope")
        store = DjangoModelStore(directory)
        async_to_sync(store.write)("notes/deleteme.md", "payload", expected_version=None)

        with pytest.raises(MemoryConflictError, match="changed before it could be deleted"):
            async_to_sync(store.delete)("notes/deleteme.md", expected_version="999")

    @pytest.mark.django_db
    def test_list_paths_filters_and_limits_prefix_matches(self) -> None:
        directory = Directory.objects.create(name="list-scope")
        StoredMemoryFile.objects.create(
            directory=directory, path="notes/a.md", content="alpha", version=content_version("alpha")
        )
        StoredMemoryFile.objects.create(
            directory=directory, path="notes/b.md", content="beta", version=content_version("beta")
        )
        StoredMemoryFile.objects.create(
            directory=directory, path="other/z.md", content="zeta", version=content_version("zeta")
        )

        assert async_to_sync(DjangoModelStore(directory).list_paths)(prefix="notes/", limit=10) == [
            "notes/a.md",
            "notes/b.md",
        ]
        assert async_to_sync(DjangoModelStore(directory).list_paths)(prefix="docs/", limit=10) == []

    @pytest.mark.django_db
    def test_search_ranks_matches_and_bounds_scan_to_prefix(self) -> None:
        directory = Directory.objects.create(name="search-scope")
        StoredMemoryFile.objects.create(
            directory=directory,
            path="notes/a.md",
            content="needle",
            version=content_version("needle"),
        )
        StoredMemoryFile.objects.create(
            directory=directory,
            path="notes/b.md",
            content="needle",
            version=content_version("needle"),
        )
        StoredMemoryFile.objects.create(
            directory=directory,
            path="notes/c.md",
            content="needle",
            version=content_version("needle"),
        )
        StoredMemoryFile.objects.create(
            directory=directory,
            path="other/a.md",
            content="needle",
            version=content_version("needle"),
        )

        max_files = 2
        result = async_to_sync(DjangoModelStore(directory).search)(
            "notes/",
            "needle",
            limit=1,
            max_files=max_files,
            max_chars=100,
            max_file_chars=100,
        )

        assert [match.path for match in result.matches] == ["notes/a.md"]
        assert result.scanned == max_files
        assert result.truncated is True

    @pytest.mark.django_db
    def test_search_reports_content_truncated_by_per_file_limit(self) -> None:
        directory = Directory.objects.create(name="truncated-scope")
        StoredMemoryFile.objects.create(
            directory=directory,
            path="truncated/a.md",
            content="prefix needle",
            version=content_version("prefix needle"),
        )

        result = async_to_sync(DjangoModelStore(directory).search)(
            "truncated/",
            "needle",
            limit=10,
            max_files=10,
            max_chars=100,
            max_file_chars=7,
        )

        assert result.matches == []
        assert result.scanned == 1
        assert result.truncated is True

    @pytest.mark.django_db
    def test_search_rejects_invalid_prefix_and_empty_query(self) -> None:
        directory = Directory.objects.create(name="search-validation-scope")
        store = DjangoModelStore(directory)

        with pytest.raises(ValueError, match="invalid memory path"):
            async_to_sync(store.search)("../outside", "needle", limit=1, max_files=1, max_chars=10, max_file_chars=10)

        result = async_to_sync(store.search)("notes/", "", limit=1, max_files=1, max_chars=10, max_file_chars=10)

        assert result.matches == []
        assert result.scanned == 0
        assert result.truncated is False

    @pytest.mark.django_db
    def test_store_operations_are_scoped_to_directory(self) -> None:
        first_directory = Directory.objects.create(name="scope-first")
        second_directory = Directory.objects.create(name="scope-second")
        StoredMemoryFile.objects.create(
            directory=first_directory,
            path="shared.md",
            content="first",
            version=content_version("first"),
        )
        StoredMemoryFile.objects.create(
            directory=second_directory,
            path="shared.md",
            content="second",
            version=content_version("second"),
        )
        first_store = DjangoModelStore(first_directory)
        second_store = DjangoModelStore(second_directory)

        first_file = async_to_sync(first_store.read)("shared.md", max_chars=100)
        second_file = async_to_sync(second_store.read)("shared.md", max_chars=100)
        assert first_file is not None
        assert second_file is not None
        assert first_file.content == "first"
        assert second_file.content == "second"
        assert async_to_sync(first_store.list_paths)(limit=10) == ["shared.md"]

        async_to_sync(first_store.write)("new.md", "first only", expected_version=None)
        assert async_to_sync(first_store.read)("new.md", max_chars=100) is not None
        assert async_to_sync(second_store.read)("new.md", max_chars=100) is None

        async_to_sync(first_store.delete)("shared.md", expected_version=first_file.version)
        assert async_to_sync(first_store.read)("shared.md", max_chars=100) is None
        assert async_to_sync(second_store.read)("shared.md", max_chars=100).content == "second"
