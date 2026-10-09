from django.apps import apps


def test_app_config_is_registered() -> None:
    config = apps.get_app_config("django_pydantic_ai")

    assert config.name == "django_pydantic_ai"
