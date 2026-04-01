"""
Serviço central de progressão do player.
Todos os minigames devem usar grant_xp() para conceder XP.
"""

from django.utils import timezone
from django.db import transaction
from .models import OfensivaConfig


def xp_para_nivel(nivel):
    return int(50 * (nivel ** 2.5))


def get_perks_ativos(user):
    """Retorna todos os perks ativos do player baseado na classe e level."""
    from .models import Perk
    player = getattr(user, 'player', None)
    if not player:
        return Perk.objects.none()
    return Perk.objects.filter(
        classe=player.classe,
        level_required__lte=player.level,
        ativo=True
    )


def get_perk_valor(user, tipo):
    """Retorna o valor acumulado de perks de um tipo específico."""
    perks = get_perks_ativos(user).filter(tipo=tipo)
    return sum(p.valor for p in perks)


def calcular_xp_com_bonus(user, xp_base, fonte, contexto=None):
    """
    Aplica perks + bônus de ofensiva ao valor base.
    Retorna (xp_final, xp_bonus, bonus_breakdown).
    """
    from apps.store.services import get_passive_bonus_xp_pct

    player = getattr(user, 'player', None)
    bonus_pct   = 0
    breakdown   = []

    # ── Perks globais ────────────────────────────
    perks_global = get_perks_ativos(user).filter(tipo='xp_global')
    for perk in perks_global:
        bonus_pct += perk.valor
        breakdown.append({
            "fonte":        perk.nome,
            "categoria":    "Perk Global",
            "tipo":         "xp_global",
            "pct":          perk.valor,
            "xp_adicionado": int(xp_base * perk.valor / 100),
        })

    # ── Perks específicos por fonte ──────────────
    mapa_fonte = {
        'quiz':      'xp_quiz',
        'decriptar': 'xp_decriptar',
        'codigo':    'xp_codigo',
        'password':  'xp_password',
    }
    tipo_especifico = mapa_fonte.get(fonte)
    if tipo_especifico:
        perks_fonte = get_perks_ativos(user).filter(tipo=tipo_especifico)
        for perk in perks_fonte:
            bonus_pct += perk.valor
            breakdown.append({
                "fonte":         perk.nome,
                "categoria":     "Perk Específico",
                "tipo":          tipo_especifico,
                "pct":           perk.valor,
                "xp_adicionado": int(xp_base * perk.valor / 100),
            })

    # ── Ofensiva ─────────────────────────────────
    bonus_ofensiva = get_ofensiva_bonus_pct(user)
    if bonus_ofensiva:
        bonus_pct += bonus_ofensiva
        breakdown.append({
            "fonte":         f"Ofensiva ({player.ofensiva} pts)",
            "categoria":     "Ofensiva",
            "tipo":          "ofensiva",
            "pct":           bonus_ofensiva,
            "xp_adicionado": int(xp_base * bonus_ofensiva / 100),
        })

    # ── Conquistas — global ───────────────────────
    from .models import PlayerAchievement, AchievementConfig
    config = AchievementConfig.get()
    ach_global = (
        PlayerAchievement.objects
        .filter(player=user, em_destaque=True,
                achievement__bonus_type='global_xp_pct',
                achievement__ativo=True)
        .select_related('achievement')[:config.max_destaques]
    )
    for pa in ach_global:
        v = pa.achievement.bonus_value
        bonus_pct += v
        breakdown.append({
            "fonte":         pa.achievement.nome,
            "categoria":     "Conquista",
            "tipo":          "global_xp_pct",
            "pct":           v,
            "xp_adicionado": int(xp_base * v / 100),
        })

    # ── Conquistas — específicas por fonte ────────
    mapa_fonte_ach = {
        'quiz':      'quiz_xp_pct',
        'decriptar': 'anagram_xp_pct',
        'codigo':    'termo_xp_pct',
        'password':  'pw_xp_pct',
        'patrol':    'patrol_xp_pct',
    }
    tipo_ach = mapa_fonte_ach.get(fonte)
    if tipo_ach:
        ach_fonte = (
            PlayerAchievement.objects
            .filter(player=user, em_destaque=True,
                    achievement__bonus_type=tipo_ach,
                    achievement__ativo=True)
            .select_related('achievement')[:config.max_destaques]
        )
        for pa in ach_fonte:
            v = pa.achievement.bonus_value
            bonus_pct += v
            breakdown.append({
                "fonte":         pa.achievement.nome,
                "categoria":     "Conquista",
                "tipo":          tipo_ach,
                "pct":           v,
                "xp_adicionado": int(xp_base * v / 100),
            })

    # ── Passivos da loja ──────────────────────────
    bonus_passivos, passivos_breakdown = get_passive_bonus_xp_pct(
        user, fonte=fonte, contexto=contexto or {}, retornar_breakdown=True
    )
    bonus_pct += bonus_passivos
    
    for item in passivos_breakdown:
        item['xp_adicionado'] = int(xp_base * item['pct'] / 100)

    breakdown.extend(passivos_breakdown)

    xp_bonus = int(xp_base * bonus_pct / 100)
    xp_final = xp_base + xp_bonus

    return xp_final, xp_bonus, breakdown


