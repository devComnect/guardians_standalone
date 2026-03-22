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


def calcular_xp_com_bonus(user, xp_base, fonte):
    """
    Aplica perks + bônus de ofensiva ao valor base.
    Retorna (xp_final, xp_bonus).
    """
    bonus_pct = get_perk_valor(user, 'xp_global')

    # Bônus específico por fonte
    mapa_fonte = {
        'quiz':      'xp_quiz',
        'decriptar': 'xp_decriptar',
        'codigo':    'xp_codigo',
        'password':  'xp_password',
    }
    tipo_especifico = mapa_fonte.get(fonte)
    if tipo_especifico:
        bonus_pct += get_perk_valor(user, tipo_especifico)

    # ── Bônus de ofensiva ────────────────────────────────────
    bonus_pct += get_ofensiva_bonus_pct(user)

    xp_bonus = int(xp_base * bonus_pct / 100)
    return xp_base + xp_bonus, xp_bonus


@transaction.atomic
def grant_xp(user, xp_base, fonte, descricao=''):
    """
    Concede XP ao player, aplica perks, verifica level up e cria notificações.
    Retorna dict com resultado.
    """
    from .models import XPEvent, PlayerNotification

    player = getattr(user, 'player', None)
    if not player or xp_base <= 0:
        return {'xp_total': 0, 'level_up': False, 'novo_level': None}

    xp_final, xp_bonus = calcular_xp_com_bonus(user, xp_base, fonte)

    # Registra evento
    XPEvent.objects.create(
        player    = user,
        fonte     = fonte,
        xp_base   = xp_base,
        xp_bonus  = xp_bonus,
        xp_total  = xp_final,
        descricao = descricao or f'+{xp_final} XP via {fonte}',
    )

    # Aplica XP
    player.xp_total += xp_final
    level_antes = player.level

    # Verifica level ups (pode subir vários de uma vez)
    niveis_subidos = []
    while player.xp_total >= xp_para_nivel(player.level):
        player.level += 1
        niveis_subidos.append(player.level)

    player.save()

    # Notificações de level up
    level_up = len(niveis_subidos) > 0
    for nivel in niveis_subidos:
        PlayerNotification.objects.create(
            player   = user,
            tipo     = 'level_up',
            titulo   = f'LEVEL UP — Nível {nivel}!',
            mensagem = f'Parabéns! Você atingiu o nível {nivel}.',
            icone    = 'bi-arrow-up-circle-fill',
        )
        # Verifica perks desbloqueados nesse nível
        _notificar_perks_desbloqueados(user, player.classe, nivel)

    return {
        'xp_base':      xp_base,
        'xp_bonus':     xp_bonus,
        'xp_final':     xp_final,
        'level_up':     level_up,
        'level_antes':  level_antes,
        'novo_level':   player.level if level_up else None,
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
    Troca a classe do player deduzindo coins.
    Retorna (sucesso, mensagem).
    """
    from .models import ClasseConfig, PlayerNotification
    player = getattr(user, 'player', None)
    if not player:
        return False, 'Perfil não encontrado.'

    classes_validas = ['guardian', 'analyst', 'sentinel', 'hacker']
    if nova_classe not in classes_validas:
        return False, 'Classe inválida.'

    if nova_classe == player.classe:
        return False, 'Você já pertence a esta classe.'

    config = ClasseConfig.get()
    if player.coins < config.custo_troca_coins:
        return False, f'Coins insuficientes. Necessário: {config.custo_troca_coins} ⬡'

    classe_antiga = player.get_classe_display()
    player.coins           -= config.custo_troca_coins
    player.classe           = nova_classe
    player.classe_trocada_em = timezone.now()
    player.save()

    PlayerNotification.objects.create(
        player   = user,
        tipo     = 'sistema',
        titulo   = f'Classe alterada para {player.get_classe_display()}',
        mensagem = f'Você deixou os {classe_antiga} e se juntou aos {player.get_classe_display()}.',
        icone    = 'bi-person-badge-fill',
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