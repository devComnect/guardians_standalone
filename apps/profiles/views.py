from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import PlayerNotification, ClasseConfig, PlayerAchievement, XPEvent, Perk, ClasseConfig
from .services import trocar_classe
import json


@login_required
@require_POST
def marcar_notificacoes_lidas(request):
    request.user.notifications.filter(lida=False).update(lida=True)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def trocar_classe_view(request):
    try:
        body = json.loads(request.body)
        nova_classe = body.get('classe')
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Payload inválido.'}, status=400)

    sucesso, mensagem = trocar_classe(request.user, nova_classe)
    return JsonResponse({'ok': sucesso, 'mensagem': mensagem})


@login_required
def index(request):
    player = request.user.player
    
    conquistas_destaque = PlayerAchievement.objects.filter(
        player=request.user, 
        em_destaque=True
    ).select_related('achievement')
    
    historico_logs = XPEvent.objects.filter(player=request.user).order_by('-criado_em')[:15]
    
    perks_desbloqueados = Perk.objects.filter(
        classe=player.classe, 
        level_required__lte=player.level, 
        ativo=True
    )
    
    config_classe = ClasseConfig.get()

    context = {
        'player': player,
        'conquistas_destaque': conquistas_destaque,
        'historico_logs': historico_logs,
        'perks_desbloqueados': perks_desbloqueados,
        'config_classe': config_classe,
        'xp_percentual': player.xp_percentual,
    }
    
    return render(request, 'profiles/index.html', context)