@transaction.atomic
def grant_xp(user, xp_base, fonte, descricao='', contexto=None):
    from .models import XPEvent, PlayerNotification

    player = getattr(user, 'player', None)
    if not player or xp_base <= 0:
        return {'xp_total': 0, 'level_up': False, 'novo_level': None}

    xp_final, xp_bonus, bonus_breakdown = calcular_xp_com_bonus(
        user, xp_base, fonte, contexto=contexto
    )

    XPEvent.objects.create(
        player    = user,
        fonte     = fonte,
        xp_base   = xp_base,
        xp_bonus  = xp_bonus,
        xp_total  = xp_final,
        descricao = descricao or f'+{xp_final} XP via {fonte}',
        breakdown = bonus_breakdown,
    )

    player.xp_total += xp_final
    level_antes = player.level

    niveis_subidos = []
    while player.xp_total >= xp_para_nivel(player.level):
        player.level += 1
        niveis_subidos.append(player.level)

    player.save()

    level_up = len(niveis_subidos) > 0
    for nivel in niveis_subidos:
        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'level_up',
            titulo   = f'LEVEL UP — Nível {nivel}!',
            mensagem = f'Parabéns! Você atingiu o nível {nivel}.',
            icone    = 'bi-arrow-up-circle-fill',
        )
        _notificar_perks_desbloqueados(user, player.classe, nivel)

    try:
        atualizar_battle_pass(user, xp_final)
    except Exception:
        pass

    return {
        'xp_base':        xp_base,
        'xp_bonus':       xp_bonus,
        'xp_final':       xp_final,
        'bonus_breakdown': bonus_breakdown,
        'level_up':       level_up,
        'level_antes':    level_antes,
        'novo_level':     player.level if level_up else None,
        'niveis_subidos': niveis_subidos,
    }


@transaction.atomic
def grant_coins(user, coins_base, fonte='bonus'):
    """Concede coins ao player aplicando perk de bônus de moedas."""
    player = getattr(user, 'player', None)
    if not player or coins_base <= 0:
        return 0

    bonus_pct  = get_perk_valor(user, 'coin_bonus')
    coins_final = int(coins_base * (1 + bonus_pct / 100))
    player.coins += coins_final
    player.save()
    return coins_final


def _notificar_perks_desbloqueados(user, classe, nivel):
    """Cria notificação para cada perk desbloqueado nesse nível."""
    from .models import Perk, PlayerNotification
    perks = Perk.objects.filter(classe=classe, level_required=nivel, ativo=True)
    for perk in perks:
        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'perk_unlock',
            titulo   = f'PERK DESBLOQUEADO — {perk.nome}',
            mensagem = perk.descricao,
            icone    = 'bi-lightning-charge-fill',
        )


