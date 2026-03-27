"""
apps/store/services.py
Etapa 9 — Lógica de negócio da Loja

Regras de ouro:
  1. Unique Check: passivo duplicado é bloqueado
  2. Price Modifier: Cartão Clonado (ID 102) aplica 15% de desconto
  3. Atomic Transactions: Coins → Item → Log em uma única transação
  4. Gacha Lite: raridades ponderadas configuráveis via admin
"""

import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import (
    Item, PlayerItem, ActiveEffect,
    DailyStore, StoreConfig, StoreTransaction,
)


# ─────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────

def _tem_cartao_clonado(user):
    """Verifica se o player tem Cartão Clonado (ID 102) em slot ativo."""
    return PlayerItem.objects.filter(
        player=user,
        item__item_id=102,
        slot_index__isnull=False,   # Equipado em algum slot passivo
    ).exists()


def _calcular_preco_final(item, user):
    """
    Retorna (preco_final, desconto_aplicado).
    Desconto de 15% se player tem Cartão Clonado equipado.
    """
    if _tem_cartao_clonado(user):
        desconto = int(item.cost * 0.15)
        return max(0, item.cost - desconto), True
    return item.cost, False


def _slots_passivos_ocupados(user):
    """Retorna dict {slot_index: PlayerItem} dos slots passivos ativos."""
    equipados = PlayerItem.objects.filter(
        player=user,
        item__tipo='passive',
        slot_index__isnull=False,
    ).select_related('item')
    return {pi.slot_index: pi for pi in equipados}


def _proximo_slot_livre(user):
    """Retorna o próximo slot livre (1–4) ou None se todos cheios."""
    config  = StoreConfig.get()
    ocupados = _slots_passivos_ocupados(user)
    for i in range(1, config.max_passivos_slots + 1):
        if i not in ocupados:
            return i
    return None


def _sortear_raridade(config):
    """
    Retorna uma raridade ('COMMON', 'RARE', 'EPIC')
    com base nos pesos configurados no StoreConfig.
    """
    populacao = ['COMMON', 'RARE', 'EPIC']
    pesos     = [config.weight_common, config.weight_rare, config.weight_epic]
    return random.choices(populacao, weights=pesos, k=1)[0]


# ─────────────────────────────────────────────
# GERAÇÃO DA LOJA DIÁRIA
# ─────────────────────────────────────────────

def get_or_generate_daily_store(user):
    """
    Retorna o DailyStore do dia para o player.
    Se não existir, gera lazily na primeira visita.
    Retorna (daily_store, items_qs).
    """
    today = timezone.localdate()
    config = StoreConfig.get()

    daily, criado = DailyStore.objects.get_or_create(
        player=user,
        date=today,
    )

    if criado or daily.items.count() == 0:
        _popular_slots(daily, config, user)

    return daily, daily.items.all()


def _popular_slots(daily_store, config, user):
    """
    Sorteia N itens únicos para os slots do DailyStore.
    Respeita raridades e a temporada ativa.
    """
    from apps.challenges.models import Season

    season_ativa = Season.objects.filter(ativa=True).first()

    # Pool base: itens disponíveis da season ativa + itens eternos
    pool_qs = Item.objects.filter(disponivel=True).filter(
        models.Q(season__isnull=True) |
        models.Q(season=season_ativa)
    ) if season_ativa else Item.objects.filter(disponivel=True, season__isnull=True)

    selecionados = []
    tentativas   = 0

    while len(selecionados) < config.slots_diarios and tentativas < 50:
        tentativas += 1
        raridade = _sortear_raridade(config)
        candidatos = list(pool_qs.filter(raridade=raridade).exclude(
            id__in=[i.id for i in selecionados]
        ))
        if candidatos:
            selecionados.append(random.choice(candidatos))

    # Fallback: completa com qualquer item se não achou suficientes
    if len(selecionados) < config.slots_diarios:
        faltam = config.slots_diarios - len(selecionados)
        extras = list(pool_qs.exclude(
            id__in=[i.id for i in selecionados]
        )[:faltam])
        selecionados.extend(extras)

    daily_store.items.set(selecionados)


