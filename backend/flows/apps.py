from django.apps import AppConfig


class FlowsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "flows"

    def ready(self) -> None:
        import flows.definitions  # noqa: F401  (registers flows)
