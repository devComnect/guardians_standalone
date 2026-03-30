"""
apps/store/views.py
Etapa 9 — Views da Loja

Endpoints JSON (fetch) estão marcados com @require_POST e retornam JsonResponse.
A view principal (index) renderiza o template da loja.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Item, StoreConfig
from .services import (
    get_or_generate_daily_store,
    realizar_reroll,
    comprar_item,
    vender_passivo,
    ativar_consumivel,
    equipar_cosmético,
    desequipar_cosmético,
    get_inventario_completo,
    _calcular_preco_final,
)


# ─────────────────────────────────────────────
# LOJA PRINCIPAL
# ─────────────────────────────────────────────

@login_required
def index(request):
    """
    Página principal da loja.
    Gera (ou recupera) os slots diários do player.
    """
    daily, items_qs = get_or_generate_daily_store(request.user)
    config          = StoreConfig.get()
    player          = getattr(request.user, 'player', None)

    # Calcula preço final de cada item (com desconto se aplicável)
    slots = []
    for item in items_qs:
        preco_final, tem_desconto = _calcular_preco_final(item, request.user)
        slots.append({
            'item':        item,
            'preco_final': preco_final,
            'tem_desconto': tem_desconto,
        })

    inventario = get_inventario_completo(request.user)

    context = {
        'daily':           daily,
        'slots':           slots,
        'reroll_custo':    daily.reroll_cost,
        'config':          config,
        'player':          player,
        'inventario':      inventario,
    }
    return render(request, 'store/index.html', context)


# ───────────────────────────────────────────── 
# INVENTÁRIO
# ─────────────────────────────────────────────

@login_required
def inventario(request):
    """Página de inventário do player."""
    inventario = get_inventario_completo(request.user)
    player     = getattr(request.user, 'player', None)

    context = {
        'inventario': inventario,
        'player':     player,
    }
    return render(request, 'store/inventario.html', context)


# ─────────────────────────────────────────────
# AÇÕES (JSON endpoints)
# ─────────────────────────────────────────────

@login_required
@require_POST
def ajax_reroll(request):
    """POST /loja/reroll/ — Paga e rerrola os slots do dia."""
    sucesso, mensagem, daily, proximo_custo = realizar_reroll(request.user)

    if not sucesso:
        return JsonResponse({'ok': False, 'mensagem': mensagem}, status=400)

    config = StoreConfig.get()
    player = getattr(request.user, 'player', None)

    # Retorna os novos itens com preços finais
    novos_itens = []
    for item in daily.items.all():
        preco_final, tem_desconto = _calcular_preco_final(item, request.user)
        novos_itens.append({
            'item_id':     item.item_id,
            'name':        item.name,
            'description': item.description,
            'tipo':        item.tipo,
            'raridade':    item.raridade,
            'build':       item.build,
            'icon':        item.icon,
            'cost':        item.cost,
            'preco_final': preco_final,
            'tem_desconto': tem_desconto,
        })

    return JsonResponse({
        'ok':            True,
        'mensagem':      mensagem,
        'novos_itens':   novos_itens,
        'proximo_custo': proximo_custo,
        'reroll_count':  daily.reroll_count,
        'coins_atual':   player.coins if player else 0,
    })


@login_required
@require_POST
def ajax_comprar(request):
    """
    POST /loja/comprar/
    Body JSON: {item_id: int, slot_substituir?: int}
    """
    try:
        data          = json.loads(request.body)
        item_id       = int(data.get('item_id', 0))
        slot_sub      = data.get('slot_substituir')
        slot_sub      = int(slot_sub) if slot_sub else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'mensagem': 'Dados inválidos.'}, status=400)

    sucesso, mensagem, extra = comprar_item(request.user, item_id, slot_sub)
    player = getattr(request.user, 'player', None)

    if not sucesso:
        return JsonResponse({
            'ok':       False,
            'mensagem': mensagem,
            'extra':    extra,
        }, status=400)

    return JsonResponse({
        'ok':         True,
        'mensagem':   mensagem,
        'extra':      extra,
        'coins_atual': player.coins if player else 0,
    })


@login_required
@require_POST
def ajax_vender(request):
    """POST /loja/vender/ — Vende passivo por 50% do valor."""
    try:
        data    = json.loads(request.body)
        item_id = int(data.get('item_id', 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'mensagem': 'Dados inválidos.'}, status=400)

    sucesso, mensagem, reembolso = vender_passivo(request.user, item_id)
    player = getattr(request.user, 'player', None)

    if not sucesso:
        return JsonResponse({'ok': False, 'mensagem': mensagem}, status=400)

    return JsonResponse({
        'ok':         True,
        'mensagem':   mensagem,
        'reembolso':  reembolso,
        'coins_atual': player.coins if player else 0,
    })


@login_required
@require_POST
def ajax_ativar_consumivel(request):
    """POST /loja/ativar/ — Ativa consumível do inventário."""
    try:
        data    = json.loads(request.body)
        item_id = int(data.get('item_id', 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'mensagem': 'Dados inválidos.'}, status=400)

    sucesso, mensagem, resultado = ativar_consumivel(request.user, item_id)
    player = getattr(request.user, 'player', None)

    if not sucesso:
        return JsonResponse({'ok': False, 'mensagem': mensagem}, status=400)

    return JsonResponse({
        'ok':         True,
        'mensagem':   mensagem,
        'resultado':  resultado,
        'coins_atual': player.coins if player else 0,
        'xp_atual':   player.xp_total if player else 0,
    })


@login_required
@require_POST
def ajax_equipar_cosmético(request):
    """POST /loja/equipar-cosmético/ — Equipa cosmético."""
    try:
        data    = json.loads(request.body)
        item_id = int(data.get('item_id', 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'mensagem': 'Dados inválidos.'}, status=400)

    sucesso, mensagem = equipar_cosmético(request.user, item_id)
    if not sucesso:
        return JsonResponse({'ok': False, 'mensagem': mensagem}, status=400)

    return JsonResponse({'ok': True, 'mensagem': mensagem})


@login_required
@require_POST
def ajax_desequipar_cosmético(request):
    """POST /loja/desequipar-cosmético/ — Desequipa cosmético."""
    try:
        data    = json.loads(request.body)
        item_id = int(data.get('item_id', 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'mensagem': 'Dados inválidos.'}, status=400)

    sucesso, mensagem = desequipar_cosmético(request.user, item_id)
    if not sucesso:
        return JsonResponse({'ok': False, 'mensagem': mensagem}, status=400)

    return JsonResponse({'ok': True, 'mensagem': mensagem})


@login_required
def ajax_estado_inventario(request):
    """GET /loja/inventario/estado/ — Retorna estado atual do inventário como JSON."""
    inventario = get_inventario_completo(request.user)
    player     = getattr(request.user, 'player', None)

    passivos_json = {}
    for slot, pi in inventario['passivos'].items():
        if pi:
            passivos_json[slot] = {
                'item_id':     pi.item.item_id,
                'name':        pi.item.name,
                'raridade':    pi.item.raridade,
                'effect':      pi.item.effect,
                'description': pi.item.description,
            }
        else:
            passivos_json[slot] = None

    consumiveis_json = [
        {
            'item_id':    pi.item.item_id,
            'name':       pi.item.name,
            'raridade':   pi.item.raridade,
            'quantidade': pi.quantidade,
            'effect':     pi.item.effect,
        }
        for pi in inventario['consumiveis']
    ]

    efeitos_json = [
        {
            'effect':      ae.effect,
            'value':       ae.value,
            'expires_at':  ae.expires_at.isoformat(),
        }
        for ae in inventario['efeitos_ativos']
    ]

    return JsonResponse({
        'passivos':       passivos_json,
        'consumiveis':    consumiveis_json,
        'efeitos_ativos': efeitos_json,
        'coins':          player.coins if player else 0,
    })