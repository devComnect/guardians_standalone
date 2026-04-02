"""
apps/store/admin.py
"""
from django.contrib import admin, messages # Adicionado messages
from django.utils.html import format_html
from django import forms # Adicionado para o formulário customizado
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from .models import (
    StoreConfig, Item, PlayerItem,
    ActiveEffect, DailyStore, StoreTransaction,
)

# ─────────────────────────────────────────────
# CONFIG SINGLETON
# ─────────────────────────────────────────────

@admin.register(StoreConfig)
class StoreConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Slots e Probabilidades', {
            'fields': (
                'slots_diarios',
                ('weight_common', 'weight_rare', 'weight_epic'),
            ),
            'description': 'Os pesos de raridade não precisam somar 100 — são ponderados automaticamente.'
        }),
        ('Reroll', {
            'fields': ('reroll_custo_base', 'reroll_incremento'),
        }),
        ('Inventário', {
            'fields': ('max_passivos_slots', 'max_consumiveis'),
        }),
    )

    def has_add_permission(self, request):
        return not StoreConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ─────────────────────────────────────────────
# ITEM
# ─────────────────────────────────────────────

class GiveItemForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    player = forms.ModelChoiceField(queryset=User.objects.all(), label="Selecionar Player")
    quantidade = forms.IntegerField(min_value=1, initial=1, label="Quantidade de cada item")

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'item_id', 'name', 'tipo_badge', 'raridade_badge',
        'build', 'effect', 'cost', 'disponivel',
    )
    list_filter = ('tipo', 'raridade', 'build', 'disponivel', 'season')
    search_fields = ('name', 'description', 'effect')
    list_editable = ('disponivel', 'cost')
    ordering = ('item_id',)
    actions = ['give_items_to_player'] # Registra a ação

    fieldsets = (
        ('Identificação', {
            'fields': ('item_id', 'name', 'description', 'tipo', 'raridade', 'build'),
        }),
        ('Efeito', {
            'fields': ('effect', 'value', 'value_secondary', 'duration_days', 'max_bonus'),
        }),
        ('Economia', {
            'fields': ('cost', 'disponivel', 'season'),
        }),
    )

    # ACTION: Dar itens selecionados para um player
    def give_items_to_player(self, request, queryset):
        form = None

        # Se o formulário foi enviado (confirmado o player)
        if 'apply' in request.POST:
            form = GiveItemForm(request.POST)
            if form.is_valid():
                player = form.cleaned_data['player']
                qtd = form.cleaned_data['quantidade']
                count = 0

                for item in queryset:
                    # Lógica: incrementa se existe, cria se não existe
                    player_item, created = PlayerItem.objects.get_or_create(
                        player=player,
                        item=item,
                        defaults={'quantidade': qtd}
                    )
                    if not created:
                        player_item.quantidade += qtd
                        player_item.save()
                    count += 1

                self.message_user(request, f"Sucesso! {count} tipos de itens entregues para {player.username}.", messages.SUCCESS)
                return HttpResponseRedirect(request.get_full_path())

        # Se é o primeiro clique, exibe a página de seleção de player
        if not form:
            form = GiveItemForm(initial={'_selected_action': queryset.values_list('pk', flat=True)})

        return render(request, 'admin/store/give_items_confirmation.html', {
            'items': queryset,
            'form': form,
            'title': u'Entregar itens para Player'
        })

    give_items_to_player.short_description = "Debug: Dar itens selecionados a um Player"

    # --- Seus métodos de badge mantidos ---
    def tipo_badge(self, obj):
        cores = {'consumable': '#f59e0b', 'passive': '#3b82f6', 'cosmetic': '#ec4899'}
        cor = cores.get(obj.tipo, '#6b7280')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>', cor, obj.get_tipo_display())
    tipo_badge.short_description = 'Tipo'

    def raridade_badge(self, obj):
        cores = {'COMMON': '#6b7280', 'RARE': '#3b82f6', 'EPIC': '#9333ea', 'LEGENDARY': '#fcee0a'}
        cor = cores.get(obj.raridade, '#6b7280')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">{}</span>', cor, obj.raridade)
    raridade_badge.short_description = 'Raridade'


# ─────────────────────────────────────────────
# PLAYER ITEM (Inventário)
# ─────────────────────────────────────────────

@admin.register(PlayerItem)
class PlayerItemAdmin(admin.ModelAdmin):
    list_display  = ('player', 'item', 'tipo_item', 'quantidade', 'slot_index', 'equipado', 'adquirido_em')
    list_filter   = ('item__tipo', 'item__raridade', 'equipado')
    search_fields = ('player__username', 'item__name')
    raw_id_fields = ('player', 'item')
    readonly_fields = ('adquirido_em', 'atualizado_em')

    def tipo_item(self, obj):
        return obj.item.get_tipo_display()
    tipo_item.short_description = 'Tipo'


# ─────────────────────────────────────────────
# EFEITOS ATIVOS
# ─────────────────────────────────────────────

@admin.register(ActiveEffect)
class ActiveEffectAdmin(admin.ModelAdmin):
    list_display  = ('player', 'effect', 'value', 'expires_at', 'is_ativo')
    list_filter   = ('effect',)
    search_fields = ('player__username', 'effect')
    readonly_fields = ('ativado_em',)

    def is_ativo(self, obj):
        from django.utils import timezone
        ativo = timezone.now() < obj.expires_at
        cor   = '#16a34a' if ativo else '#dc2626'
        label = 'Ativo' if ativo else 'Expirado'
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>', cor, label
        )
    is_ativo.short_description = 'Status'


# ─────────────────────────────────────────────
# LOJA DIÁRIA
# ─────────────────────────────────────────────

class DailyStoreItemsInline(admin.TabularInline):
    model  = DailyStore.items.through
    extra  = 0
    verbose_name = 'Item no Slot'
    verbose_name_plural = 'Itens nos Slots'


@admin.register(DailyStore)
class DailyStoreAdmin(admin.ModelAdmin):
    list_display  = ('player', 'date', 'reroll_count', 'total_itens', 'gerado_em')
    list_filter   = ('date',)
    search_fields = ('player__username',)
    readonly_fields = ('gerado_em',)
    inlines       = [DailyStoreItemsInline]

    def total_itens(self, obj):
        return obj.items.count()
    total_itens.short_description = 'Itens'


# ─────────────────────────────────────────────
# TRANSAÇÕES
# ─────────────────────────────────────────────

@admin.register(StoreTransaction)
class StoreTransactionAdmin(admin.ModelAdmin):
    list_display  = (
        'player', 'item', 'tipo', 'coins_delta_fmt',
        'xp_delta', 'desconto_aplicado', 'criado_em',
    )
    list_filter   = ('tipo', 'desconto_aplicado')
    search_fields = ('player__username', 'item__name', 'descricao')
    readonly_fields = ('criado_em',)

    def has_add_permission(self, request):
        return False  # Log imutável via interface

    def has_change_permission(self, request, obj=None):
        return False

    def coins_delta_fmt(self, obj):
        cor   = '#16a34a' if obj.coins_delta >= 0 else '#dc2626'
        sinal = '+' if obj.coins_delta >= 0 else ''
        return format_html(
            '<span style="color:{};font-weight:bold">{}{}</span>',
            cor, sinal, obj.coins_delta
        )
    coins_delta_fmt.short_description = 'Coins Δ'