@transaction.atomic
def trocar_classe(user, nova_classe):
    """
    Troca a classe do player deduzindo coins baseando-se se é primeira escolha ou troca.
    Retorna (sucesso, mensagem).
    """
    from .models import ClasseConfig, PlayerNotification
    from django.utils import timezone
    
    player = getattr(user, 'player', None)
    if not player:
        return False, 'Perfil não encontrado.'

    classes_validas = ['guardian', 'analyst', 'sentinel', 'hacker']
    if nova_classe not in classes_validas:
        return False, 'Classe inválida.'

    if nova_classe == player.classe:
        return False, 'Você já pertence a esta classe.'

    config = ClasseConfig.get()
    
    # Valida se é a primeira escolha
    is_primeira_vez = (player.classe == 'none')
    custo = config.custo_primeira_classe if is_primeira_vez else config.custo_troca_coins

    if player.coins < custo:
        return False, f'Coins insuficientes. Necessário: {custo} ⬡'

    classe_antiga = player.get_classe_display()
    
    # Aplica as mudanças
    player.coins             -= custo
    player.classe             = nova_classe
    player.classe_trocada_em  = timezone.now()
    player.save()

    # Define a mensagem dependendo do contexto
    if is_primeira_vez:
        mensagem_log = f'Você definiu sua classe e se juntou aos {player.get_classe_display()}.'
    else:
        mensagem_log = f'Você deixou os {classe_antiga} e se juntou aos {player.get_classe_display()}.'

    PlayerNotification.objects.create(
        player   = user,
        tipo     = 'sistema',
        titulo   = f'Classe definida: {player.get_classe_display()}',
        mensagem = mensagem_log,
        icone    = 'bi-diagram-3-fill',
    )

    return True, f'Bem-vindo aos {player.get_classe_display()}!'

@transaction.atomic
def revoke_xp(user, xp_amount, descricao=''):
    """
    Remove XP do player e recalcula o level.
    Chamado automaticamente ao resetar tentativas.
    """
    from .models import XPEvent, PlayerNotification

    player = getattr(user, 'player', None)
    if not player or xp_amount <= 0:
        return

    # Remove o XP (nunca fica negativo)
    player.xp_total = max(0, player.xp_total - xp_amount)

    # Recalcula o level de baixo para cima
    novo_level = 1
    while novo_level < 100 and player.xp_total >= xp_para_nivel(novo_level):
        novo_level += 1

    level_perdido = player.level > novo_level
    player.level  = novo_level
    player.save()

    # Registra o estorno no histórico
    XPEvent.objects.create(
        player    = user,
        fonte     = 'bonus',
        xp_base   = -xp_amount,
        xp_bonus  = 0,
        xp_total  = -xp_amount,
        descricao = descricao or f'Estorno: -{xp_amount} XP (tentativa resetada)',
    )

    if level_perdido:
        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'sistema',
            titulo   = f'Nível ajustado para {novo_level}',
            mensagem = 'Uma tentativa foi resetada pelo administrador.',
            icone    = 'bi-arrow-down-circle-fill',
        )


@transaction.atomic
def revoke_coins(user, coins_amount):
    """Remove coins do player (nunca fica negativo)."""
    player = getattr(user, 'player', None)
    if not player or coins_amount <= 0:
        return
    player.coins = max(0, player.coins - coins_amount)
    player.save()


def get_ofensiva_bonus_pct(user):
    """
    Retorna o % de bônus global vindo da ofensiva do player.
    Respeita o teto da config + extensões de itens/perks.
    """
    player = getattr(user, 'player', None)
    if not player:
        return 0

    config = OfensivaConfig.get()

    # Teto base da config
    teto = config.teto_bonus_ofensiva

    # Extensão de teto via perk (tipo 'ofensiva_teto' — adicionaremos depois)
    teto_extra = get_perk_valor(user, 'ofensiva_teto')
    teto += int(teto_extra)

    # Bônus = 1% por ponto de ofensiva, limitado ao teto
    bonus = min(player.ofensiva, teto)
    return bonus


