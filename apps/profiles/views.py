from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum, Count, Avg
import json

from .models import (
    Player, Perk, XPEvent, PlayerNotification,
    PlayerAchievement, Achievement, ClasseConfig, OfensivaConfig,
)
from .services import trocar_classe, verificar_conquistas


# ─────────────────────────────────────────────
# PERFIL PRINCIPAL
# ─────────────────────────────────────────────

@login_required
def index(request):
    user   = request.user
    player = getattr(user, 'player', None)

    if not player:
        messages.error(request, 'Perfil não encontrado.')
        return redirect('core:home')

    context = {
        **_ctx_identidade(user, player),
        **_ctx_stats(user, player),
        **_ctx_bonus(user, player),
        **_ctx_skills(user, player),
        **_ctx_atividade_semanal(user),
        **_ctx_inventario(user),
        **_ctx_conquistas(user),
        **_ctx_missoes(user),
        **_ctx_log(user),
        'classe_config': ClasseConfig.get(),
    }
    return render(request, 'profiles/index.html', context)


# ─── Blocos de contexto ───────────────────────

def _ctx_identidade(user, player):
    """Avatar, classe, frame, título, background."""
    from apps.store.models import PlayerItem

    # Substituído 'item__efeito_tipo' por 'item__effect'
    frame_ativo = PlayerItem.objects.filter(
        player=user, equipado=True, item__effect='COSMETIC_FRAME' 
    ).select_related('item').first()

    bg_ativo = PlayerItem.objects.filter(
        player=user, equipado=True, item__effect='COSMETIC_BACKGROUND'
    ).select_related('item').first()

    titulo_ativo = PlayerItem.objects.filter(
        player=user, equipado=True, item__effect='COSMETIC_TITLE'
    ).select_related('item').first()

    return {
        'player':       player,
        'frame_ativo':  frame_ativo,
        'bg_ativo':     bg_ativo,
        'titulo_ativo': titulo_ativo,
    }


def _ctx_stats(user, player):
    """Estatísticas completas do perfil."""
    from apps.minigames.models import (
        QuizAttempt, DecriptarAttempt, CodigoAttempt,
        PatrolAttempt, PasswordAttempt,
    )
    from apps.rankings.models import RankingSnapshot, Season

    # Quiz
    quiz_total     = QuizAttempt.objects.filter(player=user, completed_at__isnull=False)
    quiz_count     = quiz_total.count()
    quiz_perfeitos = sum(
        1 for a in quiz_total
        if a.xp_earned >= (a.quiz.questions.aggregate(t=Sum('xp_points'))['t'] or 0) > 0
    )
    quiz_xp_total  = quiz_total.aggregate(t=Sum('xp_earned'))['t'] or 0

    # Decriptar
    dcr_total = DecriptarAttempt.objects.filter(player=user, completed_at__isnull=False)
    dcr_count = dcr_total.count()
    dcr_perfeitos = dcr_total.filter(
        correct_count__gte=1
    ).annotate(
        total=Count('id')
    ).filter(correct_count=dcr_total.values('words_sequence').first().__len__()
             if dcr_total.exists() else 0
    ).count() if dcr_total.exists() else 0

    # Código
    cod_total    = CodigoAttempt.objects.filter(player=user, completed_at__isnull=False)
    cod_count    = cod_total.count()
    cod_vitorias = cod_total.filter(won=True).count()

    # Patrulha
    try:
        patrol_total    = PatrolAttempt.objects.filter(player=user, completed=True)
        patrol_count    = patrol_total.count()
        patrol_vitorias = patrol_total.filter(won=True).count()
    except Exception:
        patrol_count = patrol_vitorias = 0

    # Cofre
    try:
        pw_total    = PasswordAttempt.objects.filter(player=user, completed_at__isnull=False)
        pw_count    = pw_total.count()
        pw_vitorias = pw_total.filter(is_won=True).count()
    except Exception:
        pw_count = pw_vitorias = 0

    # Ranking
    season = Season.objects.filter(ativa=True).first()
    ranking_xp     = None
    ranking_moedas = None
    ranking_ofensiva = None
    if season:
        snap_xp = RankingSnapshot.objects.filter(
            season=season, player=user, categoria='xp').first()
        snap_moedas = RankingSnapshot.objects.filter(
            season=season, player=user, categoria='moedas').first()
        snap_of = RankingSnapshot.objects.filter(
            season=season, player=user, categoria='ofensiva').first()
        ranking_xp      = snap_xp.posicao if snap_xp else None
        ranking_moedas  = snap_moedas.posicao if snap_moedas else None
        ranking_ofensiva = snap_of.posicao if snap_of else None

    desafios_total = quiz_count + dcr_count + cod_count + patrol_count + pw_count

    return {
        'stats': {
            'desafios_total':   desafios_total,
            'quiz_count':       quiz_count,
            'quiz_perfeitos':   quiz_perfeitos,
            'quiz_xp_total':    quiz_xp_total,
            'dcr_count':        dcr_count,
            'cod_count':        cod_count,
            'cod_vitorias':     cod_vitorias,
            'patrol_count':     patrol_count,
            'patrol_vitorias':  patrol_vitorias,
            'pw_count':         pw_count,
            'pw_vitorias':      pw_vitorias,
            'ranking_xp':       ranking_xp,
            'ranking_moedas':   ranking_moedas,
            'ranking_ofensiva': ranking_ofensiva,
            'season':           season,
        }
    }


