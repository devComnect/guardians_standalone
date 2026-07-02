"""
apps/store/services.py
Etapa 9 — Lógica de negócio da Loja

Regras de ouro:
  1. Unique Check: passivo duplicado é bloqueado
  2. Price Modifier: Cartão Clonado (ID 102) aplica x% de desconto
  3. Atomic Transactions: Coins → Item → Log em uma única transação
  4. Gacha Lite: raridades ponderadas configuráveis via admin
"""

import random
from datetime import timedelta
from django.db.models import Q, Sum
from django.db import transaction
from django.utils import timezone

from .models import (
    Item, PlayerItem, ActiveEffect,
    DailyStore, StoreConfig, StoreTransaction,
)

# Consumíveis que usam ActiveEffect com duração — não podem ser stackados
_EFEITOS_NAO_STACKAVEIS = {
    'XP_BOOST_DAYS',
    'STREAK_CAP_BOOST',
    'STREAK_FREEZE',
    'EXTRA_LIFE_TIME',
    'TOKEN_RETAKE',
    'FREE_HINT',
}
 
# Tabela de drop do Pacote de Cargas: item_id → peso relativo por raridade
_LOOT_PACK_POOL = [
    # (item_id, raridade)      peso
    (1,  'COMMON'),   # Backup de Memória
    (2,  'RARE'),   # Injetor de Overclock
    (5,  'COMMON'),   # Sniffer de Metadados
    (6,  'COMMON'),     # Buffer de Contingência
    (3,  'RARE'),     # Expansor de Cache
    (4,  'RARE'),     # Protocolo Persistência
    (7,  'EPIC'),     # Script de Arbitragem
    (8,  'EPIC'),     # Monetizador de Expertise
]
 
_LOOT_PESOS = {
    'COMMON': 60,
    'RARE':   30,
    'EPIC':   10,
}


# ─────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────