@transaction.atomic
def registrar_desafio_diario(user):
    """
    Chamado quando o player conclui qualquer desafio no dia.
    - Garante +1 ofensiva apenas uma vez por dia
    - Atualiza streak
    - Retorna dict com o que mudou
    """
    from django.utils import timezone
    from .models import OfensivaConfig

    player = getattr(user, 'player', None)
    if not player:
        return {}

    today = timezone.localdate()

    # Já registrou desafio hoje — não conta novamente
    if player.last_challenge_date == today:
        return {'ja_registrado': True}

    config    = OfensivaConfig.get()
    resultado = {}

    # ── Streak ──────────────────────────────────────────────
    if player.last_challenge_date is None:
        # Primeiro desafio
        player.streak_days = 1
    else:
        dias_passados = (today - player.last_challenge_date).days

        if dias_passados <= config.dias_tolerancia:
            # Dentro da tolerância — mantém/aumenta streak
            player.streak_days += 1
        else:
            # Passou da tolerância — zera streak
            resultado['streak_zerada'] = True
            resultado['streak_anterior'] = player.streak_days
            player.streak_days = 1

    # ── Ofensiva ─────────────────────────────────────────────
    player.ofensiva            += 1
    player.last_challenge_date  = today
    player.last_play_date       = today
    player.save()

    resultado.update({
        'ja_registrado':     False,
        'ofensiva_atual':    player.ofensiva,
        'streak_atual':      player.streak_days,
        'bonus_ofensiva_pct': get_ofensiva_bonus_pct(user),
    })
    return resultado


@transaction.atomic
def verificar_streak_decay(user):
    """
    Verifica se o player perdeu a streak por inatividade.
    Chamado pelo management command diário.
    Retorna True se a streak foi zerada.
    """
    from django.utils import timezone
    from .models import OfensivaConfig, PlayerNotification

    player = getattr(user, 'player', None)
    if not player or not player.last_challenge_date:
        return False

    today         = timezone.localdate()
    dias_passados = (today - player.last_challenge_date).days
    config        = OfensivaConfig.get()

    if dias_passados > config.dias_tolerancia and player.streak_days > 0:
        streak_anterior     = player.streak_days
        player.streak_days  = 0
        player.save()

        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'sistema',
            titulo   = 'Streak perdida!',
            mensagem = (
                f'Sua sequência de {streak_anterior} dia(s) foi zerada '
                f'por {dias_passados} dias de inatividade. Volte a jogar para reconstruir!'
            ),
            icone    = 'bi-exclamation-triangle-fill',
        )
        return True
    return False

# ─────────────────────────────────────────────
# CONQUISTAS
# ─────────────────────────────────────────────

def get_achievement_bonus(user, bonus_type):
    """
    Soma os bônus de conquistas em destaque de um tipo específico.
    Só conta conquistas dentro do limite de destaques.
    """
    from .models import PlayerAchievement, AchievementConfig

    config     = AchievementConfig.get()
    destaques  = (
        PlayerAchievement.objects
        .filter(player=user, em_destaque=True,
                achievement__bonus_type=bonus_type,
                achievement__ativo=True)
        .select_related('achievement')
        [:config.max_destaques]
    )
    return sum(pa.achievement.bonus_value for pa in destaques)


def _auto_gerenciar_destaque(user, nova_conquista_pa):
    """
    Conquistas ganhas entram em destaque automaticamente.
    Se o limite for atingido, a mais antiga sai do destaque.
    """
    from .models import PlayerAchievement, AchievementConfig

    config = AchievementConfig.get()
    destaques_atuais = (
        PlayerAchievement.objects
        .filter(player=user, em_destaque=True)
        .order_by('desbloqueada_em')
    )

    if destaques_atuais.count() >= config.max_destaques:
        # Remove destaque da mais antiga para abrir espaço
        mais_antiga = destaques_atuais.first()
        if mais_antiga and mais_antiga.pk != nova_conquista_pa.pk:
            mais_antiga.em_destaque = False
            mais_antiga.save()