def _ctx_bonus(user, player):
    """Painel de bônus — breakdown completo de onde vem cada bônus."""
    from apps.profiles.services import (
        get_perk_valor, get_ofensiva_bonus_pct, get_achievement_bonus,
    )
    # IMPORTAÇÃO CORRIGIDA AQUI
    from apps.store.services import get_passive_bonus_xp_pct
    from apps.store.models import PlayerItem

    # Perks ativos
    perks_ativos = Perk.objects.filter(
        classe=player.classe,
        level_required__lte=player.level,
        ativo=True
    ).order_by('level_required')

    # Conquistas em destaque com bônus
    conquistas_com_bonus = PlayerAchievement.objects.filter(
        player=user, em_destaque=True,
        achievement__bonus_type__isnull=False,
        achievement__bonus_value__gt=0,
    ).select_related('achievement')

    # Itens nos slots
    itens_slot = PlayerItem.objects.filter(
        player=user, slot_index__isnull=False
    ).select_related('item').order_by('slot_index')

    # Totais calculados
    bonus_xp_global   = get_perk_valor(user, 'xp_global')
    bonus_ofensiva    = get_ofensiva_bonus_pct(user)
    bonus_conquistas  = get_achievement_bonus(user, 'global_xp_pct')
    
    # CHAMADA DA FUNÇÃO CORRIGIDA AQUI
    bonus_itens = get_passive_bonus_xp_pct(user, fonte='quiz')

    ofensiva_config = OfensivaConfig.get()
    teto_ofensiva   = ofensiva_config.teto_bonus_ofensiva

    return {
        'bonus': {
            'perks_ativos':       perks_ativos,
            'conquistas_bonus':   conquistas_com_bonus,
            'itens_slot':         itens_slot,
            'bonus_xp_global':    bonus_xp_global,
            'bonus_ofensiva':     bonus_ofensiva,
            'bonus_conquistas':   bonus_conquistas,
            'bonus_itens':        bonus_itens,
            'total_bonus_pct':    bonus_xp_global + bonus_ofensiva + bonus_conquistas + bonus_itens,
            'ofensiva_atual':     player.ofensiva,
            'ofensiva_teto':      teto_ofensiva,
        }
    }

