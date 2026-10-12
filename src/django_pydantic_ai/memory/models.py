"""Database models for the Django-backed Pydantic AI memory store."""

from __future__ import annotations

from typing import ClassVar, override

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta
from pydantic_ai_harness.memory import MemoryMutation, MemoryOperation, MemoryOperationConflictError


class Directory(models.Model):
    """Logical namespace containing memory files and operation receipts."""

    name = models.TextField(
        verbose_name=_("directory name"),
        help_text=_("Unique name identifying this memory directory."),
        db_comment="Unique name identifying this memory directory.",
    )

    class Meta(TypedModelMeta):
        verbose_name = _("memory directory")
        verbose_name_plural = _("memory directories")
        db_table_comment = "Namespaces containing persisted memory files and operation receipts."
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["name"],
                name="%(app_label)s_%(class)s_name_unq",
            )
        ]

    @override
    def __str__(self) -> str:
        """Return this directory's name.

        Returns:
            The unique name identifying this directory.
        """
        return self.name


class ReceiptManager(models.Manager["Receipt"]):
    """Query operation receipts and validate their fingerprints."""

    def _validate_receipt(self, receipt: Receipt, operation: MemoryOperation) -> None:
        """Ensure a receipt matches the operation that claims its ID.

        Args:
            receipt: Stored result associated with the operation ID.
            operation: Operation whose fingerprint must match the receipt.

        Returns:
            `None`.

        Raises:
            MemoryOperationConflictError: If the fingerprints do not match.
        """
        if receipt.fingerprint != operation.fingerprint:
            msg = f"operation id {operation.id!r} was reused with different arguments"
            raise MemoryOperationConflictError(msg)

    def get_receipt(self, directory: Directory, operation: MemoryOperation) -> Receipt | None:
        """Return the receipt for an operation, if it has been recorded.

        Args:
            directory: Directory that owns the operation receipt.
            operation: Operation whose receipt should be retrieved.

        Returns:
            The matching receipt, or `None` if no receipt exists.

        Raises:
            MemoryOperationConflictError: If the operation ID has a different fingerprint.
        """
        try:
            instance = Receipt.objects.get(directory=directory, operation_id=operation.id)
        except Receipt.DoesNotExist:
            return None
        else:
            self._validate_receipt(instance, operation)
            return instance

    async def aget_receipt(self, directory: Directory, operation: MemoryOperation) -> Receipt | None:
        """Return the receipt for an operation, if it has been recorded.

        Async version of :meth:`get_receipt`.

        Args:
            directory: Directory that owns the operation receipt.
            operation: Operation whose receipt should be retrieved.

        Returns:
            The matching receipt, or `None` if no receipt exists.

        Raises:
            MemoryOperationConflictError: If the operation ID has a different fingerprint.
        """
        try:
            instance = await Receipt.objects.aget(directory=directory, operation_id=operation.id)
        except Receipt.DoesNotExist:
            return None
        else:
            self._validate_receipt(instance, operation)
            return instance

    async def aget_mutation(self, directory: Directory, operation: MemoryOperation) -> MemoryMutation | None:
        """Return the mutation represented by an operation's receipt, if present.

        Args:
            directory: Directory that owns the operation receipt.
            operation: Operation whose receipt should be retrieved.

        Returns:
            The recorded mutation result, marked as replayed, or `None` if no
            receipt exists.

        Raises:
            MemoryOperationConflictError: If the operation ID has a different
                fingerprint.
        """
        receipt = await self.aget_receipt(directory, operation)
        return receipt.to_memory_mutation() if receipt is not None else None


class OperationKind(models.TextChoices):
    """Kinds of memory mutations recorded in operation receipts."""

    WRITE = "write", "Write"
    DELETE = "delete", "Delete"


