from django.apps import AppConfig
import logging
logger = logging.getLogger(__name__)

class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.profiles'
    def ready(self):
        import apps.profiles.signals  # noqa
        from apps.profiles.signals import (
            _register_store_signals,
            _register_mission_signals,
            _register_battle_pass_signals,
        )
        _register_store_signals()
        _register_mission_signals()
        try:
            _register_battle_pass_signals()
        except Exception as e:
            logger.exception(f'[BATTLE PASS SIGNAL] Falha ao registrar: {e}')
            print(f'[BATTLE PASS SIGNAL ERROR] {e}')