def _calcular_preco_final(item, user):
    """Aplica desconto de item (Cartão Clonado) e perk de classe (shop_discount), somados."""
    from apps.profiles.services import get_perk_valor

    pct_total = 0
    tem_desconto = False

    player_item = PlayerItem.objects.filter(
        player=user,
        item__item_id=102,
        slot_index__isnull=False,
    ).select_related('item').first()

    if player_item:
        pct_total += player_item.item.value
        tem_desconto = True

    pct_perk = get_perk_valor(user, 'shop_discount')
    if pct_perk:
        pct_total += pct_perk
        tem_desconto = True

    if not tem_desconto:
        return item.cost, False

    desconto = int(item.cost * pct_total / 100)
    return max(0, item.cost - desconto), True


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
    Retorna uma raridade ('COMMON', 'RARE', 'EPIC', 'LEGENDARY')
    com base nos pesos configurados no StoreConfig.
    """
    populacao = ['COMMON', 'RARE', 'EPIC', 'LEGENDARY']
    pesos     = [config.weight_common, config.weight_rare, config.weight_epic, config.weight_legendary]
    return random.choices(populacao, weights=pesos, k=1)[0]

def _is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def _e_primeiro_desafio_da_semana(user):
    from apps.profiles.models import XPEvent
    from django.utils import timezone
    from datetime import timedelta

    hoje = timezone.localdate()
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    return not XPEvent.objects.filter(
        player=user,
        fonte__in=['quiz', 'codigo', 'decriptar', 'password', 'logscan'],
        criado_em__date__gte=inicio_semana,
    ).exists()

def _e_primeiro_desafio_do_dia(user):
    from apps.profiles.models import XPEvent
    from django.utils import timezone

    hoje = timezone.localdate()
    inicio_hoje = timezone.make_aware(
        timezone.datetime(hoje.year, hoje.month, hoje.day)
    )

    return not XPEvent.objects.filter(
        player=user,
        fonte__in=['quiz', 'codigo', 'decriptar', 'password', 'logscan'],
        criado_em__gte=inicio_hoje,
    ).exists()

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
    pool_qs = Item.objects.filter(disponivel=True).exclude(tipo='cosmetic').filter(
        Q(season__isnull=True) |
        Q(season=season_ativa)
    ) if season_ativa else Item.objects.filter(disponivel=True, season__isnull=True).exclude(tipo='cosmetic')

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
            f'Compra passivo "{item.name}"'
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
    ).aggregate(total=Sum('quantidade'))['total'] or 0

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

    today = timezone.localdate()
    daily = DailyStore.objects.filter(player=user, date=today).first()
    if daily:
        daily.items.remove(item)

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
    try:
        pi = PlayerItem.objects.select_related('item').get(
            player=user, item__item_id=item_id, item__tipo='passive'
        )
    except PlayerItem.DoesNotExist:
        return False, 'Item não encontrado no inventário.', 0

    reembolso = pi.item.cost // 2
    nome      = pi.item.name

    from apps.profiles.services import grant_coins
    grant_coins(user, reembolso, fonte='venda', aplicar_bonus=False)

    StoreTransaction.objects.create(
        player      = user,
        item        = pi.item,
        tipo        = 'sell',
        coins_delta = reembolso,
        descricao   = f'Venda de "{nome}" (reembolso 50%)',
    )

    pi.delete()

    return True, f'"{nome}" vendido por {reembolso}⬡.', reembolso


# ─────────────────────────────────────────────
# ATIVAÇÃO DE CONSUMÍVEIS
# ─────────────────────────────────────────────

@transaction.atomic
def ativar_consumivel(user, item_id):
    """
    Ativa um consumível do inventário.
    - Bloqueia reativação de efeitos não-stackáveis já ativos.
    - Efeitos instantâneos são aplicados imediatamente.
    - Efeitos com duração criam um ActiveEffect.
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
 
    # ── Stack check: bloqueia se efeito não-stackável já está ativo ──────────
    if item.effect in _EFEITOS_NAO_STACKAVEIS:
        ja_ativo = ActiveEffect.objects.filter(
            player=user,
            effect=item.effect,
            expires_at__gt=timezone.now(),
        ).exists()
        if ja_ativo:
            return (
                False,
                f'"{item.name}" já está ativo. Aguarde expirar antes de usar outro.',
                {},
            )
 
    resultado = _aplicar_efeito_consumivel(user, player, item)
 
    if not resultado.get('sucesso', True):
        return False, resultado.get('mensagem', 'Erro ao aplicar efeito.'), {}
 
    if pi.quantidade > 1:
        pi.quantidade -= 1
        pi.save()
    else:
        pi.delete()

    descricao_log = resultado.get('descricao_log', f'Ativou a carga "{item.name}".')

    StoreTransaction.objects.create(
        player      = user,
        item        = item,
        tipo        = 'activate',
        xp_delta    = resultado.get('xp_delta', 0),
        coins_delta = resultado.get('coins_delta', 0),
        descricao   = descricao_log,
    )

    return True, resultado.get('mensagem', f'"{item.name}" ativado!'), resultado


def _sortear_item_loot_pack():
    """
    Sorteia 1 item_id do pool do Pacote de Cargas usando pesos por raridade.
    Retorna o item_id sorteado.
    """
    pool_ids      = [entry[0] for entry in _LOOT_PACK_POOL]
    pool_raridades = [entry[1] for entry in _LOOT_PACK_POOL]
    pesos         = [_LOOT_PESOS[r] for r in pool_raridades]
    sorteado      = random.choices(pool_ids, weights=pesos, k=1)[0]
    return sorteado
 

