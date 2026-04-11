from django.db import transaction


def recalcular_ranking_player(user):
    from apps.rankings.models import Season, RankingSnapshot

    season = Season.objects.filter(ativa=True).first()
    if not season:
        return

    player = getattr(user, 'player', None)
    if not player:
        return

    valores = {
        'xp':       player.xp_total,
        'moedas':   player.coins,
        'ofensiva': player.ofensiva,
    }

    for categoria, valor in valores.items():
        snap = RankingSnapshot.objects.filter(season=season, player=user, categoria=categoria).first()
        posicao_atual = snap.posicao if snap else 9999

        RankingSnapshot.objects.update_or_create(
            season=season,
            player=user,
            categoria=categoria,
            defaults={'valor': valor, 'posicao': posicao_atual, 'posicao_anterior': posicao_atual},
        )

    _reordenar_posicoes(season)


def _reordenar_posicoes(season):
    from apps.rankings.models import RankingSnapshot

    for categoria in ['xp', 'moedas', 'ofensiva']:
        snapshots = list(
            RankingSnapshot.objects.filter(season=season, categoria=categoria)
            .order_by('-valor')
            .values_list('pk', flat=True)
        )
        with transaction.atomic():
            for posicao, pk in enumerate(snapshots, start=1):
                RankingSnapshot.objects.filter(pk=pk).update(posicao=posicao)