import hashlib

import pytest
from asgiref.sync import async_to_sync
from django.db import IntegrityError
from pydantic_ai_harness.memory import MemoryMutation, MemoryOperation, MemoryOperationConflictError

from django_pydantic_ai.memory.models import Directory, OperationKind, Receipt, StoredMemoryFile


def content_version(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class TestReceiptManager:
    @pytest.mark.django_db
    def test_get_receipt_and_aget_receipt_return_matching_record(self) -> None:
        directory = Directory.objects.create(name="receipt-scope")
        operation = MemoryOperation(id="op-1", fingerprint="abc")
        receipt = Receipt.objects.create(
            directory=directory,
            operation_id=operation.id,
            fingerprint=operation.fingerprint,
            version=content_version("first"),
            kind=OperationKind.WRITE,
            existed=False,
        )

        assert Receipt.objects.get_receipt(directory, operation) == receipt
        assert async_to_sync(Receipt.objects.aget_receipt)(directory, operation) == receipt

        with pytest.raises(MemoryOperationConflictError, match="different arguments"):
            Receipt.objects.get_receipt(directory, MemoryOperation(id="op-1", fingerprint="xyz"))

        with pytest.raises(MemoryOperationConflictError, match="different arguments"):
            async_to_sync(Receipt.objects.aget_receipt)(directory, MemoryOperation(id="op-1", fingerprint="xyz"))

    @pytest.mark.django_db
    def test_get_receipt_rejects_mismatched_fingerprint(self) -> None:
        directory = Directory.objects.create(name="receipt-fingerprint-scope")
        operation = MemoryOperation(id="op-2", fingerprint="abc")
        Receipt.objects.create(
            directory=directory,
            operation_id=operation.id,
            fingerprint=operation.fingerprint,
            version=None,
            kind=OperationKind.DELETE,
            existed=True,
        )

        with pytest.raises(MemoryOperationConflictError, match="different arguments"):
            Receipt.objects.get_receipt(directory, MemoryOperation(id="op-2", fingerprint="xyz"))

        with pytest.raises(MemoryOperationConflictError, match="different arguments"):
            async_to_sync(Receipt.objects.aget_receipt)(directory, MemoryOperation(id="op-2", fingerprint="xyz"))

    @pytest.mark.django_db
    def test_aget_mutation_replays_the_recorded_mutation(self) -> None:
        directory = Directory.objects.create(name="receipt-replay-scope")
        operation = MemoryOperation(id="op-3", fingerprint="def")
        receipt = Receipt.objects.create(
            directory=directory,
            operation_id=operation.id,
            fingerprint=operation.fingerprint,
            version=content_version("payload"),
            kind=OperationKind.WRITE,
            existed=True,
        )

        mutation = async_to_sync(Receipt.objects.aget_mutation)(directory, operation)

        assert mutation == MemoryMutation(version=content_version("payload"), replayed=True, existed=True)
        assert receipt.to_memory_mutation() == mutation


class TestModelConstraints:
    @pytest.mark.django_db
    def test_directory_name_is_unique(self) -> None:
        Directory.objects.create(name="unique")

        with pytest.raises(IntegrityError):
            Directory.objects.create(name="unique")

    @pytest.mark.django_db
    def test_receipt_operation_id_is_unique_per_directory(self) -> None:
        directory = Directory.objects.create(name="receipt-constraint-scope")
        Receipt.objects.create(
            directory=directory,
            operation_id="op-repeat",
            fingerprint="first",
            version=content_version("first"),
            kind=OperationKind.WRITE,
            existed=False,
        )

        with pytest.raises(IntegrityError):
            Receipt.objects.create(
                directory=directory,
                operation_id="op-repeat",
                fingerprint="second",
                version=content_version("second"),
                kind=OperationKind.WRITE,
                existed=True,
            )

    @pytest.mark.django_db
    def test_receipt_operation_id_may_repeat_across_directories(self) -> None:
        Directory.objects.create(name="first-receipt-scope")
        second_directory = Directory.objects.create(name="second-receipt-scope")

        receipt = Receipt.objects.create(
            directory=second_directory,
            operation_id="op-repeat",
            fingerprint="unique-to-other-directory",
            version=None,
            kind=OperationKind.DELETE,
            existed=True,
        )

        assert receipt.directory == second_directory

    @pytest.mark.django_db
    def test_stored_memory_file_path_is_unique_per_directory(self) -> None:
        first_directory = Directory.objects.create(name="first-store")
        second_directory = Directory.objects.create(name="second-store")
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

        with pytest.raises(IntegrityError):
            StoredMemoryFile.objects.create(
                directory=first_directory,
                path="shared.md",
                content="replace",
                version=content_version("replace"),
            )


class TestStoredMemoryFileManager:
    @pytest.mark.django_db
    def test_with_path_prefix_filters_only_matching_paths(self) -> None:
        directory = Directory.objects.create(name="prefix-scope")
        StoredMemoryFile.objects.create(
            directory=directory,
            path="notes/a.md",
            content="alpha",
            version=content_version("alpha"),
        )
        StoredMemoryFile.objects.create(
            directory=directory,
            path="notes/b.md",
            content="beta",
            version=content_version("beta"),
        )
        StoredMemoryFile.objects.create(
            directory=directory,
            path="archive/c.md",
            content="gamma",
            version=content_version("gamma"),
        )

        paths = list(
            StoredMemoryFile.objects.with_path_prefix("notes/").order_by("path").values_list("path", flat=True)
        )

        assert paths == ["notes/a.md", "notes/b.md"]

    @pytest.mark.django_db
    def test_model_str_methods_return_expected_values(self) -> None:
        directory = Directory.objects.create(name="str-scope")
        file = StoredMemoryFile.objects.create(
            directory=directory,
            path="docs/guide.md",
            content="text",
            version=content_version("text"),
        )
        receipt = Receipt.objects.create(
            directory=directory,
            operation_id="op-str",
            fingerprint="abc",
            version=content_version("latest"),
            kind=OperationKind.WRITE,
            existed=True,
        )

        assert str(directory) == "str-scope"
        assert str(file) == "docs/guide.md"
        assert str(receipt) == "Write operation op-str"
