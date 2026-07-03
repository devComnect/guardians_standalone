from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum, Count, Avg
import json, os

from .models import (
    Player, Perk, XPEvent, PlayerNotification,
    PlayerAchievement, Achievement, ClasseConfig, OfensivaConfig,
)
from .services import trocar_classe, verificar_conquistas
import os
from django.conf import settings
from django.core.files import File


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
        PatrolAttempt, PasswordAttempt, LogScanAttempt,
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

    # LogScan
    try:
        logscan_total = LogScanAttempt.objects.filter(
            player=user, completed_at__isnull=False, abandoned=False, timer_expired=False
        )
        logscan_count = logscan_total.count()
        logscan_vitorias = logscan_total.filter(correct_count__gt=0).count()
    except Exception:
        logscan_count = logscan_vitorias = 0

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

    desafios_total = quiz_count + dcr_count + cod_count + patrol_count + pw_count + logscan_count

    # . Stats de galeria
    from apps.minigames.models import Quiz
    from apps.training.models import PlayerWordUnlock

    quiz_season_total = Quiz.objects.filter(
        ativo=True,
        available_from__gte=season.inicio
    ).count() if season else 0

    lexico_desbloqueado = PlayerWordUnlock.objects.filter(player=user, season=season).count() if season else 0
    from apps.minigames.models import WordBank
    lexico_total = WordBank.objects.filter(ativo=True).count()

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
            'logscan_count':    logscan_count,
            'logscan_vitorias': logscan_vitorias,
            'ranking_xp':       ranking_xp,
            'ranking_moedas':   ranking_moedas,
            'ranking_ofensiva': ranking_ofensiva,
            'season':           season,
            'quiz_season_total':    quiz_season_total,
            'lexico_desbloqueado':  lexico_desbloqueado,
            'lexico_total':         lexico_total,
        }
    }


