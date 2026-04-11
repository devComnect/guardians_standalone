from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Season, RankingSnapshot
from apps.store.models import PlayerItem


def _get_cosmetics_map(user_list):
    """Retorna {user_id: {'titulo': PlayerItem, 'frame': PlayerItem, 'bg': PlayerItem}}"""
    result = {}
    
    # Adicionamos o COSMETIC_BACKGROUND mapeado para a chave 'bg' (que é a que vc usa no HTML)
    efeitos_mapeados = [
        ('COSMETIC_TITLE', 'titulo'), 
        ('COSMETIC_FRAME', 'frame'),
        ('COSMETIC_BACKGROUND', 'bg') 
    ]
    
    for effect, key in efeitos_mapeados:
        items = PlayerItem.objects.filter(
            player__in=user_list,
            equipado=True,
            item__effect=effect,
        ).select_related('item', 'player')
        
        for pi in items:
            if pi.player_id not in result:
                result[pi.player_id] = {}
            result[pi.player_id][key] = pi
            
    return result


@login_required
def index(request):
    season = Season.objects.filter(ativa=True).first()
    categoria = request.GET.get('tab', 'xp')

    if categoria not in ['xp', 'moedas', 'ofensiva']:
        categoria = 'xp'

    minha_posicao = None
    total = 0
    podio = []
    tabela = []
    cosmetics_map = {}

    if season:
        qs = RankingSnapshot.objects.filter(
            season=season,
            categoria=categoria,
        ).select_related('player', 'player__player').order_by('posicao')

        minha_posicao = qs.filter(player=request.user).first()
        total = qs.count()
        podio  = list(qs[:3])
        tabela = list(qs[3:])

        all_players = [s.player for s in podio + tabela]
        cosmetics_map = _get_cosmetics_map(all_players)

    return render(request, 'rankings/index.html', {
        'season':        season,
        'categoria':     categoria,
        'podio':         podio,
        'tabela':        tabela,
        'minha_posicao': minha_posicao,
        'total_players': total,
        'cosmetics_map': cosmetics_map,
    })

def temporadas_anteriores(request):
    s1_tabela = [
        {'pos': 4,  'nome': 'Lucas Kaizer',              'valor': '949 pts'},
        {'pos': 5,  'nome': 'Danilo Neto',     'valor': '825 pts'},
        {'pos': 6,  'nome': 'Raysa Melo',           'valor': '822 pts'},
        {'pos': 7,  'nome': 'Matheus Melo',            'valor': '805 pts'},
        {'pos': 8,  'nome': 'Fábio Silva',          'valor': '570 pts'},
        {'pos': 9,  'nome': 'Renato Ragga',         'valor': '387 pts'},
        {'pos': 10, 'nome': 'Luciano Olegario',            'valor': '363 pts'},
        {'pos': 11, 'nome': 'Rafael Silva',   'valor': '212 pts'},
        {'pos': 12, 'nome': 'Henrique Almeida',     'valor': '187 pts'},
        {'pos': 13, 'nome': 'Gustavo Maciel',       'valor': '148 pts'},
    ]

    s2_tabela = [
        {'pos': 4,  'nome': 'Fabio Silva',                  'valor': '5255 XP'},
        {'pos': 5,  'nome': 'Chrysthyanne Rodrigues',          'valor': '5185 XP'},
        {'pos': 6,  'nome': 'Eduardo Pinheiro',        'valor': '3489 XP'},
        {'pos': 7,  'nome': 'Matheus Melo',                  'valor': '3376 XP'},
        {'pos': 8,  'nome': 'Rafael Silva',   'valor': '3174 XP'},
        {'pos': 9,  'nome': 'Renato Ragga',              'valor': '3027 XP'},
        {'pos': 10, 'nome': 'Danilo Neto', 'valor': '2128 XP'},
        {'pos': 11, 'nome': 'Marcos Pedroso',           'valor': '244 XP'},
    ]

    return render(request, 'rankings/temporadas_anteriores.html', {
        's1_tabela': s1_tabela,
        's2_tabela': s2_tabela,
    })

