from django.apps import AppConfig
class MinigamesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.minigames'

    def ready(self):
        import apps.minigames.signals  # noqa
