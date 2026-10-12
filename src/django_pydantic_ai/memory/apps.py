"""Django application configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MemoryConfig(AppConfig):
    """Application configuration for memory."""

    name = "django_pydantic_ai.memory"
    verbose_name = _("Memory")
    default_auto_field = "django.db.models.BigAutoField"