def _ctx_skills(user, player):
    """
    Matriz de skills — mostra onde o player é mais forte.
    Calcula taxa de sucesso e XP médio por tipo de desafio.
    """
    from apps.minigames.models import (
        QuizAttempt, DecriptarAttempt, CodigoAttempt,
        PatrolAttempt, PasswordAttempt,
    )

    def _taxa(total, sucesso):
        return round((sucesso / total * 100) if total > 0 else 0, 1)

    quiz_tot  = QuizAttempt.objects.filter(player=user, completed_at__isnull=False)
    dcr_tot   = DecriptarAttempt.objects.filter(player=user, completed_at__isnull=False)
    cod_tot   = CodigoAttempt.objects.filter(player=user, completed_at__isnull=False)

    try:
        pat_tot = PatrolAttempt.objects.filter(player=user, completed=True)
        pat_win = pat_tot.filter(won=True).count()
    except Exception:
        pat_tot = []
        pat_win = 0

    try:
        pw_tot = PasswordAttempt.objects.filter(player=user, completed_at__isnull=False)
        pw_win = pw_tot.filter(is_won=True).count()
    except Exception:
        pw_tot = []
        pw_win = 0

    quiz_xp_medio = quiz_tot.aggregate(m=Avg('xp_earned'))['m'] or 0
    dcr_xp_medio  = dcr_tot.aggregate(m=Avg('xp_earned'))['m'] or 0
    cod_xp_medio  = cod_tot.aggregate(m=Avg('xp_earned'))['m'] or 0

    skills = [
        {
            'nome':      'Quiz',
            'icone':     'bi-patch-question-fill',
            'cor':       '#0dcaf0',
            'total':     quiz_tot.count(),
            'taxa':      _taxa(quiz_tot.count(),
                               quiz_tot.filter(xp_earned__gt=0).count()),
            'xp_medio':  round(quiz_xp_medio, 0),
        },
        {
            'nome':      'Decriptar',
            'icone':     'bi-shuffle',
            'cor':       '#bd00ff',
            'total':     dcr_tot.count(),
            'taxa':      _taxa(dcr_tot.count(),
                               dcr_tot.filter(correct_count__gt=0).count()),
            'xp_medio':  round(dcr_xp_medio, 0),
        },
        {
            'nome':      'Código',
            'icone':     'bi-terminal-fill',
            'cor':       '#ff2a6d',
            'total':     cod_tot.count(),
            'taxa':      _taxa(cod_tot.count(),
                               cod_tot.filter(won=True).count()),
            'xp_medio':  round(cod_xp_medio, 0),
        },
        {
            'nome':      'Patrulha',
            'icone':     'bi-shield-fill',
            'cor':       '#05d9e8',
            'total':     len(pat_tot) if isinstance(pat_tot, list) else pat_tot.count(),
            'taxa':      _taxa(
                             len(pat_tot) if isinstance(pat_tot, list) else pat_tot.count(),
                             pat_win),
            'xp_medio':  0,
        },
        {
            'nome':      'Cofre',
            'icone':     'bi-key-fill',
            'cor':       '#fcee0a',
            'total':     len(pw_tot) if isinstance(pw_tot, list) else pw_tot.count(),
            'taxa':      _taxa(
                             len(pw_tot) if isinstance(pw_tot, list) else pw_tot.count(),
                             pw_win),
            'xp_medio':  0,
        },
    ]

    # Ordena por taxa de sucesso para mostrar o mais forte primeiro
    skills_sorted = sorted(skills, key=lambda x: x['taxa'], reverse=True)

    return {'skills': skills_sorted}