@transaction.atomic
def verificar_conquistas(user, trigger_type, valor_atual=None):
    """
    Verifica e concede conquistas para um trigger específico.
    Chamado após qualquer evento relevante.
    Retorna lista de conquistas desbloqueadas.
    """
    from .models import Achievement, PlayerAchievement, PlayerNotification

    if valor_atual is None:
        valor_atual = _obter_valor_trigger(user, trigger_type)

    conquistas_possiveis = Achievement.objects.filter(
        trigger_type=trigger_type,
        trigger_value__lte=valor_atual,
        ativo=True,
    )

    ja_tem = set(
        PlayerAchievement.objects
        .filter(player=user, achievement__trigger_type=trigger_type)
        .values_list('achievement_id', flat=True)
    )

    novas = []
    for conquista in conquistas_possiveis:
        if conquista.id in ja_tem:
            continue

        pa = PlayerAchievement.objects.create(
            player      = user,
            achievement = conquista,
            em_destaque = True,
        )
        _auto_gerenciar_destaque(user, pa)

        # Notificação
        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'conquista',
            titulo   = f'CONQUISTA — {conquista.nome}',
            mensagem = conquista.descricao,
            icone    = 'bi-trophy-fill',
        )
        novas.append(conquista)

    return novas


def _obter_valor_trigger(user, trigger_type):
    """Busca o valor atual do player para um trigger."""
    from apps.minigames.models import (
        QuizAttempt, DecriptarAttempt, CodigoAttempt,
        PatrolAttempt, PasswordAttempt,
    )
    player = getattr(user, 'player', None)

    mapa = {
        'quiz_count':      lambda: QuizAttempt.objects.filter(
            player=user, completed_at__isnull=False).count(),
        'quiz_perfect':    lambda: QuizAttempt.objects.filter(
            player=user, completed_at__isnull=False,
            xp_earned__gte=1).extra(
            where=['xp_earned >= (SELECT SUM(xp_points) FROM minigames_quizquestion WHERE quiz_id = minigames_quizattempt.quiz_id)']
        ).count() if False else _contar_quiz_perfeito(user),
        'decriptar_count': lambda: DecriptarAttempt.objects.filter(
            player=user, completed_at__isnull=False).count(),
        'codigo_count':    lambda: CodigoAttempt.objects.filter(
            player=user, completed_at__isnull=False).count(),
        'patrol_count':    lambda: PatrolAttempt.objects.filter(
            player=user, completed=True).count(),
        'minigame_count':  lambda: (
            DecriptarAttempt.objects.filter(player=user, completed_at__isnull=False).count() +
            CodigoAttempt.objects.filter(player=user, completed_at__isnull=False).count() +
            PasswordAttempt.objects.filter(player=user, completed_at__isnull=False).count()
        ),
        'all_daily_count': lambda: _contar_dias_completos(user),
        'level_reached':   lambda: player.level if player else 0,
        'streak_days':     lambda: player.streak_days if player else 0,
        'ofensiva':        lambda: player.ofensiva if player else 0,
        'xp_total':        lambda: player.xp_total if player else 0,
        'shop_count':      lambda: _contar_compras(user),
        'feedback_count':  lambda: user.feedbacks.count(),
        'vulnerability':   lambda: user.feedbacks.filter(tipo='vulnerabilidade').count(),
        'season_top1':     lambda: _verificar_ranking(user, 1),
        'season_top3':     lambda: _verificar_ranking(user, 3),
    }

    fn = mapa.get(trigger_type)
    return fn() if fn else 0


def _contar_quiz_perfeito(user):
    from apps.minigames.models import QuizAttempt, QuizQuestion
    from django.db.models import Sum
    count = 0
    for attempt in QuizAttempt.objects.filter(player=user, completed_at__isnull=False):
        max_xp = QuizQuestion.objects.filter(
            quiz=attempt.quiz).aggregate(total=Sum('xp_points'))['total'] or 0
        if max_xp > 0 and attempt.xp_earned >= max_xp:
            count += 1
    return count


def _contar_dias_completos(user):
    """Conta dias em que o player fez TODOS os desafios disponíveis."""
    # Simplificado: dia em que fez pelo menos 3 tipos diferentes de desafio
    from apps.minigames.models import QuizAttempt, DecriptarAttempt, CodigoAttempt
    from django.db.models import DateField
    from django.db.models.functions import TruncDate

    quiz_dias = set(
        QuizAttempt.objects.filter(player=user, completed_at__isnull=False)
        .annotate(d=TruncDate('completed_at'))
        .values_list('d', flat=True)
    )
    dcr_dias = set(
        DecriptarAttempt.objects.filter(player=user, completed_at__isnull=False)
        .values_list('date', flat=True)
    )
    cod_dias = set(
        CodigoAttempt.objects.filter(player=user, completed_at__isnull=False)
        .values_list('date', flat=True)
    )
    dias_completos = quiz_dias & dcr_dias & cod_dias
    return len(dias_completos)