def _ctx_bonus(user, player):
    from apps.store.models import PlayerItem, ActiveEffect
    from apps.profiles.models import Perk, PlayerAchievement, OfensivaConfig
    from django.utils import timezone

    radar_stats = {
        'quiz_xp': 0.0,
        'codigo_xp': 0.0,
        'decriptar_xp': 0.0,
        'patrulha_xp': 0.0,
        'cofre_xp': 0.0, 
        'logscan_xp': 0.0,
        'moedas': 0.0,
    }

    global_xp_acumulado = 0.0
    buffs_temporarios = []

    conquistas_ativas = PlayerAchievement.objects.filter(
        player=user, em_destaque=True,
        achievement__bonus_type__isnull=False,
        achievement__bonus_value__gt=0
    ).select_related('achievement')

    for pa in conquistas_ativas:
        tipo = pa.achievement.bonus_type
        valor = pa.achievement.bonus_value
        
        if tipo == 'global_xp_pct': global_xp_acumulado += valor
        elif tipo == 'quiz_xp_pct': radar_stats['quiz_xp'] += valor
        elif tipo == 'termo_xp_pct': radar_stats['codigo_xp'] += valor
        elif tipo == 'anagram_xp_pct': radar_stats['decriptar_xp'] += valor
        elif tipo == 'patrol_xp_pct': radar_stats['patrulha_xp'] += valor
        elif tipo == 'coin_pct': radar_stats['moedas'] += valor
        elif tipo == 'pw_xp_pct': radar_stats['cofre_xp'] += valor
        elif tipo == 'logscan_xp_pct': radar_stats['logscan_xp'] += valor
        elif tipo == 'minigame_xp_pct': 
            radar_stats['codigo_xp'] += valor
            radar_stats['decriptar_xp'] += valor
            radar_stats['cofre_xp'] += valor
            radar_stats['logscan_xp'] += valor

    perks_ativos = Perk.objects.filter(
        classe=player.classe, level_required__lte=player.level, ativo=True
    ).order_by('level_required')

    for perk in perks_ativos:
        if perk.tipo == 'global_xp_pct': global_xp_acumulado += perk.valor
        elif perk.tipo == 'xp_quiz': radar_stats['quiz_xp'] += perk.valor
        elif perk.tipo == 'xp_codigo': radar_stats['codigo_xp'] += perk.valor
        elif perk.tipo == 'xp_decriptar': radar_stats['decriptar_xp'] += perk.valor
        elif perk.tipo == 'xp_password':  radar_stats['cofre_xp'] += perk.valor
        elif perk.tipo == 'xp_logscan':   radar_stats['logscan_xp'] += perk.valor
        elif perk.tipo == 'coin_bonus': radar_stats['moedas'] += perk.valor

    from apps.store.services import get_passive_bonus_xp_pct

    passivos_equipados = PlayerItem.objects.filter(
        player=user, slot_index__isnull=False, item__tipo='passive'
    ).select_related('item')

    fontes_radar = {
        'quiz_xp':     'quiz',
        'codigo_xp':   'codigo',
        'decriptar_xp':'decriptar',
        'patrulha_xp': 'patrol',
        'cofre_xp':    'password',
        'logscan_xp':  'logscan',
    }

    for chave_radar, fonte_sim in fontes_radar.items():
        bonus_fonte, _ = get_passive_bonus_xp_pct(user, fonte=fonte_sim, retornar_breakdown=True)
        radar_stats[chave_radar] += bonus_fonte

    agora = timezone.now()
    efeitos_ativos = ActiveEffect.objects.filter(
        player=user, expires_at__gt=agora
    ).select_related('item')

    for efeito in efeitos_ativos:
        tempo_restante = efeito.expires_at - agora
        horas, resto = divmod(tempo_restante.seconds, 3600)
        dias = tempo_restante.days
        tempo_str = f"{dias}d {horas}h" if dias > 0 else f"{horas}h {resto // 60}m"
        
        if 'XP_BOOST' in efeito.effect:
            global_xp_acumulado += efeito.value

        buffs_temporarios.append({
            'nome': efeito.item.name if efeito.item else efeito.effect,
            'descricao': efeito.item.description if efeito.item else 'Efeito do sistema.',
            'expira_em': efeito.expires_at,
            'tempo_str': tempo_str,
            'valor': efeito.value
        })

    if global_xp_acumulado > 0:
        radar_stats['quiz_xp'] += global_xp_acumulado
        radar_stats['codigo_xp'] += global_xp_acumulado
        radar_stats['decriptar_xp'] += global_xp_acumulado
        radar_stats['patrulha_xp'] += global_xp_acumulado
        radar_stats['logscan_xp'] += global_xp_acumulado

    ofensiva_config = OfensivaConfig.get()
    teto_ofensiva = ofensiva_config.teto_bonus_ofensiva

    from apps.profiles.services import get_perk_valor
    teto_extra = get_perk_valor(user, 'ofensiva_teto')
    teto_ofensiva += int(teto_extra)

    from apps.store.models import ActiveEffect as _AE
    efeito_cap = _AE.objects.filter(
        player=user, effect='STREAK_CAP_BOOST', expires_at__gt=agora
    ).first()
    if efeito_cap:
        teto_ofensiva += int(efeito_cap.value)

    bonus_ofensiva = min(player.ofensiva, teto_ofensiva)
    multiplicador_ofensiva = bonus_ofensiva / 100

    CHAVES_XP = ('quiz_xp', 'codigo_xp', 'decriptar_xp', 'patrulha_xp', 'cofre_xp', 'logscan_xp')
    for chave in CHAVES_XP:
        base = radar_stats[chave]
        radar_stats[chave] = round(base + (1 + base / 100) * multiplicador_ofensiva * 100, 2)

    return {
        'bonus': {
            'perks_ativos':       perks_ativos,
            'conquistas_bonus':   conquistas_ativas,
            'itens_slot':         passivos_equipados,
            'buffs_temporarios':  buffs_temporarios,
            'matriz_radar':       radar_stats,
            'bonus_ofensiva':     bonus_ofensiva,
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
        PatrolAttempt, PasswordAttempt, LogScanAttempt,
    )
    from django.db.models import Avg

    def _taxa(total, sucesso):
        return round((sucesso / total * 100) if total > 0 else 0, 1)

    quiz_tot  = QuizAttempt.objects.filter(player=user, completed_at__isnull=False)
    dcr_tot   = DecriptarAttempt.objects.filter(player=user, completed_at__isnull=False)
    cod_tot   = CodigoAttempt.objects.filter(player=user, completed_at__isnull=False)
    
    # LogScan
    logscan_tot = LogScanAttempt.objects.filter(
        player=user, completed_at__isnull=False, abandoned=False, timer_expired=False
    )

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
    logscan_xp_medio = logscan_tot.aggregate(m=Avg('xp_earned'))['m'] or 0

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
            'nome':      'LogScan',
            'icone':     'bi-upc-scan',
            'cor':       '#00ff9f',
            'total':     logscan_tot.count(),
            'taxa':      _taxa(logscan_tot.count(),
                               logscan_tot.filter(correct_count__gt=0).count()),
            'xp_medio':  round(logscan_xp_medio, 0),
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

    skills_sorted = sorted(skills, key=lambda x: x['taxa'], reverse=True)

    return {'skills': skills_sorted}


def _ctx_atividade_semanal(user):
    from apps.minigames.models import (
        QuizAttempt, DecriptarAttempt, CodigoAttempt,
        PatrolAttempt, PasswordAttempt, LogScanAttempt
    )
    from django.utils import timezone
    from datetime import datetime, time, timedelta

    hoje = timezone.localdate()
    segunda = hoje - timedelta(days=hoje.weekday())
    dias = []
    nomes_dias = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM']

    for i in range(7):
        dia = segunda + timedelta(days=i)
        
        inicio_dia = timezone.make_aware(datetime.combine(dia, time.min))
        fim_dia = timezone.make_aware(datetime.combine(dia, time.max))

        quiz_dia = QuizAttempt.objects.filter(player=user, completed_at__range=(inicio_dia, fim_dia)).count()
        dcr_dia = DecriptarAttempt.objects.filter(player=user, date=dia, completed_at__isnull=False).count()
        cod_dia = CodigoAttempt.objects.filter(player=user, date=dia, completed_at__isnull=False).count()
        
        try:
            patrol_dia = PatrolAttempt.objects.filter(player=user, date=dia, completed=True).count()
        except Exception:
            patrol_dia = 0

        try:
            pw_dia = PasswordAttempt.objects.filter(player=user, completed_at__range=(inicio_dia, fim_dia)).count()
        except Exception:
            pw_dia = 0

        try:
            logscan_dia = LogScanAttempt.objects.filter(
                player=user, date=dia, completed_at__isnull=False, abandoned=False, timer_expired=False
            ).count()
        except Exception:
            logscan_dia = 0

        total_dia = quiz_dia + dcr_dia + cod_dia + patrol_dia + pw_dia + logscan_dia
        
        detalhes = {}
        if quiz_dia:     detalhes['Quiz']     = quiz_dia
        if dcr_dia:      detalhes['Decriptar'] = dcr_dia
        if cod_dia:      detalhes['Código']   = cod_dia
        if patrol_dia:   detalhes['Patrulha'] = patrol_dia
        if pw_dia:       detalhes['Cofre']    = pw_dia
        if logscan_dia:  detalhes['LogScan']  = logscan_dia

        dias.append({
            'data':     dia,
            'dia_nome': nomes_dias[i],
            'total':    total_dia,
            'detalhes': detalhes,
            'ativo':    total_dia > 0,
            'hoje':     dia == hoje,
            'futuro':   dia > hoje,
        })

    streak_visual = 0
    for d in reversed([d for d in dias if d['data'] <= hoje]):
        if d['ativo']:
            streak_visual += 1
        else:
            break

    return {
        'atividade_semanal': dias,
        'streak_visual': streak_visual,
    }

def _ctx_inventario(user):
    from apps.store.models import PlayerItem, StoreConfig
    
    config = StoreConfig.get()
    inventario = PlayerItem.objects.filter(player=user).select_related('item').order_by('item__tipo', '-adquirido_em')

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
        'itens_novos_count':      sum(1 for pi in inventario if getattr(pi, 'is_new', False)),
        'passivos_novos_count':   sum(1 for pi in passivos if getattr(pi, 'is_new', False)),
        'consumiveis_novos_count':sum(1 for pi in consumiveis if getattr(pi, 'is_new', False)),
        'cosmeticos_novos_count': sum(1 for pi in cosmeticos if getattr(pi, 'is_new', False)),
    }

