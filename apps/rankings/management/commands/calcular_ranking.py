from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from apps.rankings.models import Season, RankingSnapshot
from django.utils import timezone as tz


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
                else:  # ofensiva
                    valor = p.ofensiva

                snap = RankingSnapshot.objects.filter(season=season, player=player, categoria=categoria).first()
                valor_desde = snap.valor_desde if snap else tz.now()
                dados.append((player, valor, valor_desde))

            # Ordena por valor desc e atribui posições
            dados.sort(key=lambda x: (-x[1], x[2]))

            for posicao, (player, valor, valor_desde) in enumerate(dados, start=1):
                RankingSnapshot.objects.update_or_create(
                    season=season, player=player, categoria=categoria,
                    defaults={'posicao': posicao, 'valor': valor}
                )

        self.stdout.write(self.style.SUCCESS(f'Ranking recalculado — Season {season.numero}'))