def _contar_compras(user):
    try:
        return user.inventory.count()
    except Exception:
        return 0


def _verificar_ranking(user, top_n):
    from apps.rankings.models import Season, RankingSnapshot
    season = Season.objects.filter(ativa=True).first()
    if not season:
        return 0
    snap = RankingSnapshot.objects.filter(
        season=season, player=user, categoria='xp'
    ).first()
    if snap and snap.posicao <= top_n:
        return 1
    return 0


# ─────────────────────────────────────────────
# BATTLE PASS
# ─────────────────────────────────────────────

@transaction.atomic
def atualizar_battle_pass(user, xp_ganho):
    """
    Chamado automaticamente após grant_xp.
    Atualiza o XP do BP e verifica novos tiers desbloqueados.
    """
    from .models import BattlePassConfig, PlayerBattlePass, PlayerNotification

    bp_config = BattlePassConfig.get_ativo()
    if not bp_config:
        return

    pbp, _ = PlayerBattlePass.objects.get_or_create(
        player=user,
        battle_pass=bp_config,
    )

    pbp.xp_bp += xp_ganho

    # Verifica tiers novos desbloqueados
    tiers_novos = bp_config.tiers.filter(
        xp_necessario__lte=pbp.xp_bp,
        tier__gt=pbp.tier_atual,
    ).order_by('tier')

    if tiers_novos.exists():
        pbp.tier_atual = tiers_novos.last().tier

        # Notifica sobre tiers disponíveis para coleta
        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'sistema',
            titulo   = f'Battle Pass — Tier {pbp.tier_atual} desbloqueado!',
            mensagem = 'Acesse seu perfil para coletar as recompensas.',
            icone    = 'bi-stars',
        )

    pbp.save()


@transaction.atomic
def coletar_recompensa_bp(user, tier_number):
    """
    Player coleta a recompensa de um tier.
    Retorna (sucesso, mensagem, recompensa_descricao).
    """
    from .models import BattlePassConfig, PlayerBattlePass, PlayerNotification
    from apps.store.models import PlayerItem, CoinTransaction

    bp_config = BattlePassConfig.get_ativo()
    if not bp_config:
        return False, 'Nenhum Battle Pass ativo.', None

    try:
        pbp = PlayerBattlePass.objects.get(player=user, battle_pass=bp_config)
    except PlayerBattlePass.DoesNotExist:
        return False, 'Você não iniciou este Battle Pass.', None

    try:
        tier = bp_config.tiers.get(tier=tier_number)
    except BattlePassTier.DoesNotExist:
        return False, 'Tier não encontrado.', None

    if tier.xp_necessario > pbp.xp_bp:
        return False, 'Tier ainda não desbloqueado.', None

    if tier_number in pbp.tiers_coletados:
        return False, 'Recompensa já coletada.', None

    player = getattr(user, 'player', None)

    # ── Entrega a recompensa ──────────────────────
    if tier.recompensa_tipo == 'coins' and player:
        player.coins += tier.recompensa_coins
        player.save()
        CoinTransaction.objects.create(
            player    = user,
            tipo      = 'recompensa',
            valor     = tier.recompensa_coins,
            descricao = f'Battle Pass Tier {tier_number}',
        )

    elif tier.recompensa_tipo in ('item', 'cosmetico') and tier.recompensa_item:
        item = tier.recompensa_item
        pi, created = PlayerItem.objects.get_or_create(
            player=user, item=item,
            defaults={'usos_restantes': item.usos_max or 1}
        )
        if not created:
            pi.quantidade     += 1
            pi.usos_restantes += item.usos_max or 1
            pi.save()

    # ── Registra coleta ───────────────────────────
    coletados = pbp.tiers_coletados
    coletados.append(tier_number)
    pbp.tiers_coletados = coletados
    pbp.save()

    descricao = tier.recompensa_descricao or f'Tier {tier_number}'
    return True, f'Recompensa coletada: {descricao}!', descricao