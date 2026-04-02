import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.profiles.models import Player 

class Command(BaseCommand):
    help = 'Popula o banco de dados com 10 jogadores genéricos'

    def handle(self, *args, **kwargs):
        classes = ['none', 'guardian', 'analyst', 'sentinel', 'hacker']
        criados = 0
        atualizados = 0

        for i in range(1, 11):
            username = f'jogador_{i}'
            email = f'{username}@exemplo.com'
            
            user, created_user = User.objects.get_or_create(
                username=username,
                defaults={'email': email}
            )

            if created_user:
                user.set_password('senha_padrao_123')
                user.save()

            level = random.randint(1, 15)
            xp_total = Player.xp_para_nivel(level) + random.randint(0, 500)

            player, created_player = Player.objects.update_or_create(
                user=user,
                defaults={
                    'display_name': f'Player Genérico {i}',
                    'classe': random.choice(classes),
                    'bio': f'Conta de testes gerada automaticamente ({username}).',
                    'xp_total': xp_total,
                    'level': level,
                    'coins': random.randint(50, 2000),
                    'streak_days': random.randint(0, 15),
                    'ofensiva': random.randint(0, 50),
                }
            )

            if created_player:
                criados += 1
            else:
                atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Seed de jogadores finalizado: {criados} novos, {atualizados} atualizados.'
        ))