# ─────────────────────────────────────────────
# REROLL
# ─────────────────────────────────────────────

@transaction.atomic
def realizar_reroll(user):
    """
    Paga o custo de reroll, regenera os slots do dia.
    Retorna (sucesso, mensagem, daily_store, novo_custo).
    """
    today  = timezone.localdate()
    config = StoreConfig.get()

    daily = DailyStore.objects.filter(player=user, date=today).first()
    if not daily:
        daily = DailyStore.objects.create(player=user, date=today)

    custo = daily.reroll_cost
    player = getattr(user, 'player', None)

    if not player:
        return False, 'Perfil não encontrado.', None, custo

    if player.coins < custo:
        return False, f'Coins insuficientes. Custo: {custo}⬡', daily, custo

    # Debita coins
    player.coins -= custo
    player.save()

    # Registra transação
    StoreTransaction.objects.create(
        player      = user,
        tipo        = 'reroll',
        coins_delta = -custo,
        descricao   = f'Reroll #{daily.reroll_count + 1} da loja',
    )

    # Regenera slots
    daily.reroll_count += 1
    daily.save()
    _popular_slots(daily, config, user)

    proximo_custo = daily.reroll_cost
    return True, f'Loja renovada! Próximo reroll: {proximo_custo}⬡', daily, proximo_custo


# ─────────────────────────────────────────────
# COMPRA
# ─────────────────────────────────────────────

@transaction.atomic
def comprar_item(user, item_id, slot_substituir=None):
    """
    Fluxo de compra atômica.

    Para PASSIVOS:
      - Verifica unique check (não pode ter duplicado equipado)
      - Se slots cheios, exige slot_substituir (int 1–4)
      - Se slot livre, equipa automaticamente

    Para CONSUMÍVEIS:
      - Adiciona ao inventário (quantidade += 1)
      - Respeita limite de max_consumiveis

    Para COSMÉTICOS:
      - Adiciona ao inventário (sem limite de slot)

    Retorna (sucesso, mensagem, contexto_extra).
    """
    try:
        item = Item.objects.get(item_id=item_id, disponivel=True)
    except Item.DoesNotExist:
        return False, 'Item não encontrado ou indisponível.', {}

    player = getattr(user, 'player', None)
    if not player:
        return False, 'Perfil não encontrado.', {}

    preco_final, desconto = _calcular_preco_final(item, user)

    if player.coins < preco_final:
        return False, f'Coins insuficientes. Preço: {preco_final}⬡', {}

    # ── Passivos ─────────────────────────────────────────────
    if item.tipo == 'passive':
        return _comprar_passivo(user, player, item, preco_final, desconto, slot_substituir)

    # ── Consumíveis ──────────────────────────────────────────
    if item.tipo == 'consumable':
        return _comprar_consumivel(user, player, item, preco_final, desconto)

    # ── Cosméticos ───────────────────────────────────────────
    if item.tipo == 'cosmetic':
        return _comprar_cosmetico(user, player, item, preco_final, desconto)

    return False, 'Tipo de item desconhecido.', {}


