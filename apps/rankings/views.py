from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Season, RankingSnapshot


@login_required
def index(request):
    season   = Season.objects.filter(ativa=True).first()
    categoria = request.GET.get('tab', 'xp')

    if categoria not in ['xp', 'moedas', 'ofensiva']:
        categoria = 'xp'

    qs = []
    minha_posicao = None

    if season:
            qs = (
        RankingSnapshot.objects
        .filter(season=season, categoria=categoria)
        .select_related('player', 'player__player')
        .order_by('posicao')
    )

    minha_posicao = qs.filter(player=request.user).first()
    total         = qs.count()
    podio         = list(qs[:3])
    tabela        = list(qs[3:])

    return render(request, 'rankings/index.html', {
        'season':        season,
        'categoria':     categoria,
        'podio':         podio,
        'tabela':        tabela,
        'minha_posicao': minha_posicao,
        'total_players': total,
    })