def _ctx_conquistas(user):
    from .models import AchievementConfig
    from collections import defaultdict

    BONUS_GRUPOS = {
        'global_xp_pct':   'Bônus Global',
        'quiz_xp_pct':     'Bônus em Quiz',
        'minigame_xp_pct': 'Bônus em Minigames',
        'patrol_xp_pct':   'Bônus em Patrulha',
        'anagram_xp_pct':  'Bônus em Decriptar',
        'termo_xp_pct':    'Bônus em Código',
        'pw_xp_pct':       'Bônus em Cofre de Senhas',
        'coin_pct':        'Bônus de Moedas',
        'ofensiva_teto':   'Ofensiva',
        'streak_shield':   'Streak',
        'logscan_xp_pct':  'Bônus em LogScan',
        None:              'Sem Bônus',
    }

    config      = AchievementConfig.get()
    todas       = Achievement.objects.filter(ativo=True).order_by('raridade', 'trigger_value')
    desbloqueadas = PlayerAchievement.objects.filter(
        player=user
    ).select_related('achievement').order_by('achievement__bonus_type', 'achievement__raridade')

    ids_desbloqueados = set(pa.achievement_id for pa in desbloqueadas)
    em_destaque_count = desbloqueadas.filter(em_destaque=True).count()
    bloqueadas        = [a for a in todas if a.id not in ids_desbloqueados]

    grupos = defaultdict(list)
    for pa in desbloqueadas:
        chave = pa.achievement.bonus_type or None
        grupos[chave].append(pa)

    conquistas_agrupadas = [
        {'label': BONUS_GRUPOS.get(k, k), 'items': v}
        for k, v in sorted(grupos.items(), key=lambda x: list(BONUS_GRUPOS.keys()).index(x[0]) if x[0] in BONUS_GRUPOS else 99)
    ]

    return {
        'conquistas_agrupadas':   conquistas_agrupadas,
        'conquistas_desbloqueadas': desbloqueadas,
        'conquistas_bloqueadas':  bloqueadas,
        'conquistas_em_destaque': desbloqueadas.filter(em_destaque=True),
        'max_destaques':          config.max_destaques,
        'em_destaque_count':      em_destaque_count,
    }

