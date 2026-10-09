"""Settings for the project's test Django application."""

from django.core.management.utils import get_random_secret_key

SECRET_KEY = get_random_secret_key()
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django_pydantic_ai.apps.DjangoPydanticAIConfig",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
