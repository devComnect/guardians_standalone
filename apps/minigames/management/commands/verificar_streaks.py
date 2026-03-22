from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Verifica e zera streaks de players inativos (rodar diariamente)'

    def handle(self, *args, **kwargs):
        from apps.profiles.services import verificar_streak_decay

        players = User.objects.filter(is_active=True, player__isnull=False)
        zeradas = 0

        for user in players:
            if verificar_streak_decay(user):
                zeradas += 1
                self.stdout.write(f'  Streak zerada: {user.username}')

        self.stdout.write(self.style.SUCCESS(
            f'✅ Verificação concluída: {zeradas} streak(s) zerada(s) de {players.count()} player(s).'
        ))