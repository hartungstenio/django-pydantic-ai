# django-pydantic-ai

[![PyPI - Version](https://img.shields.io/pypi/v/django-pydantic-ai.svg)](https://pypi.org/project/django-pydantic-ai)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-pydantic-ai.svg)](https://pypi.org/project/django-pydantic-ai)

Integrations between Django and [Pydantic AI](https://ai.pydantic.dev/), including Django-backed memory storage.

## Requirements

- Python 3.10+
- Django 5.2+
- Pydantic AI

## Table of Contents

- [Installation](#installation)
- [Requirements](#requirements)
- [License](#license)

## Installation

```console
pip install django-pydantic-ai
```

## License
Add `django_pydantic_ai` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
	...,
	"django_pydantic_ai",
]
```

The library is being scaffolded; integration APIs and database models will be documented as they are added.

## License

`django-pydantic-ai` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
