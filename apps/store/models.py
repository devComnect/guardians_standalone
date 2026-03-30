"""
apps/store/models.py
Etapa 9 — Itens, Cosméticos e Inventário
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ─────────────────────────────────────────────
# CONFIG SINGLETON DA LOJA
# ─────────────────────────────────────────────

class StoreConfig(models.Model):
    """
    Configuração global da loja — singleton.
    Permite ao admin ajustar raridades, reroll e slots sem tocar no código.
    """
    # Probabilidades de raridade (devem somar 100)
    weight_common   = models.PositiveSmallIntegerField(
        default=70,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name='Peso COMMON (%)',
        help_text='Probabilidade de aparecer um item Common nos slots da loja'
    )
    weight_rare     = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name='Peso RARE (%)'
    )
    weight_epic     = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name='Peso EPIC (%)'
    )

    # Slots da loja por dia
    slots_diarios   = models.PositiveSmallIntegerField(
        default=4,
        help_text='Quantos itens aparecem na loja por dia'
    )

    # Reroll
    reroll_custo_base   = models.PositiveSmallIntegerField(
        default=5,
        help_text='Custo do primeiro reroll do dia (em G-Coins)'
    )
    reroll_incremento   = models.PositiveSmallIntegerField(
        default=5,
        help_text='Quanto sobe o custo a cada reroll adicional no dia'
    )

    # Slots passivos do inventário
    max_passivos_slots  = models.PositiveSmallIntegerField(
        default=4,
        help_text='Quantos upgrades passivos o player pode ter ativos simultaneamente'
    )

    # Limite de consumíveis no inventário
    max_consumiveis     = models.PositiveSmallIntegerField(
        default=20,
        help_text='Limite de consumíveis no inventário de carga'
    )

    class Meta:
        verbose_name        = 'Config — Loja'
        verbose_name_plural = 'Config — Loja'

    def __str__(self):
        return (
            f'Loja: {self.slots_diarios} slots | '
            f'C:{self.weight_common}% R:{self.weight_rare}% E:{self.weight_epic}%'
        )

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ─────────────────────────────────────────────
# ITEM (Catálogo)
# ─────────────────────────────────────────────

class Item(models.Model):

    TIPO_CHOICES = [
        ('consumable', 'Consumível'),
        ('passive',    'Upgrade Passivo'),
        ('cosmetic',   'Cosmético'),
    ]

    RARIDADE_CHOICES = [
        ('COMMON', 'Common'),
        ('RARE',   'Rare'),
        ('EPIC',   'Epic'),
    ]

    # Efeitos possíveis — usados pelo services.py para aplicar lógica
    EFFECT_CHOICES = [
        # Consumíveis
        ('TOKEN_RETAKE',        'Refazer desafio falho'),
        ('XP_BOOST_DAYS',       'Bônus de XP por dias'),
        ('STREAK_CAP_BOOST',    'Aumenta teto de ofensiva'),
        ('STREAK_FREEZE',       'Congela streak por dias'),
        ('FREE_HINT',           'Dica grátis no próximo desafio'),
        ('EXTRA_LIFE_TIME',     '+Tempo e +Vida no próximo desafio'),
        ('CONVERT_GOLD_XP',     'Converte Coins em XP'),
        ('CONVERT_XP_GOLD',     'Converte XP em Coins'),
        # Passivos
        ('XP_PER_COIN',             '+XP% por coin em saldo'),
        ('SHOP_DISCOUNT',           'Desconto na loja'),
        ('XP_LOW_CASH',             '+XP% se saldo < 10'),
        ('XP_ODD_CASH',             '+XP% se saldo ímpar'),
        ('TIME_REDUCTION_XP_BOOST', '-Tempo +XP%'),
        ('XP_PER_SECOND',           '+XP% por segundo restante'),
        ('ADD_TIME',                '+Tempo fixo'),
        ('XP_QUICK_WIN',            '+XP% se vencer em < 3 tentativas'),
        ('XP_SAME_RARITY',          '+XP% se todos 4 itens mesma raridade'),
        ('XP_PER_COMMON',           '+XP% por item Common equipado'),
        ('XP_PER_EMPTY_SLOT',       '+XP% por slot vazio'),
        ('XP_STACK_MULTIPLIER',     'Multiplica todos bônus XP'),
        ('XP_PER_COSMETIC',         '+XP% por cosmético equipado'),
        ('XP_PER_FEATURED_ACHIEVEMENT', '+XP% por conquista em destaque'),
        ('XP_TOP_3',                '+XP% se Top 3'),
        ('XP_OUTSIDE_TOP_10',       '+XP% se fora do Top 10'),
        ('XP_PER_LEVEL',            '+XP% por nível'),
        ('XP_CODE_CHALLENGE',       '+XP% em desafios de Código'),
        ('XP_PATROL_CHALLENGE',     '+XP% em desafios de Patrulha'),
        ('XP_DECRYPT_CHALLENGE',    '+XP% em desafios de Decriptar'),
        ('XP_RANDOM',               'Bônus XP% aleatório'),
        ('DOUBLE_XP_WEEK_FIRST',    'Dobra XP do 1º desafio da semana'),
        # Cosméticos
        ('COSMETIC_FRAME',      'Frame de perfil'),
        ('COSMETIC_BACKGROUND', 'Background de perfil'),
        ('COSMETIC_TITLE',      'Título de perfil'),
    ]

    BUILD_CHOICES = [
        ('ECONOMY',  'Economy'),
        ('SPEEDRUN', 'Speedrun'),
        ('UTILITY',  'Utility'),
        ('SKILL',    'Skill'),
        ('SYNERGY',  'Synergy'),
        ('BUFF',     'Buff'),
        ('SOCIAL',   'Social'),
        ('RANKING',  'Ranking'),
        ('SCALING',  'Scaling'),
        ('SPECIFIC', 'Specific'),
        ('LUCK',     'Luck'),
        ('TIME',     'Time'),
        ('NONE',     'Nenhum'),
    ]

    # Identificação
    item_id     = models.PositiveSmallIntegerField(
        unique=True,
        help_text='ID canônico do JSON de design (ex: 1, 101, 201)'
    )
    name        = models.CharField(max_length=100, verbose_name='Nome')
    description = models.TextField(verbose_name='Descrição')
    tipo        = models.CharField(max_length=12, choices=TIPO_CHOICES)
    raridade    = models.CharField(max_length=6, choices=RARIDADE_CHOICES, default='COMMON')
    build       = models.CharField(max_length=10, choices=BUILD_CHOICES, default='NONE')
    effect      = models.CharField(max_length=40, choices=EFFECT_CHOICES)

    # Ícone do item — Bootstrap Icons class
    icon        = models.CharField(
        max_length=60,
        default='bi-box',
        verbose_name='Ícone Bootstrap Icons',
        help_text='Classe do Bootstrap Icons (ex: bi-cpu-fill). Editável via admin.'
    )

    # Valores do efeito (flexível para diferentes tipos)
    value           = models.FloatField(default=0, help_text='Valor principal do efeito')
    value_secondary = models.FloatField(default=0, help_text='Valor secundário (ex: xp_cost, time_mod)')
    duration_days   = models.PositiveSmallIntegerField(default=0, help_text='Duração em dias (0 = instantâneo)')
    max_bonus       = models.FloatField(default=0, help_text='Bônus máximo (0 = sem teto)')

    # Preço
    cost        = models.PositiveIntegerField(default=0, help_text='Preço base em G-Coins')

    # Disponibilidade
    disponivel  = models.BooleanField(default=True, help_text='Aparece na rolagem da loja')
    season      = models.ForeignKey(
        'challenges.Season', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='store_items',
        help_text='Se preenchido, só aparece nessa temporada'
    )

    criado_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Item'
        verbose_name_plural = 'Itens'
        ordering            = ['tipo', 'raridade', 'item_id']

    def __str__(self):
        return f'[{self.item_id}] {self.name} ({self.get_raridade_display()}) — {self.cost}⬡'


# ─────────────────────────────────────────────
# INVENTÁRIO DO PLAYER
# ─────────────────────────────────────────────

class PlayerItem(models.Model):
    """
    Inventário: itens que o player possui.
    - Passivos: slot_index 1–4 (None = não equipado)
    - Consumíveis: quantidade >= 1, sem slot
    - Cosméticos: equipado=True = visual ativo
    """
    player      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='inventory'
    )
    item        = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name='owners'
    )
    quantidade  = models.PositiveSmallIntegerField(default=1)

    # Passivos: qual slot está ocupando (None = comprado mas não equipado)
    slot_index  = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text='Slot ativo (1–4) para upgrades passivos. Null = não equipado'
    )

    # Cosméticos: qual está equipado
    equipado    = models.BooleanField(
        default=False,
        help_text='Para cosméticos: True = visual ativo no perfil'
    )

    adquirido_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Item do Player'
        verbose_name_plural = 'Itens dos Players'
        unique_together     = ('player', 'item')
        ordering            = ['-adquirido_em']

    def __str__(self):
        return f'{self.player.username} → {self.item.name} (x{self.quantidade})'

    @property
    def is_equipado(self):
        """Para passivos: está em algum slot. Para cosméticos: equipado=True."""
        if self.item.tipo == 'passive':
            return self.slot_index is not None
        return self.equipado


# ─────────────────────────────────────────────
# EFEITOS TEMPORÁRIOS ATIVOS
# ─────────────────────────────────────────────

class ActiveEffect(models.Model):
    """
    Rastreia consumíveis com duração (ex: XP_BOOST_DAYS, STREAK_FREEZE).
    Verificado pelo services.py no momento do cálculo de XP.
    """
    player      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='active_effects'
    )
    item        = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name='active_instances'
    )
    effect      = models.CharField(max_length=40)      # Cópia do item.effect
    value       = models.FloatField(default=0)          # Cópia do item.value
    expires_at  = models.DateTimeField()
    ativado_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Efeito Ativo'
        verbose_name_plural = 'Efeitos Ativos'
        ordering            = ['expires_at']

    def __str__(self):
        return f'{self.player.username} — {self.effect} até {self.expires_at.date()}'

    @property
    def is_active(self):
        return timezone.now() < self.expires_at


# ─────────────────────────────────────────────
# LOJA DIÁRIA (Slots gerados)
# ─────────────────────────────────────────────

class DailyStore(models.Model):
    """
    Registro dos slots gerados para o dia.
    Gerado uma vez por player por dia (lazy: na primeira visita).
    """
    player      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='daily_stores'
    )
    date        = models.DateField(default=timezone.localdate)
    items       = models.ManyToManyField(Item, blank=True, related_name='daily_appearances')
    reroll_count = models.PositiveSmallIntegerField(default=0)
    gerado_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Loja Diária'
        verbose_name_plural = 'Lojas Diárias'
        unique_together     = ('player', 'date')
        ordering            = ['-date']

    def __str__(self):
        return f'{self.player.username} — Loja {self.date} (rerolls: {self.reroll_count})'

    @property
    def reroll_cost(self):
        """Custo do próximo reroll com base no histórico do dia."""
        config = StoreConfig.get()
        return config.reroll_custo_base + (self.reroll_count * config.reroll_incremento)


# ─────────────────────────────────────────────
# LOG DE TRANSAÇÕES
# ─────────────────────────────────────────────

class StoreTransaction(models.Model):
    """
    Log imutável de cada compra/venda/ativação na loja.
    Nunca deletar — serve para auditoria e conquistas.
    """
    TIPO_CHOICES = [
        ('purchase',   'Compra'),
        ('sell',       'Venda'),
        ('activate',   'Ativação de Consumível'),
        ('reroll',     'Reroll'),
        ('convert',    'Conversão (XP↔Coins)'),
    ]

    player          = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='store_transactions'
    )
    item            = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True
    )
    tipo            = models.CharField(max_length=10, choices=TIPO_CHOICES)
    coins_delta     = models.IntegerField(default=0,
        help_text='Negativo = gasto, positivo = recebido'
    )
    xp_delta        = models.IntegerField(default=0,
        help_text='XP ganho/perdido na transação'
    )
    desconto_aplicado = models.BooleanField(default=False)
    descricao       = models.CharField(max_length=300, blank=True)
    criado_em       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Transação — Loja'
        verbose_name_plural = 'Transações — Loja'
        ordering            = ['-criado_em']

    def __str__(self):
        return (
            f'{self.player.username} — {self.get_tipo_display()} '
            f'| {self.coins_delta:+}⬡ [{self.criado_em.date()}]'
        )