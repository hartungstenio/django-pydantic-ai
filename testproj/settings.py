"""Settings for the project's test Django application."""

from django.core.management.utils import get_random_secret_key

SECRET_KEY = get_random_secret_key()
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django_pydantic_ai.conversations",
    "django_pydantic_ai.memory",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
USE_TZ = True