def _comprar_passivo(user, player, item, preco_final, desconto, slot_substituir):
    config  = StoreConfig.get()
    slots   = _slots_passivos_ocupados(user)

    # Unique check: passivo já equipado?
    if any(pi.item.item_id == item.item_id for pi in slots.values()):
        return False, f'"{item.name}" já está equipado em um slot ativo.', {}

    # Slot livre?
    slot_livre = _proximo_slot_livre(user)

    if slot_livre:
        # Equipa diretamente
        slot_alvo = slot_livre
        substituido = None
    else:
        # Slots cheios — precisa substituir
        if not slot_substituir or slot_substituir not in slots:
            return (
                False,
                'Todos os slots estão cheios. Informe qual slot deseja substituir (1–4).',
                {'slots_cheios': True, 'slots': {k: v.item.item_id for k, v in slots.items()}}
            )
        slot_alvo   = slot_substituir
        substituido = slots[slot_substituir]

        # Remove o item substituído do slot (mantém no inventário sem slot)
        substituido.slot_index = None
        substituido.save()

    # Debita coins
    player.coins -= preco_final
    player.save()

    # Upsert no inventário
    pi, criado = PlayerItem.objects.get_or_create(
        player=user, item=item,
        defaults={'slot_index': slot_alvo}
    )
    if not criado:
        pi.slot_index = slot_alvo
        pi.save()

    # Log
    StoreTransaction.objects.create(
        player             = user,
        item               = item,
        tipo               = 'purchase',
        coins_delta        = -preco_final,
        desconto_aplicado  = desconto,
        descricao          = (
            f'Compra passivo "{item.name}" → slot {slot_alvo}'
            + (f' (substituiu slot {slot_alvo})' if substituido else '')
        ),
    )

    return True, f'"{item.name}" equipado no slot {slot_alvo}!', {
        'slot': slot_alvo,
        'substituido': substituido.item.name if substituido else None,
        'preco_final': preco_final,
        'desconto': desconto,
    }


def _comprar_consumivel(user, player, item, preco_final, desconto):
    config = StoreConfig.get()

    # Conta total de consumíveis no inventário
    total_consumiveis = PlayerItem.objects.filter(
        player=user, item__tipo='consumable'
    ).aggregate(total=models.Sum('quantidade'))['total'] or 0

    if total_consumiveis >= config.max_consumiveis:
        return False, f'Inventário de consumíveis cheio (máx. {config.max_consumiveis}).', {}

    # Debita coins
    player.coins -= preco_final
    player.save()

    # Upsert: se já tem, incrementa quantidade
    pi, criado = PlayerItem.objects.get_or_create(
        player=user, item=item,
        defaults={'quantidade': 1}
    )
    if not criado:
        pi.quantidade += 1
        pi.save()

    StoreTransaction.objects.create(
        player            = user,
        item              = item,
        tipo              = 'purchase',
        coins_delta       = -preco_final,
        desconto_aplicado = desconto,
        descricao         = f'Compra consumível "{item.name}"',
    )

    return True, f'"{item.name}" adicionado ao inventário!', {
        'quantidade': pi.quantidade,
        'preco_final': preco_final,
        'desconto': desconto,
    }


def _comprar_cosmetico(user, player, item, preco_final, desconto):
    # Não pode comprar cosmético que já possui
    if PlayerItem.objects.filter(player=user, item=item).exists():
        return False, f'Você já possui "{item.name}".', {}

    player.coins -= preco_final
    player.save()

    PlayerItem.objects.create(player=user, item=item, quantidade=1)

    StoreTransaction.objects.create(
        player            = user,
        item              = item,
        tipo              = 'purchase',
        coins_delta       = -preco_final,
        desconto_aplicado = desconto,
        descricao         = f'Compra cosmético "{item.name}"',
    )

    return True, f'"{item.name}" desbloqueado!', {
        'preco_final': preco_final,
        'desconto': desconto,
    }


# ─────────────────────────────────────────────
# VENDA DE PASSIVO
# ─────────────────────────────────────────────

@transaction.atomic
def vender_passivo(user, item_id):
    """
    Remove passivo do slot e do inventário.
    Reembolsa 50% do custo original (sem desconto).
    Retorna (sucesso, mensagem, coins_recebidos).
    """
    try:
        pi = PlayerItem.objects.select_related('item').get(
            player=user, item__item_id=item_id, item__tipo='passive'
        )
    except PlayerItem.DoesNotExist:
        return False, 'Item não encontrado no inventário.', 0

    reembolso = pi.item.cost // 2
    player    = getattr(user, 'player', None)

    if player:
        player.coins += reembolso
        player.save()

    StoreTransaction.objects.create(
        player      = user,
        item        = pi.item,
        tipo        = 'sell',
        coins_delta = reembolso,
        descricao   = f'Venda de "{pi.item.name}" (reembolso 50%)',
    )

    nome = pi.item.name
    pi.delete()

    return True, f'"{nome}" vendido por {reembolso}⬡.', reembolso


