from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import AdminPost
from apps.minigames.models import PatrolAttempt
from apps.profiles.services import get_ofensiva_bonus_pct
from apps.missions.services import MissionService # Importe o serviço



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

    patrol_done = patrol_attempt is not None
    patrol_won  = patrol_attempt.won if patrol_attempt else False

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

    return render(request, 'core/home.html', {
        'posts':       posts,
        'player':      player,
        'patrol_done': patrol_done,
        'patrol_won':  patrol_won,
        'ranking_pos': ranking_pos,
        'ofensiva_bonus':  get_ofensiva_bonus_pct(request.user) if player else 0,
        'mission_set': mission_data,
        'active_missions': active_missions,
    })