def _ctx_battle_pass(user):
    from .models import BattlePassConfig, PlayerBattlePass

    bp_config = BattlePassConfig.get_ativo()
    if not bp_config:
        return {'battle_pass': None, 'player_bp': None, 'bp_tiers': []}

    pbp = PlayerBattlePass.objects.filter(
        player=user, battle_pass=bp_config
    ).first()

    tiers = bp_config.tiers.select_related('recompensa_item').all()

    tiers_info = []
    coletados  = set(pbp.tiers_coletados if pbp else [])
    xp_atual   = pbp.xp_bp if pbp else 0

    for tier in tiers:
        desbloqueado = xp_atual >= tier.xp_necessario
        tiers_info.append({
            'tier':          tier,
            'desbloqueado':  desbloqueado,
            'coletado':      tier.tier in coletados,
            'disponivel':    desbloqueado and tier.tier not in coletados,
        })

    proximo = next((t for t in tiers_info if not t['desbloqueado']), None)
    xp_para_proximo = (proximo['tier'].xp_necessario - xp_atual) if proximo else 0
    pct_proximo = 0
    if proximo:
        tier_anterior_xp = tiers_info[tiers_info.index(proximo) - 1]['tier'].xp_necessario if tiers_info.index(proximo) > 0 else 0
        faixa = proximo['tier'].xp_necessario - tier_anterior_xp
        ganho = xp_atual - tier_anterior_xp
        pct_proximo = min(100, int(ganho / faixa * 100)) if faixa > 0 else 100

    return {
        'battle_pass':      bp_config,
        'player_bp':        pbp,
        'bp_tiers':         tiers_info,
        'bp_xp_atual':      xp_atual,
        'bp_xp_para_proximo': xp_para_proximo,
        'bp_pct_proximo':   pct_proximo,
        'bp_disponíveis':   sum(1 for t in tiers_info if t['disponivel']),
    }

