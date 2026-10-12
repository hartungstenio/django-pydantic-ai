import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    # pyrefly: ignore [implicit-any-empty-container]
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Directory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.TextField(
                        db_comment="Unique name identifying this memory directory.",
                        help_text="Unique name identifying this memory directory.",
                        verbose_name="directory name",
                    ),
                ),
            ],
            options={
                "verbose_name": "memory directory",
                "verbose_name_plural": "memory directories",
                "db_table_comment": "Namespaces containing persisted memory files and operation receipts.",
                "constraints": [models.UniqueConstraint(fields=("name",), name="memory_directory_name_unq")],
            },
        ),
        migrations.CreateModel(
            name="Receipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "operation_id",
                    models.TextField(
                        db_comment="Unique identifier assigned to the memory operation.",
                        help_text="Unique identifier assigned to this memory operation.",
                        verbose_name="operation ID",
                    ),
                ),
                (
                    "fingerprint",
                    models.TextField(
                        db_comment="Fingerprint used to detect reuse of an operation ID with different arguments.",
                        help_text="Fingerprint of the arguments associated with this operation ID.",
                        verbose_name="operation fingerprint",
                    ),
                ),
                (
                    "version",
                    models.CharField(
                        blank=True,
                        db_comment="Version value assigned to the memory mutation, or null for deletes.",
                        help_text="Version value assigned to the memory mutation, or null for deletes.",
                        max_length=64,
                        null=True,
                        verbose_name="version",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("write", "Write"), ("delete", "Delete")],
                        db_comment="Kind of memory mutation recorded by this receipt.",
                        help_text="Kind of memory mutation recorded by this receipt.",
                        max_length=10,
                        verbose_name="operation kind",
                    ),
                ),
                (
                    "existed",
                    models.BooleanField(
                        db_comment="Whether the target memory path existed before the operation.",
                        help_text="Whether the target memory path existed before the operation.",
                        verbose_name="path existed",
                    ),
                ),
                (
                    "directory",
                    models.ForeignKey(
                        db_comment="Directory that owns this operation receipt.",
                        db_index=False,
                        help_text="Directory that owns this operation receipt.",
                        on_delete=django.db.models.deletion.DB_CASCADE,
                        to="memory.directory",
                        verbose_name="directory",
                    ),
                ),
            ],
            options={
                "verbose_name": "operation receipt",
                "verbose_name_plural": "operation receipts",
                "db_table_comment": "Receipts for idempotent memory operations.",
            },
        ),
        migrations.CreateModel(
            name="StoredMemoryFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "path",
                    models.TextField(
                        db_comment="Unique path identifying this memory file.",
                        help_text="Unique path identifying this memory file.",
                        verbose_name="path",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        db_comment="Text content stored at this memory path.",
                        help_text="Text content stored at this memory path.",
                        verbose_name="content",
                    ),
                ),
                (
                    "version",
                    models.CharField(
                        db_comment="Version value of the latest mutation to this file.",
                        default="",
                        help_text="Version value of the latest mutation to this file.",
                        max_length=64,
                        verbose_name="version",
                    ),
                ),
                (
                    "directory",
                    models.ForeignKey(
                        db_comment="Directory that owns this memory file.",
                        db_index=False,
                        help_text="Directory that owns this memory file.",
                        on_delete=django.db.models.deletion.DB_CASCADE,
                        to="memory.directory",
                        verbose_name="directory",
                    ),
                ),
                (
                    "last_operation",
                    models.ForeignKey(
                        db_comment="Receipt for the most recent operation that changed this file, if available.",
                        db_index=False,
                        help_text="Receipt for the most recent operation that changed this file, if available.",
                        null=True,
                        on_delete=django.db.models.deletion.DB_SET_NULL,
                        to="memory.receipt",
                        verbose_name="last operation",
                    ),
                ),
            ],
            options={
                "verbose_name": "stored memory file",
                "verbose_name_plural": "stored memory files",
                "db_table_comment": "Persisted files in the Django-backed memory store.",
                "ordering": ["path"],
            },
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.UniqueConstraint(fields=("directory", "operation_id"), name="memory_receipt_unq"),
        ),
        migrations.AddConstraint(
            model_name="storedmemoryfile",
            constraint=models.UniqueConstraint(fields=("directory", "path"), name="memory_storedmemoryfile_unq"),
        ),
    ]
