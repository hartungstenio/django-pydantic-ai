# django-pydantic-ai

[![PyPI - Version](https://img.shields.io/pypi/v/django-pydantic-ai.svg)](https://pypi.org/project/django-pydantic-ai)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-pydantic-ai.svg)](https://pypi.org/project/django-pydantic-ai)

Use Django as a persistent backend for [Pydantic AI](https://ai.pydantic.dev/) agent memory. The package provides an asynchronous memory store for [Pydantic AI Harness](https://github.com/pydantic/pydantic-ai-harness), backed by Django models and your configured database.

## Requirements

- Python 3.12 or newer
- Django 6.1 or newer

## Table of Contents

- [Installation](#installation)
- [Django Setup](#django-setup)
- [Use With An Agent](#use-with-an-agent)
- [Store Behavior](#store-behavior)
- [Development](#development)
- [License](#license)

## Installation

```console
pip install django-pydantic-ai
```

The package depends on Pydantic AI and Pydantic AI Harness; pip installs them along with Django.

## Django Setup

Add the memory app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # Your other Django apps...
    "django_pydantic_ai.memory",
]
```

Configure a database as usual, then create the memory tables:

```console
python manage.py migrate
```

## Use With An Agent

Create a `Directory` for each isolation boundary you need, such as a user, tenant, or agent. A `DjangoModelStore` is bound to one directory. The following async factory creates or retrieves that directory and attaches its store to the Harness `Memory` capability:

```python
from pydantic_ai import Agent
from pydantic_ai_harness.memory import Memory

from django_pydantic_ai.memory.models import Directory
from django_pydantic_ai.memory.store import DjangoModelStore


async def create_agent(model: str, user_id: int) -> Agent:
    directory, _ = await Directory.objects.aget_or_create(name=f"user:{user_id}")
    store = DjangoModelStore(directory)
    return Agent(model, capabilities=[Memory(store=store)])
```

Use the resulting agent through Pydantic AI's async API:

```python
agent = await create_agent("your-model", user_id=42)
result = await agent.run("Remember that my preferred language is Portuguese.")
```

The `Memory` capability injects the main memory notebook into agent context and provides tools for writing, reading, deleting, and searching memory files. Its default in-memory store is process-local; pass `DjangoModelStore` to persist data in Django's database across runs.

## Store Behavior

- Files and operation receipts are scoped to the `Directory` passed to `DjangoModelStore`.
- Writes use a SHA-256 hex digest of the file content as the string version. Identical content has the same version.
- `expected_version=None` requires that a file does not already exist. Supplying a version requires the stored file to still have that version; otherwise the store raises `MemoryConflictError`.
- Delete mutations return `None` as their version because deleted content has no hash.
- Supplying a `MemoryOperation` to a write or delete records a receipt so a repeated operation can return its prior result. Reusing an operation ID with different arguments raises `MemoryOperationConflictError`.
- Store methods are asynchronous. Reads, writes, deletes, path listing, and lexical search operate on the directory bound to the store.

## Development

Run the test suite with Hatch:

```console
hatch run pytest
```

## License

`django-pydantic-ai` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