def _ctx_atividade_semanal(user):
    """
    Card de atividade semanal estilo Duolingo/GitHub.
    Retorna os últimos 7 dias com flag de ativo/inativo.
    """
    from apps.minigames.models import (
        QuizAttempt, DecriptarAttempt, CodigoAttempt,
        PatrolAttempt, PasswordAttempt,
    )
    from datetime import timedelta

    hoje  = timezone.localdate()
    dias  = []

    for i in range(6, -1, -1):   # últimos 7 dias, mais antigo primeiro
        dia = hoje - timedelta(days=i)

        quiz_dia = QuizAttempt.objects.filter(
            player=user, completed_at__date=dia, completed_at__isnull=False
        ).count()
        dcr_dia = DecriptarAttempt.objects.filter(
            player=user, date=dia, completed_at__isnull=False
        ).count()
        cod_dia = CodigoAttempt.objects.filter(
            player=user, date=dia, completed_at__isnull=False
        ).count()

        total_dia = quiz_dia + dcr_dia + cod_dia
        dias.append({
            'data':     dia,
            'dia_nome': dia.strftime('%a'),   # Seg, Ter, Qua...
            'total':    total_dia,
            'ativo':    total_dia > 0,
            'hoje':     dia == hoje,
        })

    # Sequência atual de dias ativos
    streak_visual = 0
    for d in reversed(dias):
        if d['ativo']:
            streak_visual += 1
        else:
            break

    return {
        'atividade_semanal': dias,
        'streak_visual':     streak_visual,
    }


def _ctx_inventario(user):
    from apps.store.models import PlayerItem, StoreConfig
    
    config = StoreConfig.get()
    
    inventario = PlayerItem.objects.filter(
        player=user
    ).select_related('item').order_by('item__tipo', '-adquirido_em')

    consumiveis = [pi for pi in inventario if pi.item.tipo == 'consumable']
    passivos    = [pi for pi in inventario if pi.item.tipo == 'passive']
    cosmeticos  = [pi for pi in inventario if pi.item.tipo == 'cosmetic']

    slots_max = config.max_passivos_slots
    
    slots_grade = []
    slot_ocupado = {pi.slot_index: pi for pi in passivos if pi.slot_index is not None}
    
    for s in range(1, slots_max + 1):
        slots_grade.append({
            'numero': s,
            'player_item': slot_ocupado.get(s),
        })

    return {
        'inventario_consumiveis': consumiveis,
        'inventario_passivos':    passivos,
        'inventario_cosmeticos':  cosmeticos,
        'slots_grade':            slots_grade,
        'slots_max':              slots_max,
    }


def _ctx_conquistas(user):
    """Galeria de conquistas — separadas em desbloqueadas e bloqueadas."""
    from .models import AchievementConfig

    config   = AchievementConfig.get()
    todas    = Achievement.objects.filter(ativo=True).order_by('raridade', 'trigger_value')

    desbloqueadas = PlayerAchievement.objects.filter(
        player=user
    ).select_related('achievement').order_by('-desbloqueada_em')

    ids_desbloqueados = set(pa.achievement_id for pa in desbloqueadas)
    em_destaque_count = desbloqueadas.filter(em_destaque=True).count()

    bloqueadas = [a for a in todas if a.id not in ids_desbloqueados]

    return {
        'conquistas_desbloqueadas': desbloqueadas,
        'conquistas_bloqueadas':    bloqueadas,
        'conquistas_em_destaque':   desbloqueadas.filter(em_destaque=True),
        'max_destaques':            config.max_destaques,
        'em_destaque_count':        em_destaque_count,
    }


def _ctx_missoes(user):
    """Missões ativas do player."""
    try:
        from apps.challenges.models import PlayerMission
        missoes_ativas = PlayerMission.objects.filter(
            player=user, concluida=False
        ).select_related('mission').order_by('mission__tipo', 'mission__ordem')

        missoes_concluidas_hoje = PlayerMission.objects.filter(
            player=user, concluida=True,
            concluida_em__date=timezone.localdate()
        ).count()
    except Exception:
        missoes_ativas = []
        missoes_concluidas_hoje = 0

    return {
        'missoes_ativas':          missoes_ativas,
        'missoes_concluidas_hoje': missoes_concluidas_hoje,
    }


