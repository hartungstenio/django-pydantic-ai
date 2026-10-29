"""Django-backed implementation of the Pydantic AI memory store."""

import hashlib

from asgiref.sync import sync_to_async
from django.db import IntegrityError, transaction
from django.db.models import Q
from pydantic_ai_harness.memory import (
    MemoryConflictError,
    MemoryFile,
    MemoryMutation,
    MemoryOperation,
    MemorySearchResult,
)
from pydantic_ai_harness.memory._store import lexical_search, validate_store_prefix

from django_pydantic_ai.memory.models import OperationKind

from .models import Directory, Receipt, StoredMemoryFile


class DjangoModelStore:
    """Persist memory files and operation receipts in Django models.

    Each store instance is scoped to one directory.

    Writes and deletes use version checks to detect concurrent changes. When an
    operation is provided, its receipt makes successful mutations replayable.
    """

    def __init__(self, directory: Directory) -> None:
        """Bind this store to a memory directory.

        Args:
            directory: Directory that scopes all store operations.
        """
        self.directory = directory

    @staticmethod
    def _content_version(content: str) -> str:
        """Return the hash-based version for a file's content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def read(self, path: str, *, max_chars: int) -> MemoryFile | None:
        """Read a file, truncating its content when it exceeds the character limit.

        Args:
            path: Path of the memory file to read.
            max_chars: Maximum number of content characters to return.

        Returns:
            The file with its version and last operation ID, or `None` if the path
            does not exist. The `truncated` attribute indicates omitted content.
        """
        try:
            memory_file = await StoredMemoryFile.objects.select_related("last_operation").aget(
                directory=self.directory, path=path
            )
        except StoredMemoryFile.DoesNotExist:
            return None
        else:
            return MemoryFile(
                content=memory_file.content[:max_chars],
                version=memory_file.version,
                operation_id=memory_file.last_operation.operation_id if memory_file.last_operation else None,
                truncated=len(memory_file.content) > max_chars,
            )

    async def get_operation(self, operation: MemoryOperation) -> MemoryMutation | None:
        """Look up the recorded result for an operation.

        Args:
            operation: Operation whose receipt should be retrieved.

        Returns:
            The previous mutation result, marked as replayed, or `None` if the
            operation has not been recorded.

        Raises:
            pydantic_ai_harness.memory.MemoryOperationConflictError: If the ID was
                previously used with different operation arguments.
        """
        return await Receipt.objects.aget_mutation(self.directory, operation)

    async def write(
        self,
        path: str,
        content: str,
        *,
        expected_version: str | None,
        operation: MemoryOperation | None = None,
    ) -> MemoryMutation:
        """Create or replace a file if its current version matches the expectation.

        If `expected_version` is `None`, the path must not already exist. Supplying
        an operation makes the mutation idempotent: a matching prior receipt is
        returned instead of applying the write again.

        Args:
            path: Path of the file to create or replace.
            content: New content to store at the path.
            expected_version: Current version required for replacement, or `None`
                to require that the path does not exist.
            operation: Optional identifier and fingerprint for replay protection.

        Returns:
            The resulting version, whether this call was replayed, and whether the
            file existed before the mutation.

        Raises:
            MemoryConflictError: If the path's existence or version differs from
                the expectation.
            pydantic_ai_harness.memory.MemoryOperationConflictError: If the
                operation ID was reused with different arguments.
        """
        if (
            operation is not None
            and (mutation := await Receipt.objects.aget_mutation(self.directory, operation)) is not None
        ):
            return mutation

        @sync_to_async
        @transaction.atomic
        def _write() -> MemoryMutation:
            version = self._content_version(content)
            existed = expected_version is not None
            if operation is not None:
                receipt = Receipt.objects.create(
                    directory=self.directory,
                    operation_id=operation.id,
                    fingerprint=operation.fingerprint,
                    version=version,
                    kind=OperationKind.WRITE,
                    existed=existed,
                )
            else:
                receipt = None

            if expected_version is None:
                try:
                    current = StoredMemoryFile.objects.create(
                        directory=self.directory,
                        path=path,
                        content=content,
                        version=version,
                        last_operation=receipt,
                    )
                except IntegrityError as exc:
                    msg = f"memory path {path!r} changed before it could be written"
                    raise MemoryConflictError(msg) from exc
            else:
                try:
                    current = StoredMemoryFile.objects.select_for_update(no_key=True).get(
                        directory=self.directory, path=path, version=expected_version
                    )
                except StoredMemoryFile.DoesNotExist as exc:
                    msg = f"memory path {path!r} changed before it could be written"
                    raise MemoryConflictError(msg) from exc
                else:
                    current.content = content
                    current.version = version
                    current.last_operation = receipt
                    current.save()

            return MemoryMutation(
                version=version,
                replayed=False,
                existed=existed,
            )

        return await _write()

    async def delete(
        self,
        path: str,
        *,
        expected_version: str | None,
        operation: MemoryOperation | None = None,
    ) -> MemoryMutation:
        """Delete a file if its current version matches the expectation.

        If `expected_version` is `None`, the path must not exist. Supplying an
        operation makes the mutation idempotent: a matching prior receipt is
        returned instead of applying the delete again.

        Args:
            path: Path of the file to delete.
            expected_version: Current version required for deletion, or `None` to
                require that the path does not exist.
            operation: Optional identifier and fingerprint for replay protection.

        Returns:
            The mutation result, including its version and whether a file existed
            to be deleted.

        Raises:
            MemoryConflictError: If the path's existence or version differs from
                the expectation.
            pydantic_ai_harness.memory.MemoryOperationConflictError: If the
                operation ID was reused with different arguments.
        """
        if (
            operation is not None
            and (mutation := await Receipt.objects.aget_mutation(self.directory, operation)) is not None
        ):
            return mutation

        @sync_to_async
        @transaction.atomic
        def _delete() -> MemoryMutation:
            filters = Q(directory=self.directory, path=path)
            if expected_version:
                filters &= Q(version=expected_version)

            deleted, _ = StoredMemoryFile.objects.filter(filters).delete()
            if bool(deleted) != bool(expected_version):
                msg = f"memory path {path!r} changed before it could be deleted"
                raise MemoryConflictError(msg)

            existed = deleted > 0

            if operation is not None:
                Receipt.objects.create(
                    directory=self.directory,
                    operation_id=operation.id,
                    fingerprint=operation.fingerprint,
                    version="",
                    kind=OperationKind.DELETE,
                    existed=existed,
                )

            return MemoryMutation(
                version=None,
                replayed=False,
                existed=existed,
            )

        return await _delete()

    async def list_paths(self, prefix: str = "", *, limit: int) -> list[str]:
        """List stored paths that start with a prefix.

        Args:
            prefix: Prefix used to filter stored paths.
            limit: Maximum number of paths to return.

        Returns:
            Matching path names in ascending lexicographic order, limited to at
            most `limit` entries.
        """
        validate_store_prefix(prefix)
        return [
            path
            async for path in StoredMemoryFile.objects.with_path_prefix(prefix)
            .filter(directory=self.directory)
            .order_by("path")
            .values_list("path", flat=True)[:limit]
        ]

    async def search(  # noqa: PLR0913
        self,
        prefix: str,
        query: str,
        *,
        limit: int,
        max_files: int,
        max_chars: int,
        max_file_chars: int,
    ) -> MemorySearchResult:
        """Search files below a prefix with bounded lexical matching.

        Args:
            prefix: Trusted path prefix that bounds the search scope.
            query: Whitespace-separated terms to search for.
            limit: Maximum number of matches to return.
            max_files: Maximum number of files to scan.
            max_chars: Maximum combined path and snippet characters to return.
            max_file_chars: Maximum content characters to inspect per file.

        Returns:
            Ranked matches, the number of scanned files, and whether results or
            file contents were truncated.

        Raises:
            ValueError: If `prefix` is invalid.
        """
        validate_store_prefix(prefix)
        if not query.split() or limit <= 0 or max_files <= 0 or max_chars <= 0 or max_file_chars <= 0:
            return MemorySearchResult(matches=[], scanned=0, truncated=False)

        files = [
            f
            async for f in StoredMemoryFile.objects.with_path_prefix(prefix)
            .filter(directory=self.directory)
            .order_by("path")[: max_files + 1]
        ]
        result = await lexical_search(
            [(file.path, file.content[:max_file_chars]) for file in files],
            query,
            limit=limit,
            max_files=max_files,
            max_chars=max_chars,
            score_prefix=prefix,
        )
        return MemorySearchResult(
            matches=result.matches,
            scanned=result.scanned,
            truncated=result.truncated or any(len(f.content) > max_file_chars for f in files),
        )