# ─────────────────────────────────────────────
# ATIVAÇÃO DE CONSUMÍVEIS
# ─────────────────────────────────────────────

@transaction.atomic
def ativar_consumivel(user, item_id):
    """
    Ativa um consumível do inventário.
    Efeitos instantâneos são aplicados imediatamente.
    Efeitos com duração criam um ActiveEffect.
    Retorna (sucesso, mensagem, resultado_extra).
    """
    try:
        pi = PlayerItem.objects.select_related('item').get(
            player=user, item__item_id=item_id, item__tipo='consumable'
        )
    except PlayerItem.DoesNotExist:
        return False, 'Consumível não encontrado no inventário.', {}

    item   = pi.item
    player = getattr(user, 'player', None)
    if not player:
        return False, 'Perfil não encontrado.', {}

    resultado = _aplicar_efeito_consumivel(user, player, item)

    if not resultado.get('sucesso', True):
        return False, resultado.get('mensagem', 'Erro ao aplicar efeito.'), {}

    # Consome 1 unidade
    if pi.quantidade > 1:
        pi.quantidade -= 1
        pi.save()
    else:
        pi.delete()

    StoreTransaction.objects.create(
        player      = user,
        item        = item,
        tipo        = 'activate',
        xp_delta    = resultado.get('xp_delta', 0),
        coins_delta = resultado.get('coins_delta', 0),
        descricao   = f'Ativação de "{item.name}"',
    )

    return True, resultado.get('mensagem', f'"{item.name}" ativado!'), resultado


def _aplicar_efeito_consumivel(user, player, item):
    """
    Despacha para o handler correto baseado em item.effect.
    Retorna dict com resultado da operação.
    """
    effect = item.effect

    # ── Efeitos instantâneos ─────────────────────────────────

    if effect == 'CONVERT_GOLD_XP':
        # Script de Arbitragem: 100 Coins → 150 XP
        custo_coins = int(item.value_secondary) if item.value_secondary else 100
        xp_ganho    = int(item.value)
        if player.coins < custo_coins:
            return {'sucesso': False, 'mensagem': f'Coins insuficientes (necessário: {custo_coins}⬡)'}
        player.coins -= custo_coins
        player.save()
        from apps.profiles.services import grant_xp
        grant_xp(user, xp_ganho, 'bonus', f'Script de Arbitragem: {custo_coins}⬡ → {xp_ganho}XP')
        return {
            'mensagem':    f'+{xp_ganho} XP concedidos!',
            'xp_delta':    xp_ganho,
            'coins_delta': -custo_coins,
        }

    if effect == 'CONVERT_XP_GOLD':
        # Monetizador de Expertise: 500 XP → 80 Coins
        xp_custo    = int(item.value_secondary) if item.value_secondary else 500
        coins_ganho = int(item.value)
        if player.xp_total < xp_custo:
            return {'sucesso': False, 'mensagem': f'XP insuficiente (necessário: {xp_custo}XP)'}
        from apps.profiles.services import revoke_xp
        revoke_xp(user, xp_custo, f'Monetizador de Expertise: -{xp_custo}XP → {coins_ganho}⬡')
        player.refresh_from_db()
        player.coins += coins_ganho
        player.save()
        return {
            'mensagem':    f'+{coins_ganho}⬡ recebidos!',
            'xp_delta':    -xp_custo,
            'coins_delta': coins_ganho,
        }

    # ── Efeitos com duração — criam ActiveEffect ─────────────

    efeitos_com_duracao = {
        'XP_BOOST_DAYS',
        'STREAK_CAP_BOOST',
        'STREAK_FREEZE',
        'EXTRA_LIFE_TIME',
    }

    if effect in efeitos_com_duracao:
        duracao = item.duration_days or 1
        expires = timezone.now() + timedelta(days=duracao)

        # Não empilha: se já existe efeito igual, estende
        ae, criado = ActiveEffect.objects.get_or_create(
            player=user, item=item, effect=effect,
            defaults={'value': item.value, 'expires_at': expires}
        )
        if not criado:
            ae.expires_at = max(ae.expires_at, expires)
            ae.save()

        labels = {
            'XP_BOOST_DAYS':    f'+{int(item.value)}% XP por {duracao} dia(s)',
            'STREAK_CAP_BOOST': f'+{int(item.value)} no teto da ofensiva por {duracao} dia(s)',
            'STREAK_FREEZE':    f'Streak protegida por {duracao} dia(s)',
            'EXTRA_LIFE_TIME':  f'+{int(item.value)}s e +1 vida no próximo desafio',
        }
        return {'mensagem': labels.get(effect, f'Efeito ativo por {duracao} dia(s)!')}

    # ── TOKEN_RETAKE — marca flag no player ──────────────────
    if effect == 'TOKEN_RETAKE':
        # Usa um campo auxiliar via ActiveEffect sem duração fixa
        expires = timezone.now() + timedelta(days=30)  # 30 dias para usar
        ActiveEffect.objects.get_or_create(
            player=user, item=item, effect='TOKEN_RETAKE',
            defaults={'value': 1, 'expires_at': expires}
        )
        return {'mensagem': 'Token de refação guardado! Use antes de iniciar um desafio.'}

    # ── FREE_HINT ────────────────────────────────────────────
    if effect == 'FREE_HINT':
        expires = timezone.now() + timedelta(days=7)
        ActiveEffect.objects.get_or_create(
            player=user, item=item, effect='FREE_HINT',
            defaults={'value': 1, 'expires_at': expires}
        )
        return {'mensagem': 'Dica grátis ativa para o próximo desafio!'}

    return {'mensagem': f'"{item.name}" ativado com sucesso!'}