def _ctx_missoes(user):
    """Missões ativas do player (Sincronizado com a Home)."""
    try:
        from apps.missions.models import UserMissionSet
        mission_set = UserMissionSet.objects.filter(
            user=user, is_claimed=False
        ).order_by('-created_at').first()

        if mission_set:
            active_missions = mission_set.missions.all().order_by('id')
        else:
            active_missions = []

    except ImportError:
        mission_set = None
        active_missions = []
        
    except Exception as e:
        mission_set = None
        active_missions = []

    return {
        'mission_set': mission_set,
        'active_missions': active_missions,
        **_ctx_battle_pass(user),
    }

def _ctx_log(user):
    import json
    from apps.store.models import ActiveEffect
    from apps.profiles.models import SystemLog
    from django.utils import timezone

    logs = list(SystemLog.objects.filter(player=user).order_by('-criado_em')[:80])

    breakdowns = {str(log.pk): log.breakdown for log in logs}
    breakdowns_json = json.dumps(breakdowns, ensure_ascii=False)

    agora = timezone.now()
    retake_count = ActiveEffect.objects.filter(
        player=user, effect='TOKEN_RETAKE', expires_at__gt=agora
    ).count()

    class DummyToken: pass
    retake_token = DummyToken()
    retake_token.usos_restantes = retake_count

    return {
        'system_logs':                  logs,
        'system_logs_breakdowns_json':  breakdowns_json,
        'retake_token':                 retake_token if retake_count > 0 else None,
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
        display_name  = request.POST.get('display_name', '').strip()
        bio           = request.POST.get('bio', '').strip()
        avatar_choice = request.POST.get('avatar_choice')

        if display_name:
            player.display_name = display_name[:60]
        player.bio = bio[:300]

        if avatar_choice:
            avatares_permitidos = [
                'avatar echo.png', 'avatar node 7.png',
                'avatar setx.png', 'avatar steve.png', 'avatar troia.png'
            ]
            if avatar_choice in avatares_permitidos:
                player.avatar.name = f'img/avatares/{avatar_choice}'

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

@login_required
def selecao_classe_view(request):
    from apps.profiles.models import Perk, ClasseConfig
    
    player = getattr(request.user, 'player', None)
    if not player:
        return redirect('core:home')
        
    config = ClasseConfig.get()
    is_primeira_vez = (player.classe == 'none')
    custo_atual = config.custo_primeira_classe if is_primeira_vez else config.custo_troca_coins
    
    # Estrutura de base das classes e suas cores
    classes_info = {
        'guardian': {
            'nome': 'GUARDIAN',
            'desc': 'O Banqueiro. Maximiza ganho de moedas e desconto na loja — ideal para quem quer acumular recursos e itens raros rapidamente, sacrificando parte do XP global.',
            'cor': '#0dcaf0', 'icone': 'bi-shield-fill-check', 'perks': []
        },
        'analyst': {
            'nome': 'ANALYST',
            'desc': 'O Late Game. Ganha pouco no início, mas escala o maior bônus de XP global do jogo — a melhor escolha pra quem joga a temporada inteira e foca em Decriptar.',
            'cor': '#bd00ff', 'icone': 'bi-radar', 'perks': []
        },
        'sentinel': {
            'nome': 'SENTINEL',
            'desc': 'O Defensor Consistente. Perks equilibrados entre Patrulha, LogScan e Cofre. Com reforço no teto de bônus de ofensiva — recompensa quem joga todo dia sem falhar.',
            'cor': '#fcee0a', 'icone': 'bi-eye-fill', 'perks': []
        },
        'hacker': {
            'nome': 'HACKER',
            'desc': 'O Especialista Agressivo. Zero bônus global — todo o poder vem de dominar os desafios de Código, com o maior multiplicador de XP focado do jogo.',
            'cor': '#ff2a6d', 'icone': 'bi-terminal-fill', 'perks': []
        },
    }
    
    # Popula as classes com seus perks correspondentes organizados por level
    todos_perks = Perk.objects.filter(ativo=True).order_by('level_required')
    for p in todos_perks:
        if p.classe in classes_info:
            classes_info[p.classe]['perks'].append(p)
            
    return render(request, 'profiles/selecao_classe.html', {
        'player': player,
        'classes_info': classes_info,
        'custo_atual': custo_atual,
        'is_primeira_vez': is_primeira_vez
    })


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


@login_required
@require_POST
def coletar_todos_bp(request):
    from .services import coletar_recompensa_bp
    from .models import BattlePassConfig, PlayerBattlePass

    bp_config = BattlePassConfig.get_ativo()
    if not bp_config:
        return JsonResponse({'ok': False, 'error': 'Nenhum battle pass ativo.'}, status=400)

    pbp = PlayerBattlePass.objects.filter(player=request.user, battle_pass=bp_config).first()
    if not pbp:
        return JsonResponse({'ok': False, 'error': 'Você não possui este battle pass.'}, status=400)

    coletados = set(pbp.tiers_coletados or [])
    xp_atual  = pbp.xp_bp
    tiers_disponiveis = [
        t for t in bp_config.tiers.order_by('tier')
        if xp_atual >= t.xp_necessario and t.tier not in coletados
    ]

    if not tiers_disponiveis:
        return JsonResponse({'ok': False, 'error': 'Nenhuma recompensa disponível.'}, status=400)

    resultados = []
    for tier in tiers_disponiveis:
        sucesso, mensagem, descricao = coletar_recompensa_bp(request.user, tier.tier)
        resultados.append({'tier': tier.tier, 'ok': sucesso, 'recompensa': descricao})

    coletados_count = sum(1 for r in resultados if r['ok'])
    return JsonResponse({
        'ok': True,
        'mensagem': f'{coletados_count} recompensa(s) coletada(s)!',
        'resultados': resultados,
    })

@login_required
@require_POST
def coletar_tier_bp(request):
    try:
        body   = json.loads(request.body)
        tier_n = int(body.get('tier'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    from .services import coletar_recompensa_bp
    sucesso, mensagem, descricao = coletar_recompensa_bp(request.user, tier_n)
    return JsonResponse({'ok': sucesso, 'mensagem': mensagem, 'recompensa': descricao})

@login_required
@require_POST
def marcar_inventario_visto(request):
    from apps.store.models import PlayerItem
    PlayerItem.objects.filter(player=request.user, is_new=True).update(is_new=False)
    return JsonResponse({'ok': True})

# ─────────────────────────────────────────────
# PERFIL PÚBLICO (Visão de Terceiros)
# ───────────────────────────────────────────── 

@login_required
def public_profile(request, player_id):
    from django.shortcuts import get_object_or_404
    from django.contrib.auth.models import User
    from django.db.models import Q
    target_user = get_object_or_404(User, pk=player_id)
    player_obj = getattr(target_user, 'player', None)

    if not player_obj:
        messages.error(request, 'Perfil de jogador não encontrado.')
        return redirect('rankings:index')

    if target_user == request.user:
        return redirect('profiles:index')

    from apps.store.models import PlayerItem
    from apps.profiles.models import PlayerAchievement, SystemLog, AchievementConfig

    frame_ativo = PlayerItem.objects.filter(
        player=target_user, equipado=True, item__effect='COSMETIC_FRAME'
    ).select_related('item').first()

    bg_ativo = PlayerItem.objects.filter(
        player=target_user, equipado=True, item__effect='COSMETIC_BACKGROUND'
    ).select_related('item').first()

    titulo_ativo = PlayerItem.objects.filter(
        player=target_user, equipado=True, item__effect='COSMETIC_TITLE'
    ).select_related('item').first()

    conquistas_desbloqueadas = PlayerAchievement.objects.filter(
        player=target_user
    ).select_related('achievement').order_by('-desbloqueada_em')

    conquistas_em_destaque = conquistas_desbloqueadas.filter(em_destaque=True)

    logs_raw = SystemLog.objects.filter(
        player=target_user
    ).filter(
        Q(xp_delta__gt=0) | Q(coin_delta__gt=0)
    ).order_by('-criado_em')[:15]

    logs_recentes = []
    for log in logs_raw:
        titulo = log.titulo or "SISTEMA"
        if titulo.upper().startswith("CÓDIGO:"):
            titulo = "CÓDIGO"
        logs_recentes.append({
            'criado_em': log.criado_em,
            'titulo': titulo,
            'descricao': log.descricao,
            'xp_delta': log.xp_delta,
            'coin_delta': log.coin_delta,
        })

    from apps.profiles.services import get_ofensiva_bonus_pct
    ofensiva_bonus = get_ofensiva_bonus_pct(target_user)

    config = AchievementConfig.get()

    from apps.store.models import PlayerItem, ActiveEffect, StoreConfig
    from django.utils import timezone

    config_store = StoreConfig.get()
    passivos = PlayerItem.objects.filter(
        player=target_user, item__tipo='passive'
    ).select_related('item')
    slot_ocupado = {pi.slot_index: pi for pi in passivos if pi.slot_index is not None}
    slots_grade = [
        {'numero': s, 'player_item': slot_ocupado.get(s)}
        for s in range(1, config_store.max_passivos_slots + 1)
    ]

    efeitos_ativos = ActiveEffect.objects.filter(
        player=target_user, expires_at__gt=timezone.now()
    ).select_related('item')

    from apps.minigames.models import (
        QuizAttempt, PatrolAttempt, PasswordAttempt,
        DecriptarAttempt, CodigoAttempt, LogScanAttempt,
    )
    from django.db.models import Max, Avg, F, ExpressionWrapper, DurationField
    from apps.profiles.models import XPEvent
    from datetime import timedelta

    # Cadastro central de minigames "padrão" (completed_at/started_at + xp/coins_earned).
    # Adicionar um novo minigame aqui já propaga para total_minigames, maior_xp,
    # tempo médio e histórico — sem precisar tocar no resto da view.
    MINIGAME_DEFS = [
        {'tipo': 'Quiz',      'model': QuizAttempt,     'filtro': {'completed_at__isnull': False, 'abandoned': False, 'timer_expired': False}, 'fonte': 'quiz',      'conta_minigame': False},
        {'tipo': 'Cofre',     'model': PasswordAttempt, 'filtro': {'is_won': True},                                                             'fonte': 'password',  'conta_minigame': True},
        {'tipo': 'Decriptar', 'model': DecriptarAttempt,'filtro': {'completed_at__isnull': False, 'abandoned': False, 'timer_expired': False}, 'fonte': 'decriptar', 'conta_minigame': True},
        {'tipo': 'Código',    'model': CodigoAttempt,   'filtro': {'won': True},                                                                'fonte': 'codigo',    'conta_minigame': True},
        {'tipo': 'LogScan',   'model': LogScanAttempt,  'filtro': {'completed_at__isnull': False, 'abandoned': False, 'timer_expired': False}, 'fonte': 'logscan',   'conta_minigame': True},
    ]

    total_quizzes = QuizAttempt.objects.filter(player=target_user, **MINIGAME_DEFS[0]['filtro']).count()

    total_minigames = sum(
        d['model'].objects.filter(player=target_user, **d['filtro']).count()
        for d in MINIGAME_DEFS if d['conta_minigame']
    )

    total_patrulhas = PatrolAttempt.objects.filter(player=target_user, completed=True).count()

    maior_xp = XPEvent.objects.filter(
        player=target_user,
        fonte__in=[d['fonte'] for d in MINIGAME_DEFS] + ['patrol'],
    ).aggregate(m=Max('xp_total'))['m'] or 0

    tempos = []
    for d in MINIGAME_DEFS + [{'model': PatrolAttempt, 'filtro': {'completed': True}}]:
        avg = d['model'].objects.filter(player=target_user, **d['filtro']).annotate(
            duracao=ExpressionWrapper(F('completed_at') - F('started_at'), output_field=DurationField())
        ).aggregate(media=Avg('duracao'))['media']
        if avg:
            tempos.append(avg.total_seconds())

    tempo_medio_seg = int(sum(tempos) / len(tempos)) if tempos else 0
    tempo_medio_str = f"{tempo_medio_seg // 60}m {tempo_medio_seg % 60}s" if tempo_medio_seg else "—"

    FONTE_MAP = {d['tipo']: d['fonte'] for d in MINIGAME_DEFS}
    FONTE_MAP['Patrulha'] = 'patrol'

    def _attempt_row(obj, tipo):
        row = {
            'tipo': tipo,
            'titulo': tipo,
            'xp_earned': obj.xp_earned,
            'coins_earned': obj.coins_earned,
            'completed_at': obj.completed_at,
            'duracao': None,
            'acertos': None,
            'xp_base': None,
            'xp_bonus': None,
        }
        if obj.completed_at and obj.started_at:
            seg = int((obj.completed_at - obj.started_at).total_seconds())
            row['duracao'] = f"{seg // 60}m {seg % 60}s"

        if tipo == 'Quiz':
            total_q = obj.quiz.questions.count() if hasattr(obj, 'quiz') else '?'
            row['acertos'] = f"{obj.total_correct}/{total_q}"
            row['titulo'] = obj.quiz.titulo
        elif tipo == 'Código':
            row['acertos'] = f"{len(obj.guesses)}/{obj.max_attempts}"
        elif tipo == 'Decriptar':
            total_d = len(obj.words_sequence) if obj.words_sequence else '?'
            row['acertos'] = f"{obj.correct_count}/{total_d}"
        elif tipo == 'LogScan':
            total_lw = len(obj.words_sequence) if obj.words_sequence else '?'
            row['acertos'] = f"{obj.correct_count}/{total_lw}"
        elif tipo == 'Patrulha':
            row['acertos'] = f"{obj.attempts_count}/10"
            row['duracao'] = None

        fonte = FONTE_MAP.get(tipo)
        if fonte and obj.completed_at:
            janela_inicio = obj.completed_at - timedelta(seconds=15)
            janela_fim    = obj.completed_at + timedelta(seconds=15)
            evento = XPEvent.objects.filter(
                player=target_user,
                fonte=fonte,
                criado_em__gte=janela_inicio,
                criado_em__lte=janela_fim,
            ).order_by('-criado_em').first()
            if evento:
                row['xp_base']  = evento.xp_base
                row['xp_bonus'] = evento.xp_bonus

        return row

    historico_desafios = []

    for d in MINIGAME_DEFS:
        qs = d['model'].objects.filter(player=target_user, **d['filtro']).order_by('-completed_at')[:4]
        for obj in qs:
            historico_desafios.append(_attempt_row(obj, d['tipo']))

    patrulha_qs = PatrolAttempt.objects.filter(
        player=target_user, completed=True
    ).order_by('-completed_at')[:4]
    for obj in patrulha_qs:
        historico_desafios.append(_attempt_row(obj, 'Patrulha'))

    bonus_qs = XPEvent.objects.filter(
        player=target_user,
        fonte='bonus',
    ).order_by('-criado_em')[:4]

    for obj in bonus_qs:
        historico_desafios.append({
            'tipo':         'bonus',
            'titulo':       obj.descricao,
            'xp_earned':    obj.xp_total,
            'coins_earned': 0,
            'completed_at': obj.criado_em,
            'duracao':      None,
            'acertos':      None,
            'xp_base':      obj.xp_base,
            'xp_bonus':     obj.xp_bonus,
        })
    historico_desafios.sort(key=lambda x: x['completed_at'], reverse=True)

    context = {
        'target_user': target_user,
        'player_obj': player_obj,
        'frame_ativo': frame_ativo,
        'bg_ativo': bg_ativo,
        'titulo_ativo': titulo_ativo,
        'conquistas_desbloqueadas': conquistas_desbloqueadas,
        'conquistas_em_destaque': conquistas_em_destaque,
        'logs_recentes': logs_recentes,
        'ofensiva_bonus': ofensiva_bonus,
        'config': config,
        'slots_grade': slots_grade,
        'efeitos_ativos': efeitos_ativos,
        'total_quizzes': total_quizzes,
        'total_minigames': total_minigames,
        'total_patrulhas': total_patrulhas,
        'maior_xp': maior_xp,
        'tempo_medio_str': tempo_medio_str,
        'historico_desafios': historico_desafios,
    }

    return render(request, 'profiles/public_profile.html', context)