def _ctx_log(user):
    from apps.store.models import StoreTransaction, ActiveEffect
    from apps.profiles.models import XPEvent
    from django.utils import timezone

    xp_events = XPEvent.objects.filter(player=user).order_by('-criado_em')[:50]
    coin_log  = StoreTransaction.objects.filter(player=user).order_by('-criado_em')[:30]
    notifs    = user.notifications.order_by('-criado_em')[:30]

    agora = timezone.now()
    retake_count = ActiveEffect.objects.filter(
        player=user, effect='TOKEN_RETAKE', expires_at__gt=agora
    ).count()

    class DummyToken: pass
    retake_token = DummyToken()
    retake_token.usos_restantes = retake_count

    return {
        'xp_events':    xp_events,
        'coin_log':     coin_log,
        'notif_log':    notifs,
        'retake_token': retake_token if retake_count > 0 else None,
    }


# ─────────────────────────────────────────────
# EDITAR PERFIL
# ─────────────────────────────────────────────

@login_required
def editar_perfil(request):
    player = getattr(request.user, 'player', None)
    if not player:
        return redirect('core:home')

    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        bio          = request.POST.get('bio', '').strip()
        avatar       = request.FILES.get('avatar')

        if display_name:
            player.display_name = display_name[:60]
        if bio:
            player.bio = bio[:300]
        if avatar:
            TIPOS_PERMITIDOS = ['image/png', 'image/jpeg', 'image/webp']
            if avatar.content_type not in TIPOS_PERMITIDOS:
                messages.error(request, 'Formato inválido. Use PNG, JPG ou WEBP.')
                return redirect('profiles:editar')
            if avatar.size > 2 * 1024 * 1024:
                messages.error(request, 'Imagem muito grande. Máx 2MB.')
                return redirect('profiles:editar')
            player.avatar = avatar

        player.save()
        messages.success(request, 'Perfil atualizado.')
        return redirect('profiles:index')

    return render(request, 'profiles/editar.html', {'player': player})


# ─────────────────────────────────────────────
# AJAX — CONQUISTAS (destaque)
# ─────────────────────────────────────────────

@login_required
@require_POST
def toggle_conquista_destaque(request):
    try:
        body   = json.loads(request.body)
        pa_id  = int(body.get('player_achievement_id'))
        ativar = body.get('ativar', True)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    pa = PlayerAchievement.objects.filter(pk=pa_id, player=request.user).first()
    if not pa:
        return JsonResponse({'error': 'Conquista não encontrada.'}, status=404)

    from .models import AchievementConfig
    config = AchievementConfig.get()

    if ativar:
        em_destaque_atual = PlayerAchievement.objects.filter(
            player=request.user, em_destaque=True
        ).count()
        if em_destaque_atual >= config.max_destaques:
            return JsonResponse({
                'error': f'Limite de {config.max_destaques} conquistas em destaque atingido.'
            }, status=400)

    pa.em_destaque = ativar
    pa.save()

    return JsonResponse({
        'ok':          True,
        'em_destaque': pa.em_destaque,
        'count':       PlayerAchievement.objects.filter(
                           player=request.user, em_destaque=True).count(),
    })


# ─────────────────────────────────────────────
# AJAX — INVENTÁRIO (equipar cosmético, ativar slot)
# ─────────────────────────────────────────────

