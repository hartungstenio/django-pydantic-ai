"""Django application configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ConversationsConfig(AppConfig):
    """Application configuration for conversations."""

    name = "django_pydantic_ai.conversations"
    verbose_name = _("Conversations")
    default_auto_field = "django.db.models.BigAutoField"
