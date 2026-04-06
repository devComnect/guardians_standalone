from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import AdminPost
from apps.store.models import PlayerItem
from apps.minigames.models import PatrolAttempt
from apps.profiles.services import get_ofensiva_bonus_pct
from apps.missions.services import MissionService
from datetime import timedelta




@login_required
def home(request):
    posts  = AdminPost.objects.filter(publicado=True)[:10]
    player = getattr(request.user, 'player', None)

    patrol_attempt = PatrolAttempt.objects.filter(
        player=request.user,
        date=timezone.localdate(),
        completed=True
    ).first()

    # Busca ou cria o set de missões do usuário
    mission_data = MissionService.get_or_create_set(request.user)
    # Pegamos as missões vinculadas a esse set
    active_missions = mission_data.missions.all() if mission_data else []

    week_start = timezone.localdate() - timedelta(days=6)
    patrulhas_na_semana = PatrolAttempt.objects.filter(
        player=request.user,
        date__range=(week_start, timezone.localdate()),
        completed=True,
    ).count()

    patrol_done_hoje   = patrol_attempt is not None
    patrol_limite      = patrulhas_na_semana >= 5
    patrol_done        = patrol_done_hoje or patrol_limite
    patrol_won         = patrol_attempt.won if patrol_attempt else False
    patrol_semanal_info = {'realizadas': patrulhas_na_semana, 'limite': 5}

    # Posição no ranking da temporada ativa
    ranking_pos = None
    try:
        from apps.rankings.models import Season, RankingSnapshot
        season = Season.objects.filter(ativa=True).first()
        if season and player:
            snap = RankingSnapshot.objects.filter(
                season=season,
                player=request.user,
                categoria='xp'
            ).first()
            ranking_pos = snap.posicao if snap else None
    except Exception:
        pass

    frame_ativo = None
    bg_ativo = None
    titulo_ativo = None
    if player:
        # Busca os itens que estão com 'equipado=True'
        frame_ativo = PlayerItem.objects.filter(player=request.user, equipado=True, item__effect='COSMETIC_FRAME').first()
        bg_ativo = PlayerItem.objects.filter(player=request.user, equipado=True, item__effect='COSMETIC_BACKGROUND').first()
        titulo_ativo = PlayerItem.objects.filter(player=request.user, equipado=True, item__effect='COSMETIC_TITLE').first()

    context = {
        'posts': posts,
        'player': player,
        'patrol_done': patrol_done,
        'patrol_won': patrol_won,
        'ranking_pos': ranking_pos,
        'ofensiva_bonus': get_ofensiva_bonus_pct(request.user) if player else 0,
        'mission_set': mission_data,
        'active_missions': active_missions,
        'frame_ativo': frame_ativo,
        'bg_ativo': bg_ativo,
        'titulo_ativo': titulo_ativo,
        'patrol_semanal_info': patrol_semanal_info,
        'patrol_limite': patrol_limite,
        'patrol_semanal_info': patrol_semanal_info,
    }

    return render(request, 'core/home.html', context)