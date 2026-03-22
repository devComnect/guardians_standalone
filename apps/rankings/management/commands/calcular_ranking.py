from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from apps.rankings.models import Season, RankingSnapshot
from apps.minigames.models import QuizAttempt, DecriptarAttempt, CodigoAttempt


class Command(BaseCommand):
    help = 'Recalcula e salva snapshots de ranking da temporada ativa'

    def handle(self, *args, **kwargs):
        season = Season.objects.filter(ativa=True).first()
        if not season:
            self.stdout.write(self.style.WARNING('Nenhuma temporada ativa.'))
            return

        players = User.objects.filter(is_active=True, player__isnull=False)

        for categoria in ['xp', 'moedas', 'ofensiva']:
            dados = []

            for player in players:
                p = getattr(player, 'player', None)
                if not p:
                    continue

                if categoria == 'xp':
                    valor = p.xp_total
                elif categoria == 'moedas':
                    valor = p.coins
                else:  # ofensiva — total de desafios concluídos
                    quiz   = QuizAttempt.objects.filter(player=player, completed_at__isnull=False).count()
                    dcr    = DecriptarAttempt.objects.filter(player=player, completed_at__isnull=False).count()
                    cod    = CodigoAttempt.objects.filter(player=player, completed_at__isnull=False).count()
                    valor  = quiz + dcr + cod

                dados.append((player, valor))

            # Ordena por valor desc e atribui posições
            dados.sort(key=lambda x: x[1], reverse=True)

            for posicao, (player, valor) in enumerate(dados, start=1):
                RankingSnapshot.objects.update_or_create(
                    season=season, player=player, categoria=categoria,
                    defaults={'posicao': posicao, 'valor': valor}
                )

        self.stdout.write(self.style.SUCCESS(f'Ranking recalculado — Season {season.numero}'))