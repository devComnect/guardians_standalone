from django.apps import AppConfig

class MissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.missions' # Deve ser exatamente o caminho da pasta

    def ready(self):
        import apps.missions.signals