# ─────────────────────────────────────────────
# BÔNUS DE PASSIVOS (integração com grant_xp)
# ─────────────────────────────────────────────

def get_passive_bonus_xp_pct(user, fonte=None, contexto=None):
    if contexto is None:
        contexto = {}

    print(f"\n{'─'*60}")
    print(f"[PASSIVO DEBUG] Calculando passivos para: {user.username}")
    print(f"[PASSIVO DEBUG] Fonte: {fonte} | Contexto: {contexto}")
    print(f"{'─'*60}")

    passivos = PlayerItem.objects.filter(
        player=user,
        item__tipo='passive',
        slot_index__isnull=False,
    ).select_related('item')

    if not passivos.exists():
        print(f"[PASSIVO DEBUG] Nenhum passivo equipado — bônus = 0%")
        print(f"{'─'*60}")
        return 0

    print(f"[PASSIVO DEBUG] Passivos equipados ({passivos.count()}):")
    for pi in passivos:
        print(f"  • Slot {pi.slot_index}: [{pi.item.raridade}] {pi.item.nome} — effect: {pi.item.effect}")

    player = getattr(user, 'player', None)
    if not player:
        print(f"[PASSIVO DEBUG] Player não encontrado — bônus = 0%")
        print(f"{'─'*60}")
        return 0

    print(f"[PASSIVO DEBUG] Player coins: {player.coins} | Level: {player.level}")
    print(f"{'─'*60}")

    bonus_total = 0.0
    valores_bonus = []

    for pi in passivos:
        item   = pi.item
        effect = item.effect
        b      = 0.0
        motivo = ''

        # ── Economy ──────────────────────────────────────────
        if effect == 'XP_PER_COIN':
            b = min((player.coins // 10) * item.value, item.max_bonus)
            motivo = f"{player.coins} coins → {player.coins // 10} grupos de 10 × {item.value}% (max {item.max_bonus}%)"

        elif effect == 'XP_LOW_CASH':
            if player.coins < 10:
                b = item.value
                motivo = f"coins ({player.coins}) < 10 ✅"
            else:
                motivo = f"coins ({player.coins}) >= 10 ❌ não ativou"

        elif effect == 'XP_ODD_CASH':
            if player.coins % 2 != 0:
                b = item.value
                motivo = f"coins ({player.coins}) é ímpar ✅"
            else:
                motivo = f"coins ({player.coins}) é par ❌ não ativou"

        # ── Speedrun ─────────────────────────────────────────
        elif effect == 'TIME_REDUCTION_XP_BOOST':
            b = item.value_secondary if item.value_secondary else item.value
            motivo = f"sempre ativo → value_secondary={item.value_secondary} / value={item.value}"

        elif effect == 'XP_PER_SECOND':
            seg = contexto.get('segundos_restantes', 0)
            b   = min(seg * item.value, item.max_bonus)
            motivo = f"{seg}s restantes × {item.value}% = {seg * item.value}% (max {item.max_bonus}%)"

        # ── Skill ─────────────────────────────────────────────
        elif effect == 'XP_QUICK_WIN':
            tentativas = contexto.get('tentativas', 99)
            won        = contexto.get('won', False)
            if tentativas < 3 and won:
                b = item.value
                motivo = f"tentativas={tentativas} < 3 e won={won} ✅"
            else:
                motivo = f"tentativas={tentativas}, won={won} ❌ não ativou (precisa: tentativas<3 e won=True)"

        # ── Synergy ──────────────────────────────────────────
        elif effect == 'XP_SAME_RARITY':
            raridades = [p.item.raridade for p in passivos]
            if len(set(raridades)) == 1 and len(raridades) == 4:
                b = item.value
                motivo = f"4 passivos da mesma raridade ({raridades[0]}) ✅"
            else:
                motivo = f"raridades={raridades} ❌ não ativou (precisa 4 iguais)"

        elif effect == 'XP_PER_COMMON':
            commons = sum(1 for p in passivos if p.item.raridade == 'COMMON')
            b       = min(commons * item.value, item.max_bonus)
            motivo  = f"{commons} comuns × {item.value}% = {commons * item.value}% (max {item.max_bonus}%)"

        elif effect == 'XP_PER_EMPTY_SLOT':
            config = StoreConfig.get()
            vazios = config.max_passivos_slots - passivos.count()
            b      = min(vazios * item.value, item.max_bonus)
            motivo = f"{vazios} slots vazios × {item.value}% = {vazios * item.value}% (max {item.max_bonus}%)"

        # ── Buff ─────────────────────────────────────────────
        elif effect == 'XP_STACK_MULTIPLIER':
            valores_bonus.append(('multiplier', item.value))
            print(f"  [{effect}] {item.nome} → guardado para aplicar no final (×{item.value}%)")
            continue

        # ── Social ───────────────────────────────────────────
        elif effect == 'XP_PER_COSMETIC':
            cosmeticos = PlayerItem.objects.filter(
                player=user, item__tipo='cosmetic', equipado=True
            ).count()
            b      = min(cosmeticos * item.value, item.max_bonus)
            motivo = f"{cosmeticos} cosméticos equipados × {item.value}% (max {item.max_bonus}%)"

        elif effect == 'XP_PER_FEATURED_ACHIEVEMENT':
            from apps.profiles.models import PlayerAchievement
            destaques = PlayerAchievement.objects.filter(player=user, em_destaque=True).count()
            b         = min(destaques * item.value, item.max_bonus)
            motivo    = f"{destaques} conquistas em destaque × {item.value}% (max {item.max_bonus}%)"

        # ── Ranking ──────────────────────────────────────────
        elif effect == 'XP_TOP_3':
            from apps.profiles.services import _verificar_ranking
            if _verificar_ranking(user, 3):
                b = item.value
                motivo = f"player está no top 3 ✅"
            else:
                motivo = f"player fora do top 3 ❌ não ativou"

        elif effect == 'XP_OUTSIDE_TOP_10':
            from apps.profiles.services import _verificar_ranking
            if not _verificar_ranking(user, 10):
                b = item.value
                motivo = f"player fora do top 10 ✅"
            else:
                motivo = f"player está no top 10 ❌ não ativou"

        # ── Scaling ──────────────────────────────────────────
        elif effect == 'XP_PER_LEVEL':
            b      = min(player.level * item.value, item.max_bonus)
            motivo = f"level {player.level} × {item.value}% = {player.level * item.value}% (max {item.max_bonus}%)"

        # ── Specific ─────────────────────────────────────────
        elif effect == 'XP_CODE_CHALLENGE' and fonte == 'codigo':
            b      = item.value
            motivo = f"fonte=codigo ✅"
        elif effect == 'XP_PATROL_CHALLENGE' and fonte == 'patrol':
            b      = item.value
            motivo = f"fonte=patrol ✅"
        elif effect == 'XP_DECRYPT_CHALLENGE' and fonte == 'decriptar':
            b      = item.value
            motivo = f"fonte=decriptar ✅"
        elif effect in ('XP_CODE_CHALLENGE', 'XP_PATROL_CHALLENGE', 'XP_DECRYPT_CHALLENGE'):
            motivo = f"fonte='{fonte}' ❌ não é a fonte correta para esse item"

        # ── Luck ─────────────────────────────────────────────
        elif effect == 'XP_RANDOM':
            import random
            b      = random.uniform(item.value, item.max_bonus)
            motivo = f"sorteio entre {item.value}% e {item.max_bonus}% → {b:.2f}%"

        # ── Time ─────────────────────────────────────────────
        elif effect == 'DOUBLE_XP_WEEK_FIRST':
            if _e_primeiro_desafio_da_semana(user):
                b = item.value
                motivo = f"primeiro desafio da semana ✅"
            else:
                motivo = f"não é o primeiro desafio da semana ❌ não ativou"

        else:
            motivo = f"effect '{effect}' não reconhecido"

        status = f"+{b}%" if b > 0 else "0% (inativo)"
        print(f"  [{effect}] {item.nome} → {status}")
        if motivo:
            print(f"    └─ {motivo}")

        bonus_total += b

    # ── XP_STACK_MULTIPLIER ───────────────────────────────────
    if valores_bonus:
        bonus_antes = bonus_total
        for tipo, val in valores_bonus:
            if tipo == 'multiplier':
                acrescimo = bonus_total * (val / 100)
                bonus_total += acrescimo
                print(f"  [XP_STACK_MULTIPLIER] ×{val}% sobre {bonus_antes}% → +{acrescimo:.2f}% (total agora: {bonus_total:.2f}%)")

    # ── Consumíveis ───────────────────────────────────────────
    bonus_consumivel = _get_consumivel_xp_bonus(user)
    if bonus_consumivel > 0:
        print(f"  [CONSUMIVEL] XP_BOOST_DAYS ativo → +{bonus_consumivel}%")
    else:
        print(f"  [CONSUMIVEL] Nenhum consumível de XP ativo")
    bonus_total += bonus_consumivel

    print(f"{'─'*60}")
    print(f"[PASSIVO DEBUG] Bônus total de passivos+consumíveis: +{round(bonus_total, 2)}%")
    print(f"{'─'*60}\n")

    return round(bonus_total, 2)


def _get_consumivel_xp_bonus(user):
    """Soma % de XP de consumíveis ativos com duração."""
    agora = timezone.now()
    efeitos = ActiveEffect.objects.filter(
        player=user,
        effect='XP_BOOST_DAYS',
        expires_at__gt=agora,
    )
    return sum(e.value for e in efeitos)


def _e_primeiro_desafio_da_semana(user):
    """Verifica se o player ainda não fez nenhum desafio essa semana."""
    from apps.profiles.models import XPEvent
    hoje      = timezone.localdate()
    inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda-feira
    return not XPEvent.objects.filter(
        player=user,
        criado_em__date__gte=inicio_semana,
    ).exists()


def get_tempo_extra_passivo(user):
    """
    Retorna segundos extras de tempo vindos de passivos (ADD_TIME)
    e consumíveis ativos (EXTRA_LIFE_TIME).
    Chamado pelo minigame antes de iniciar o desafio.
    """
    passivos = PlayerItem.objects.filter(
        player=user,
        item__tipo='passive',
        item__effect='ADD_TIME',
        slot_index__isnull=False,
    )
    tempo_extra = sum(p.item.value for p in passivos)

    # Consumível EXTRA_LIFE_TIME
    agora   = timezone.now()
    efeitos = ActiveEffect.objects.filter(
        player=user, effect='EXTRA_LIFE_TIME', expires_at__gt=agora
    )
    tempo_extra += sum(e.value for e in efeitos)

    return int(tempo_extra)


def get_vidas_extras(user):
    """Retorna +N vidas vindas do consumível EXTRA_LIFE_TIME ativo."""
    agora = timezone.now()
    return ActiveEffect.objects.filter(
        player=user, effect='EXTRA_LIFE_TIME', expires_at__gt=agora
    ).count()


def consumir_efeito_unico(user, effect_type):
    """
    Remove o primeiro ActiveEffect do tipo (para efeitos de 1 uso como FREE_HINT, TOKEN_RETAKE).
    Retorna True se existia e foi consumido.
    """
    ae = ActiveEffect.objects.filter(
        player=user, effect=effect_type, expires_at__gt=timezone.now()
    ).first()
    if ae:
        ae.delete()
        return True
    return False


def tem_efeito_ativo(user, effect_type):
    """Verifica se o player tem um ActiveEffect ativo do tipo informado."""
    return ActiveEffect.objects.filter(
        player=user, effect=effect_type, expires_at__gt=timezone.now()
    ).exists()


# ─────────────────────────────────────────────
# COSMÉTICOS
# ─────────────────────────────────────────────

@transaction.atomic
def equipar_cosmético(user, item_id):
    """
    Equipa um cosmético (desequipa o anterior da mesma categoria).
    Retorna (sucesso, mensagem).
    """
    try:
        pi = PlayerItem.objects.select_related('item').get(
            player=user, item__item_id=item_id, item__tipo='cosmetic'
        )
    except PlayerItem.DoesNotExist:
        return False, 'Cosmético não encontrado no inventário.'

    # Desequipa outros do mesmo effect (mesma categoria)
    PlayerItem.objects.filter(
        player=user,
        item__tipo='cosmetic',
        item__effect=pi.item.effect,
        equipado=True,
    ).exclude(pk=pi.pk).update(equipado=False)

    pi.equipado = True
    pi.save()

    return True, f'"{pi.item.name}" equipado!'


@transaction.atomic
def desequipar_cosmético(user, item_id):
    try:
        pi = PlayerItem.objects.get(
            player=user, item__item_id=item_id, item__tipo='cosmetic'
        )
    except PlayerItem.DoesNotExist:
        return False, 'Cosmético não encontrado.'

    pi.equipado = False
    pi.save()
    return True, f'"{pi.item.name}" desequipado.'


def get_cosmeticos_equipados(user):
    """Retorna dict {effect: item} dos cosméticos ativos do player."""
    equipados = PlayerItem.objects.filter(
        player=user, item__tipo='cosmetic', equipado=True
    ).select_related('item')
    return {pi.item.effect: pi.item for pi in equipados}


# ─────────────────────────────────────────────
# DADOS DO INVENTÁRIO PARA VIEWS
# ─────────────────────────────────────────────

def get_inventario_completo(user):
    """
    Retorna estrutura organizada do inventário para a view de perfil/loja.
    """
    config  = StoreConfig.get()
    passivos = {i: None for i in range(1, config.max_passivos_slots + 1)}

    passivos_equipados = PlayerItem.objects.filter(
        player=user, item__tipo='passive', slot_index__isnull=False
    ).select_related('item')

    for pi in passivos_equipados:
        passivos[pi.slot_index] = pi

    consumiveis = PlayerItem.objects.filter(
        player=user, item__tipo='consumable'
    ).select_related('item')

    cosmeticos = PlayerItem.objects.filter(
        player=user, item__tipo='cosmetic'
    ).select_related('item').order_by('item__effect', '-adquirido_em')

    efeitos_ativos = ActiveEffect.objects.filter(
        player=user, expires_at__gt=timezone.now()
    ).select_related('item')

    return {
        'passivos':        passivos,           # {slot: PlayerItem|None}
        'consumiveis':     list(consumiveis),
        'cosmeticos':      list(cosmeticos),
        'efeitos_ativos':  list(efeitos_ativos),
        'config':          config,
    }