def _aplicar_efeito_consumivel(user, player, item):
    """
    Despacha para o handler correto baseado em item.effect.
    Retorna dict com resultado da operação.
    """
    effect = item.effect
 
    # ── LOOT_PACK — Pacote de Cargas ─────────────────────────
    if effect == 'LOOT_PACK':
        config = StoreConfig.get()
 
        total_consumiveis = PlayerItem.objects.filter(
            player=user, item__tipo='consumable'
        ).aggregate(total=Sum('quantidade'))['total'] or 0
 
        if total_consumiveis >= config.max_consumiveis:
            return {
                'sucesso': False,
                'mensagem': f'Inventário cheio (máx. {config.max_consumiveis}). Libere espaço antes de abrir o pacote.',
            }
 
        item_id_dropado = _sortear_item_loot_pack()
 
        try:
            item_dropado = Item.objects.get(item_id=item_id_dropado)
        except Item.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Erro interno: item sorteado não encontrado.'}
 
        pi_drop, criado = PlayerItem.objects.get_or_create(
            player=user,
            item=item_dropado,
            defaults={'quantidade': 1},
        )
        if not criado:
            pi_drop.quantidade += 1
            pi_drop.save()

        return {
            'sucesso': True,
            'mensagem': f'Pacote aberto! Você recebeu: {item_dropado.name} ({item_dropado.get_raridade_display()})',
            'descricao_log': f'Abriu "{item.name}" e ganhou {item_dropado.name}.', 
            'item_dropado_id': item_dropado.item_id,
            'item_dropado_nome': item_dropado.name,
            'item_dropado_raridade': item_dropado.raridade,
            'item_dropado_icon': item_dropado.icon,
        }
  
    # ── Efeitos instantâneos ─────────────────────────────────

    if effect == 'CONVERT_GOLD_XP':
        custo_coins = int(item.value_secondary) if item.value_secondary else 100
        xp_ganho_base = int(item.value)

        # 1. Trava de Segurança
        if player.coins < custo_coins:
            return {'sucesso': False, 'mensagem': f'Coins insuficientes. Você precisa de {custo_coins}⬡ para esta transação.'}

        from apps.profiles.services import grant_xp
        
        # Deduz os coins
        player.coins -= custo_coins
        player.save()

        resultado_xp = grant_xp(user, xp_ganho_base, 'store', f'Script de Arbitragem: {custo_coins}⬡ → XP')
        
        xp_final = resultado_xp.get('xp_final', xp_ganho_base)

        return {
            'sucesso': True,
            'mensagem': f'Sucesso! {custo_coins}⬡ convertidos em +{xp_final} XP (bônus aplicados).',
            'xp_delta': xp_final,
            'coins_delta': -custo_coins,
        }

    if effect == 'CONVERT_XP_GOLD':
        xp_custo        = int(item.value_secondary) if item.value_secondary else 500
        coins_ganho_base = int(item.value)

        if player.xp_total < xp_custo:
            return {'sucesso': False, 'mensagem': f'XP insuficiente. Você precisa de {xp_custo} XP.'}

        from apps.profiles.services import revoke_xp, grant_coins

        revoke_xp(user, xp_custo, f'Monetizador de Expertise: -{xp_custo} XP → Coins', fonte='item')
        player.refresh_from_db()

        coin_result  = grant_coins(user, coins_ganho_base, 'consumivel')  # bonus aplicado
        coins_final  = coin_result['final']

        return {
            'sucesso':     True,
            'mensagem':    f'Sucesso! {xp_custo} XP convertidos em +{coins_final}⬡ (bônus aplicados).',
            'xp_delta':    -xp_custo,
            'coins_delta': coins_final,
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
 
        # Stack check já foi feito em ativar_consumivel — aqui só cria
        ActiveEffect.objects.create(
            player=user,
            item=item,
            effect=effect,
            value=item.value,
            expires_at=expires,
        )
 
        labels = {
            'XP_BOOST_DAYS':    f'+{int(item.value)}% XP por {duracao} dia(s).',
            'STREAK_CAP_BOOST': f'+{int(item.value)} no teto da ofensiva por {duracao} dia(s).',
            'STREAK_FREEZE':    f'Streak protegida por {duracao} dia(s).',
            'EXTRA_LIFE_TIME':  f'+{int(item.value)}s e +1 vida no próximo desafio.',
        }
        return {'mensagem': labels.get(effect, f'Efeito ativo por {duracao} dia(s)!')}
 
    # ── TOKEN_RETAKE ──────────────────────────────────────────
    if effect == 'TOKEN_RETAKE':
        expires = timezone.now() + timedelta(days=30)
        ActiveEffect.objects.create(
            player=user,
            item=item,
            effect='TOKEN_RETAKE',
            value=1,
            expires_at=expires,
        )
        return {'mensagem': 'Token de refação guardado! Disponível nos próximos desafios.'}
 
    # ── FREE_HINT ─────────────────────────────────────────────
    if effect == 'FREE_HINT':
        expires = timezone.now() + timedelta(days=7)
        ActiveEffect.objects.create(
            player=user,
            item=item,
            effect='FREE_HINT',
            value=1,
            expires_at=expires,
        )
        return {'mensagem': 'Dica grátis ativa para o próximo desafio! (sem penalidade de tempo)'}
 
    return {'mensagem': f'"{item.name}" ativado com sucesso!'}


# ─────────────────────────────────────────────
# BÔNUS DE PASSIVOS (integração com grant_xp)
# ─────────────────────────────────────────────

def get_passive_bonus_xp_pct(user, fonte=None, contexto=None, retornar_breakdown=False):
    if contexto is None:
        contexto = {}

    player = getattr(user, 'player', None)
    if not player:
        return (0, []) if retornar_breakdown else 0

    passivos = PlayerItem.objects.filter(
        player=user,
        item__tipo='passive',
        slot_index__isnull=False,
    ).select_related('item')

    bonus_total  = 0.0
    breakdown    = []
    multiplicadores = []

    # Se houver passivos, processa-os normalmente. Caso contrário, pula para os consumíveis.
    for pi in passivos:
        item   = pi.item
        effect = item.effect
        b      = 0.0
        motivo = ''

        if effect == 'XP_PER_COIN':
            raw    = (player.coins // 10) * item.value
            b      = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo = f"{player.coins} coins → {player.coins // 10} grupos × {item.value}% = {b}%"

        elif effect == 'XP_LOW_CASH':
            if player.coins < 10:
                b      = item.value
                motivo = f"coins ({player.coins}) < 10 ✅"
            else:
                motivo = f"coins ({player.coins}) >= 10 ❌"

        elif effect == 'XP_ODD_CASH':
            if player.coins % 2 != 0:
                b      = item.value
                motivo = f"coins ({player.coins}) é ímpar ✅"
            else:
                motivo = f"coins ({player.coins}) é par ❌"

        elif effect == 'TIME_REDUCTION_XP_BOOST':
            b      = item.value_secondary if item.value_secondary else item.value
            motivo = f"sempre ativo"

        elif effect == 'XP_PER_SECOND':
            seg    = contexto.get('segundos_restantes', 0)
            raw    = seg * item.value
            b      = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo = f"{seg}s restantes × {item.value}% = {b}%"

        elif effect == 'XP_QUICK_WIN':
            if fonte == 'quiz':
                motivo = "não se aplica a quiz ❌"
            else:
                tentativas = contexto.get('tentativas', 99)
                won        = contexto.get('won', False)
                if tentativas < 3 and won:
                    b      = item.value
                    motivo = f"vitória em {tentativas} tentativas ✅"
                else:
                    motivo = f"tentativas={tentativas}, won={won} ❌"

        elif effect == 'XP_SAME_RARITY':
            raridades = [p.item.raridade for p in passivos]
            if len(set(raridades)) == 1 and len(raridades) == 4:
                b      = item.value
                motivo = f"4 passivos {raridades[0]} ✅"
            else:
                motivo = f"raridades mistas ❌"

        elif effect == 'XP_PER_COMMON':
            commons = sum(1 for p in passivos if p.item.raridade == 'COMMON')
            raw     = commons * item.value
            b       = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo  = f"{commons} comuns × {item.value}% = {b}%"

        elif effect == 'XP_PER_EMPTY_SLOT':
            config = StoreConfig.get()
            vazios = config.max_passivos_slots - passivos.count()
            raw    = vazios * item.value
            b      = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo = f"{vazios} slots vazios × {item.value}% = {b}%"

        elif effect == 'XP_STACK_MULTIPLIER':
            multiplicadores.append(item)
            continue

        elif effect == 'XP_PER_COSMETIC':
            cosmeticos = PlayerItem.objects.filter(
                player=user, item__tipo='cosmetic', equipado=True
            ).count()
            raw    = cosmeticos * item.value
            b      = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo = f"{cosmeticos} cosméticos × {item.value}% = {b}%"

        elif effect == 'XP_PER_FEATURED_ACHIEVEMENT':
            from apps.profiles.models import PlayerAchievement
            destaques = PlayerAchievement.objects.filter(player=user, em_destaque=True).count()
            raw       = destaques * item.value
            b         = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo    = f"{destaques} conquistas em destaque × {item.value}% = {b}%"

        elif effect == 'XP_TOP_3':
            from apps.profiles.services import _verificar_ranking
            resultado = _verificar_ranking(user, 3)
            if resultado is True:
                b      = item.value
                motivo = "top 3 ✅"
            elif resultado is None:
                motivo = "sem snapshot de ranking ❌"
            else:
                motivo = "fora do top 3 ❌"

        elif effect == 'XP_OUTSIDE_TOP_5':
            from apps.profiles.services import _verificar_ranking
            resultado = _verificar_ranking(user, 5)
            if resultado is False:
                b      = item.value
                motivo = "fora do top 5 ✅"
            elif resultado is None:
                motivo = "sem snapshot de ranking ❌"
            else:
                motivo = "dentro do top 5 ❌"

        elif effect == 'XP_PER_LEVEL':
            raw    = player.level * item.value
            b      = raw if item.max_bonus == 0 else min(raw, item.max_bonus)
            motivo = f"level {player.level} × {item.value}% = {b}%"

        elif effect == 'XP_CODE_CHALLENGE' and fonte == 'codigo':
            b      = item.value
            motivo = "fonte=codigo ✅"
        elif effect == 'XP_PATROL_CHALLENGE' and fonte == 'patrol':
            b      = item.value
            motivo = "fonte=patrol ✅"
        elif effect == 'XP_DECRYPT_CHALLENGE' and fonte == 'decriptar':
            b      = item.value
            motivo = "fonte=decriptar ✅"
        elif effect == 'XP_LOGSCAN_CHALLENGE' and fonte == 'logscan':
            b      = item.value
            motivo = "fonte=logscan ✅"
        elif effect in ('XP_CODE_CHALLENGE', 'XP_PATROL_CHALLENGE', 'XP_DECRYPT_CHALLENGE', 'XP_LOGSCAN_CHALLENGE'):
            motivo = f"fonte='{fonte}' ❌"

        elif effect == 'XP_RANDOM':
            import random
            b      = random.uniform(item.value, item.max_bonus)
            motivo = f"sorteio {item.value}%–{item.max_bonus}% → {b:.2f}%"

        elif effect == 'DOUBLE_XP_WEEK_FIRST':
            if _e_primeiro_desafio_da_semana(user):
                b      = item.value
                motivo = "primeiro desafio da semana ✅"
            else:
                motivo = "não é o primeiro desafio da semana ❌"

        elif effect == 'XP_WEEKEND':
            if timezone.now().weekday() >= 5:
                b = item.value
                motivo = f"fim de semana ✅"
            else:
                motivo = f"dia {timezone.now().strftime('%A')} ❌"

        elif effect == 'XP_TUESDAY':
            if timezone.now().weekday() == 1:
                b = item.value
                motivo = "terça-feira ✅"
            else:
                motivo = f"dia {timezone.now().strftime('%A')} ❌"

        elif effect == 'XP_HIGH_CASH':
            if player.coins >= 100:
                b = item.value
                motivo = f"coins ({player.coins}) >= 100 ✅"
            else:
                motivo = f"coins ({player.coins}) < 100 ❌"

        elif effect == 'XP_ZERO_CASH':
            if player.coins == 0:
                b = item.value
                motivo = f"coins = 0 ✅"
            else:
                motivo = f"coins ({player.coins}) != 0 ❌"

        elif effect == 'LUCKY_13':
            resto = player.level % 10
            if resto in (3, 6):
                b = item.value
                motivo = f"level {player.level} % 10 = {resto} ✅"
            else:
                motivo = f"level {player.level} % 10 = {resto} ❌"

        elif effect == 'XP_BEAST_CASH':
            if player.coins % 10 == 6:
                b = item.value
                motivo = f"coins ({player.coins}) termina em 6 ✅"
            else:
                motivo = f"coins ({player.coins}) termina em {player.coins % 10} ❌"

        elif effect == 'XP_PRIME_CASH':
            if _is_prime(player.coins):
                b = item.value
                motivo = f"coins ({player.coins}) é primo ✅"
            else:
                motivo = f"coins ({player.coins}) não é primo ❌"

        elif effect == 'XP_FIRST_DAILY':
            if _e_primeiro_desafio_do_dia(user):
                b = item.value
                motivo = "primeiro desafio do dia ✅"
            else:
                motivo = "já completou um desafio hoje ❌"

        else:
            motivo = f"effect '{effect}' não reconhecido"

        bonus_total += b
        breakdown.append({
            "fonte":      item.name,
            "categoria":  "Módulo Passivo",
            "tipo":       effect,
            "pct":        round(b, 2),
            "motivo":     motivo,
            "ativo":      b > 0,
        })

    for item in multiplicadores:
        acrescimo   = bonus_total * (item.value / 100)
        bonus_total += acrescimo
        breakdown.append({
            "fonte":     item.name,
            "categoria": "Módulo Passivo",
            "tipo":      "XP_STACK_MULTIPLIER",
            "pct":       round(acrescimo, 2),
            "motivo":    f"×{item.value}% sobre bônus acumulado → +{acrescimo:.2f}%",
            "ativo":     acrescimo > 0,
        })

    # ── Consumíveis ativos — Agora são alcançados mesmo se 'passivos' estiver vazio ──
    agora    = timezone.now()
    efeitos  = ActiveEffect.objects.filter(
        player=user, effect='XP_BOOST_DAYS', expires_at__gt=agora
    ).select_related('item')

    for efeito in efeitos:
        bonus_total += efeito.value
        breakdown.append({
            "fonte":     efeito.item.name if efeito.item else "XP Boost",
            "categoria": "Consumível Ativo",
            "tipo":      "XP_BOOST_DAYS",
            "pct":       efeito.value,
            "motivo":    f"ativo até {efeito.expires_at.strftime('%d/%m %H:%M')}",
            "ativo":     True,
        })

    total = round(bonus_total, 2)

    return (total, breakdown) if retornar_breakdown else total


def _get_consumivel_xp_bonus(user):
    """Soma % de XP de consumíveis ativos com duração."""
    agora = timezone.now()
    efeitos = ActiveEffect.objects.filter(
        player=user,
        effect='XP_BOOST_DAYS',
        expires_at__gt=agora,
    )
    return sum(e.value for e in efeitos)

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
    from apps.profiles.services import get_perk_valor
    tempo_extra += get_perk_valor(user, 'add_time')

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


def get_fator_reducao_tempo(user):
    passivo = PlayerItem.objects.filter(
        player=user,
        item__tipo='passive',
        item__effect='TIME_REDUCTION_XP_BOOST',
        slot_index__isnull=False,
    ).select_related('item').first()
    if not passivo:
        return 1.0
    reducao_pct = abs(passivo.item.value) 
    return round(1.0 - (reducao_pct / 100), 4) 