class Receipt(models.Model):
    """Idempotency record for a completed memory operation."""

    directory = models.ForeignKey(
        Directory,
        on_delete=models.DB_CASCADE,
        db_index=False,
        verbose_name=_("directory"),
        help_text=_("Directory that owns this operation receipt."),
        db_comment="Directory that owns this operation receipt.",
    )
    operation_id = models.TextField(
        verbose_name=_("operation ID"),
        help_text=_("Unique identifier assigned to this memory operation."),
        db_comment="Unique identifier assigned to the memory operation.",
    )
    fingerprint = models.TextField(
        verbose_name=_("operation fingerprint"),
        help_text=_("Fingerprint of the arguments associated with this operation ID."),
        db_comment="Fingerprint used to detect reuse of an operation ID with different arguments.",
    )
    version = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("version"),
        help_text=_("Version value assigned to the memory mutation, or null for deletes."),
        db_comment="Version value assigned to the memory mutation, or null for deletes.",
    )
    kind = models.CharField(
        max_length=10,
        choices=OperationKind,
        verbose_name=_("operation kind"),
        help_text=_("Kind of memory mutation recorded by this receipt."),
        db_comment="Kind of memory mutation recorded by this receipt.",
    )
    existed = models.BooleanField(
        verbose_name=_("path existed"),
        help_text=_("Whether the target memory path existed before the operation."),
        db_comment="Whether the target memory path existed before the operation.",
    )

    objects = ReceiptManager()

    class Meta(TypedModelMeta):
        verbose_name = _("operation receipt")
        verbose_name_plural = _("operation receipts")
        db_table_comment = "Receipts for idempotent memory operations."
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["directory", "operation_id"],
                name="%(app_label)s_%(class)s_unq",
            )
        ]

    @override
    def __str__(self) -> str:
        """Return a readable description of this operation receipt.

        Returns:
            The operation kind and its identifier.
        """
        return f"{self.get_kind_display()} operation {self.operation_id}"

    def to_memory_mutation(self) -> MemoryMutation:
        """Convert this receipt to the mutation result returned on replay.

        Returns:
            The mutation result represented by this receipt.
        """
        return MemoryMutation(
            version=self.version or None,
            replayed=True,
            existed=self.existed,
        )


class StoredMemoryFileQuerySet(models.QuerySet["StoredMemoryFile"]):
    """Build reusable queries for persisted memory files."""

    def with_path_prefix(self, prefix: str) -> StoredMemoryFileQuerySet:
        """Filter files whose paths start with a prefix.

        Args:
            prefix: Prefix that stored paths must start with.

        Returns:
            A queryset containing matching files.
        """
        return self.filter(path__startswith=prefix)


class StoredMemoryFileManager(models.Manager["StoredMemoryFile"]):
    """Expose memory-file queries with precise model types."""

    @override
    def get_queryset(self) -> StoredMemoryFileQuerySet:
        """Return the typed queryset used by this manager.

        Returns:
            A queryset for stored memory files.
        """
        return StoredMemoryFileQuerySet(self.model, using=self._db)

    def with_path_prefix(self, prefix: str) -> StoredMemoryFileQuerySet:
        """Filter files whose paths start with a prefix.

        Args:
            prefix: Prefix that stored paths must start with.

        Returns:
            A queryset containing matching files.
        """
        return self.get_queryset().with_path_prefix(prefix)


class StoredMemoryFile(models.Model):
    """Persisted memory file, uniquely identified by its path."""

    directory = models.ForeignKey(
        Directory,
        on_delete=models.DB_CASCADE,
        db_index=False,
        verbose_name=_("directory"),
        help_text=_("Directory that owns this memory file."),
        db_comment="Directory that owns this memory file.",
    )
    path = models.TextField(
        verbose_name=_("path"),
        help_text=_("Unique path identifying this memory file."),
        db_comment="Unique path identifying this memory file.",
    )
    content = models.TextField(
        verbose_name=_("content"),
        help_text=_("Text content stored at this memory path."),
        db_comment="Text content stored at this memory path.",
    )
    version = models.CharField(
        max_length=64,
        default="",
        verbose_name=_("version"),
        help_text=_("Version value of the latest mutation to this file."),
        db_comment="Version value of the latest mutation to this file.",
    )
    last_operation = models.ForeignKey(
        Receipt,
        on_delete=models.DB_SET_NULL,
        null=True,
        db_index=False,
        verbose_name=_("last operation"),
        help_text=_("Receipt for the most recent operation that changed this file, if available."),
        db_comment="Receipt for the most recent operation that changed this file, if available.",
    )

    objects = StoredMemoryFileManager()

    class Meta(TypedModelMeta):
        verbose_name = _("stored memory file")
        verbose_name_plural = _("stored memory files")
        db_table_comment = "Persisted files in the Django-backed memory store."
        ordering: ClassVar = ["path"]
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["directory", "path"],
                name="%(app_label)s_%(class)s_unq",
            )
        ]

    @override
    def __str__(self) -> str:
        """Return this memory file's path.

        Returns:
            The path identifying this file.
        """
        return self.path