@login_required
@require_POST
def equipar_cosmetico(request):
    try:
        body  = json.loads(request.body)
        pi_id = int(body.get('player_item_id'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    from apps.store.models import PlayerItem

    pi = PlayerItem.objects.filter(pk=pi_id, player=request.user).first()
    if not pi:
        return JsonResponse({'error': 'Item não encontrado.'}, status=404)

    # Substituído 'slot_tipo' por 'tipo' e ajustado valor
    if pi.item.tipo != 'cosmetic':
        return JsonResponse({'error': 'Item não é cosmético.'}, status=400)

    # Desativa cosméticos do mesmo tipo
    # Substituído 'efeito_tipo' por 'effect'
    PlayerItem.objects.filter(
        player=request.user,
        item__effect=pi.item.effect,
        equipado=True,
    ).update(equipado=False)

    pi.equipado = not pi.equipado
    pi.save()

    return JsonResponse({'ok': True, 'equipado': pi.equipado})


@login_required
@require_POST
def usar_retake_token(request):
    import json
    from django.http import JsonResponse
    from django.utils import timezone
    from apps.minigames.models import Quiz, QuizAttempt
    from apps.store.models import ActiveEffect
    from apps.store.services import consumir_efeito_unico

    try:
        body    = json.loads(request.body)
        quiz_id = int(body.get('quiz_id'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    quiz = Quiz.objects.filter(pk=quiz_id, ativo=True).first()
    if not quiz:
        return JsonResponse({'error': 'Quiz não encontrado.'}, status=404)

    if not consumir_efeito_unico(request.user, 'TOKEN_RETAKE'):
        return JsonResponse({'error': 'Sem tokens de retake disponíveis.'}, status=400)

    QuizAttempt.objects.filter(
        player=request.user, quiz=quiz
    ).delete()

    restantes = ActiveEffect.objects.filter(
        player=request.user, effect='TOKEN_RETAKE', expires_at__gt=timezone.now()
    ).count()

    return JsonResponse({
        'ok': True,
        'mensagem': f'Token usado. Quiz "{quiz.titulo}" liberado para refazer.',
        'tokens_restantes': restantes,
    })

# ─────────────────────────────────────────────
# AJAX — NOTIFICAÇÕES
# ─────────────────────────────────────────────

@login_required
@require_POST
def marcar_notificacoes_lidas(request):
    request.user.notifications.filter(lida=False).update(lida=True)
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────
# AJAX — TROCAR CLASSE
# ─────────────────────────────────────────────

@login_required
@require_POST
def trocar_classe_view(request):
    try:
        body        = json.loads(request.body)
        nova_classe = body.get('classe')
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Payload inválido.'}, status=400)

    sucesso, mensagem = trocar_classe(request.user, nova_classe)
    return JsonResponse({'ok': sucesso, 'mensagem': mensagem})


# ─────────────────────────────────────────────
# AJAX — PASSIVOS / CONSUMIVEIS
# ─────────────────────────────────────────────

@login_required
@require_POST
def equipar_passivo_view(request):
    try:
        body = json.loads(request.body)
        pi_id = int(body.get('player_item_id'))
        novo_slot = body.get('slot')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    from apps.store.models import PlayerItem
    
    pi = PlayerItem.objects.filter(pk=pi_id, player=request.user, item__tipo='passive').first()
    if not pi:
        return JsonResponse({'ok': False, 'mensagem': 'Item não encontrado.'})

    if novo_slot is not None:
        # Desocupa o slot alvo caso tenha outro item nele
        PlayerItem.objects.filter(player=request.user, slot_index=int(novo_slot)).update(slot_index=None)
        pi.slot_index = int(novo_slot)
    else:
        pi.slot_index = None

    pi.save()
    return JsonResponse({'ok': True, 'mensagem': 'Passivo atualizado!'})


@login_required
@require_POST
def usar_consumivel_view(request):
    try:
        body = json.loads(request.body)
        pi_id = int(body.get('player_item_id'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    from apps.store.models import PlayerItem
    from apps.store.services import ativar_consumivel
    
    pi = PlayerItem.objects.filter(pk=pi_id, player=request.user).select_related('item').first()
    if not pi:
        return JsonResponse({'ok': False, 'mensagem': 'Item não encontrado.'})

    sucesso, mensagem, _ = ativar_consumivel(request.user, pi.item.item_id)
    return JsonResponse({'ok': sucesso, 'mensagem': mensagem})