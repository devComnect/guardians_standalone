from django.db import models
from django.contrib.auth.models import User


# ─────────────────────────────────────────────
# PLAYER
# ─────────────────────────────────────────────

class Player(models.Model):
    CLASSE_CHOICES = [
        ('none',      'Sem Classe'),
        ('guardian',  'Guardian'),
        ('analyst',   'Analyst'),
        ('sentinel',  'Sentinel'),
        ('hacker',    'Hacker'),
    ]

    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player')
    display_name  = models.CharField(max_length=60, blank=True)
    avatar        = models.ImageField(upload_to='avatars/', blank=True, null=True)
    classe        = models.CharField(max_length=20, choices=CLASSE_CHOICES, default='guardian')
    bio           = models.TextField(blank=True)

    # Progressão
    xp_total      = models.PositiveIntegerField(default=0)
    level         = models.PositiveSmallIntegerField(default=1)
    coins         = models.PositiveIntegerField(default=0)
    streak_days   = models.PositiveSmallIntegerField(default=0)
    last_play_date = models.DateField(null=True, blank=True)

    # Troca de classe
    classe_trocada_em = models.DateTimeField(null=True, blank=True)

    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    #Ofensiva
    ofensiva        = models.PositiveIntegerField(default=0,
        help_text='Total acumulado de ofensiva (sem teto)')
    last_challenge_date = models.DateField(null=True, blank=True,
        help_text='Último dia em que completou pelo menos um desafio')

    class Meta:
        verbose_name = 'Player'
        verbose_name_plural = 'Players'

    def __str__(self):
        return f'{self.user.username} — Lv.{self.level} [{self.get_classe_display()}]'

    @staticmethod
    def xp_para_nivel(nivel):
        """Curva agressiva: começa fácil, cresce rapidamente."""
        return int(50 * (nivel ** 2.5))

    @property
    def xp_proximo_nivel(self):
        return self.xp_para_nivel(self.level)

    @property
    def xp_nivel_anterior(self):
        if self.level <= 1:
            return 0
        return self.xp_para_nivel(self.level - 1)

    @property
    def xp_no_nivel_atual(self):
        """XP acumulado dentro do nível corrente."""
        return self.xp_total - self.xp_nivel_anterior

    @property
    def xp_necessario_nivel_atual(self):
        """Quanto XP é necessário para completar o nível atual."""
        return self.xp_proximo_nivel - self.xp_nivel_anterior

    @property
    def xp_percentual(self):
        necessario = self.xp_necessario_nivel_atual
        if necessario <= 0:
            return 100
        return min(100, int((self.xp_no_nivel_atual / necessario) * 100))
    
    @property
    def xp_para_proximo_nivel(self):
        return self.xp_proximo_nivel


# ─────────────────────────────────────────────
# PERKS
# ─────────────────────────────────────────────

class Perk(models.Model):
    CLASSE_CHOICES = [
        ('guardian',  'Guardian'),
        ('analyst',   'Analyst'),
        ('sentinel',  'Sentinel'),
        ('hacker',    'Hacker'),
    ]

    TIPO_CHOICES = [
        # Bônus de XP
        ('xp_global',    'Bônus XP Global (%)'),
        ('xp_quiz',      'Bônus XP em Quiz (%)'),
        ('xp_decriptar', 'Bônus XP em Decriptar (%)'),
        ('xp_codigo',    'Bônus XP em Código (%)'),
        ('xp_password',  'Bônus XP em Cofre de Senhas (%)'),
        # Gameplay
        ('vida_extra',       'Vida Extra em Decriptar (+N)'),
        ('dica_gratis',      'Dica Gratuita por sessão'),
        ('streak_shield',    'Proteção de Streak (dias)'),
        ('coin_bonus',       'Bônus de Moedas (%)'),
        ('tentativa_extra',  'Tentativa Extra no Código (+N)'),
    ]

    classe          = models.CharField(max_length=20, choices=CLASSE_CHOICES)
    tipo            = models.CharField(max_length=20, choices=TIPO_CHOICES)
    nome            = models.CharField(max_length=100)
    descricao       = models.TextField()
    valor           = models.FloatField(default=0, help_text='Percentual (10 = 10%) ou valor absoluto')
    level_required  = models.PositiveSmallIntegerField(default=1)
    ativo           = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Perk'
        verbose_name_plural = 'Perks'
        ordering = ['classe', 'level_required']

    def __str__(self):
        return f'[{self.get_classe_display()}] Lv.{self.level_required} — {self.nome}'


# ─────────────────────────────────────────────
# HISTÓRICO DE XP
# ─────────────────────────────────────────────

class XPEvent(models.Model):
    FONTE_CHOICES = [
        ('quiz',       'Quiz'),
        ('decriptar',  'Decriptar'),
        ('codigo',     'Código'),
        ('password',   'Cofre de Senhas'),
        ('feedback',   'Feedback'),
        ('conquista',  'Conquista'),
        ('missao',     'Missão'),
        ('bonus',      'Bônus'),
    ]

    player      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xp_events')
    fonte       = models.CharField(max_length=20, choices=FONTE_CHOICES)
    xp_base     = models.IntegerField(default=0)
    xp_bonus    = models.IntegerField(default=0)   # Vindo de perks
    xp_total    = models.IntegerField(default=0)
    descricao   = models.CharField(max_length=200)
    criado_em   = models.DateTimeField(auto_now_add=True)
    breakdown = models.JSONField(default=list, blank=True,
    help_text='Lista detalhada de bônus aplicados no cálculo')

    class Meta:
        verbose_name = 'Evento de XP'
        verbose_name_plural = 'Histórico de XP'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.player.username} +{self.xp_total}XP [{self.fonte}]'


# ─────────────────────────────────────────────
# NOTIFICAÇÕES DO PLAYER
# ─────────────────────────────────────────────

class PlayerNotification(models.Model):
    TIPO_CHOICES = [
        ('level_up',      'Level Up'),
        ('perk_unlock',   'Perk Desbloqueado'),
        ('conquista',     'Conquista'),
        ('missao',        'Missão Concluída'),
        ('sistema',       'Sistema'),
    ]

    player    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    tipo      = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo    = models.CharField(max_length=200)
    mensagem  = models.TextField(blank=True)
    icone     = models.CharField(max_length=50, default='bi-bell-fill')
    lida      = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.player.username} — {self.titulo}'


# ─────────────────────────────────────────────
# CONFIG DE TROCA DE CLASSE
# ─────────────────────────────────────────────

class ClasseConfig(models.Model):
    custo_primeira_classe = models.PositiveIntegerField(
        default=0, # Deixe 0 se quiser que a primeira vez seja de graça, ou coloque um valor
        help_text='Custo em coins para o player escolher a classe pela primeira vez'
    )
    custo_troca_coins = models.PositiveIntegerField(
        default=500,
        help_text='Custo em coins para trocar de classe posteriormente'
    )

    class Meta:
        verbose_name = 'Config — Troca de Classe'
        verbose_name_plural = 'Config — Troca de Classe'

    def __str__(self):
        return f'1ª Escolha: {self.custo_primeira_classe} | Troca: {self.custo_troca_coins}'
    
    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    


# ─────────────────────────────────────────────
# OFENSIVA
# ─────────────────────────────────────────────
class OfensivaConfig(models.Model):
    """Configuração global do sistema de ofensiva — singleton."""
    dias_tolerancia     = models.PositiveSmallIntegerField(
        default=3,
        help_text='Quantos dias sem jogar antes de zerar a streak'
    )
    teto_bonus_ofensiva = models.PositiveSmallIntegerField(
        default=50,
        help_text='Limite máximo de % de bônus global vindo da ofensiva'
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Config — Ofensiva'
        verbose_name_plural = 'Config — Ofensiva'

    def __str__(self):
        return f'Ofensiva: tolerância {self.dias_tolerancia}d · teto {self.teto_bonus_ofensiva}%'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    

class AchievementConfig(models.Model):
    """Config singleton — define quantas conquistas podem ficar em destaque."""
    max_destaques = models.PositiveSmallIntegerField(
        default=5,
        help_text='Quantas conquistas em destaque aplicam bônus simultaneamente'
    )
    class Meta:
        verbose_name = 'Config — Conquistas'
        verbose_name_plural = 'Config — Conquistas'

    def __str__(self):
        return f'Máx. destaques: {self.max_destaques}'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Achievement(models.Model):

    TRIGGER_CHOICES = [
        # Volume / contagem
        ('quiz_count',       'Nº de Quizzes concluídos'),
        ('quiz_perfect',     'Nº de Quizzes com 100%'),
        ('minigame_count',   'Nº de Minigames concluídos'),
        ('decriptar_count',  'Nº de Decriptar concluídos'),
        ('codigo_count',     'Nº de Código concluídos'),
        ('patrol_count',     'Nº de Patrulhas concluídas'),
        ('all_daily_count',  'Nº de dias com todos os desafios feitos'),
        # Progressão
        ('level_reached',    'Level atingido'),
        ('streak_days',      'Streak de dias consecutivos'),
        ('ofensiva',         'Pontos de ofensiva'),
        ('xp_total',         'XP total acumulado'),
        # Loja / social
        ('shop_count',       'Nº de itens comprados na loja'),
        ('feedback_count',   'Nº de feedbacks enviados'),
        ('vulnerability',    'Reportou uma vulnerabilidade'),
        # Sazonais
        ('season_top1',      'Terminou temporada em 1º'),
        ('season_top3',      'Terminou temporada no Top 3'),
    ]

    BONUS_TYPE_CHOICES = [
        ('global_xp_pct',    'Bônus XP Global (%)'),
        ('quiz_xp_pct',      'Bônus XP em Quiz (%)'),
        ('minigame_xp_pct',  'Bônus XP em Minigames (%)'),
        ('patrol_xp_pct',    'Bônus XP em Patrulha (%)'),
        ('anagram_xp_pct',   'Bônus XP em Decriptar (%)'),
        ('termo_xp_pct',     'Bônus XP em Código (%)'),
        ('pw_xp_pct',        'Bônus XP em Cofre de Senhas (%)'),
        ('coin_pct',         'Bônus de Moedas (%)'),
        ('ofensiva_teto',    'Aumenta teto de ofensiva (+N)'),
        ('streak_shield',    'Proteção de streak (dias)'),
    ]

    RARIDADE_CHOICES = [
        ('comum',      'Comum'),
        ('rara',       'Rara'),
        ('epica',      'Épica'),
        ('lendaria',   'Lendária'),
    ]

    code            = models.CharField(max_length=40, unique=True)
    nome            = models.CharField(max_length=100)
    descricao       = models.TextField()
    imagem          = models.CharField(max_length=200, blank=True,
                        help_text='Caminho relativo em static/ (ex: img/conquistas/nome.png)')
    raridade        = models.CharField(max_length=10, choices=RARIDADE_CHOICES, default='comum')
    trigger_type    = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    trigger_value   = models.PositiveIntegerField(default=1,
                        help_text='Valor necessário para desbloquear (ex: 5 quizzes)')
    bonus_type      = models.CharField(max_length=20, choices=BONUS_TYPE_CHOICES,
                        blank=True, null=True)
    bonus_value     = models.FloatField(default=0,
                        help_text='Valor do bônus quando em destaque')
    ativo           = models.BooleanField(default=True)
    ordem           = models.PositiveSmallIntegerField(default=0,
                        help_text='Ordem de exibição no perfil')

    class Meta:
        verbose_name = 'Conquista'
        verbose_name_plural = 'Conquistas'
        ordering = ['trigger_type', 'trigger_value']

    def __str__(self):
        return f'[{self.code}] {self.nome} ({self.get_raridade_display()})'


class PlayerAchievement(models.Model):
    player          = models.ForeignKey(User, on_delete=models.CASCADE,
                        related_name='achievements')
    achievement     = models.ForeignKey(Achievement, on_delete=models.CASCADE,
                        related_name='players')
    desbloqueada_em = models.DateTimeField(auto_now_add=True)
    em_destaque     = models.BooleanField(default=True,
                        help_text='Se True e dentro do limite, aplica o bônus')

    class Meta:
        unique_together = ('player', 'achievement')
        verbose_name = 'Conquista do Player'
        verbose_name_plural = 'Conquistas dos Players'
        ordering = ['-desbloqueada_em']

    def __str__(self):
        return f'{self.player.username} → {self.achievement.nome}'
    

# ─────────────────────────────────────────────
# BATTLE PASS
# ─────────────────────────────────────────────

class BattlePassConfig(models.Model):
    """Config por temporada — um registro por Season."""
    season      = models.OneToOneField(
        'rankings.Season', on_delete=models.CASCADE,
        related_name='battle_pass'
    )
    ativo       = models.BooleanField(default=True)
    descricao   = models.TextField(blank=True)
    criado_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Battle Pass — Config'
        verbose_name_plural = 'Battle Pass — Configs'

    def __str__(self):
        return f'Battle Pass — Season {self.season.numero}'

    @classmethod
    def get_ativo(cls):
        from apps.rankings.models import Season
        season = Season.objects.filter(ativa=True).first()
        if not season:
            return None
        return cls.objects.filter(season=season, ativo=True).first()


class BattlePassTier(models.Model):
    """Cada nível do Battle Pass com sua recompensa."""

    RECOMPENSA_TIPO_CHOICES = [
        ('coins',      'Guardian Coins'),
        ('item',       'Item (Consumível/Passivo)'),
        ('cosmetico',  'Cosmético'),
        ('xp_bonus',   'Bônus de XP temporário'),
    ]

    battle_pass  = models.ForeignKey(
        BattlePassConfig, on_delete=models.CASCADE, related_name='tiers'
    )
    tier         = models.PositiveSmallIntegerField(
        help_text='Número do nível (1 a 50)'
    )
    xp_necessario = models.PositiveIntegerField(
        help_text='XP acumulado necessário para atingir este tier'
    )

    # Recompensa
    recompensa_tipo   = models.CharField(max_length=15, choices=RECOMPENSA_TIPO_CHOICES)
    recompensa_coins  = models.PositiveSmallIntegerField(default=0,
        help_text='Coins concedidos (se tipo = coins)')
    recompensa_item   = models.ForeignKey(
        'store.Item', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='battle_pass_tiers',
        help_text='Item concedido (se tipo = item ou cosmetico)'
    )
    recompensa_descricao = models.CharField(max_length=200, blank=True,
        help_text='Descrição legível da recompensa para o front')

    class Meta:
        verbose_name = 'Battle Pass — Tier'
        verbose_name_plural = 'Battle Pass — Tiers'
        unique_together = ('battle_pass', 'tier')
        ordering = ['tier']

    def __str__(self):
        return f'BP Tier {self.tier} — {self.recompensa_descricao or self.recompensa_tipo}'


class PlayerBattlePass(models.Model):
    """Progresso do player no Battle Pass da temporada."""
    player      = models.ForeignKey(User, on_delete=models.CASCADE,
                    related_name='battle_passes')
    battle_pass = models.ForeignKey(BattlePassConfig, on_delete=models.CASCADE,
                    related_name='players')
    xp_bp       = models.PositiveIntegerField(default=0,
                    help_text='XP acumulado especificamente no Battle Pass')
    tier_atual  = models.PositiveSmallIntegerField(default=0,
                    help_text='Último tier desbloqueado')
    tiers_coletados = models.JSONField(default=list,
                    help_text='Lista de tiers já coletados pelo player')
    criado_em   = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('player', 'battle_pass')
        verbose_name = 'Battle Pass do Player'
        verbose_name_plural = 'Battle Pass dos Players'

    def __str__(self):
        return f'{self.player.username} — BP Tier {self.tier_atual}'

    def tiers_disponiveis(self):
        """Retorna tiers desbloqueados mas ainda não coletados."""
        tiers_ganhos = set(
            self.battle_pass.tiers
            .filter(xp_necessario__lte=self.xp_bp)
            .values_list('tier', flat=True)
        )
        coletados = set(self.tiers_coletados)
        return tiers_ganhos - coletados

    def proximo_tier(self):
        """Retorna o próximo tier ainda não desbloqueado."""
        return self.battle_pass.tiers.filter(
            xp_necessario__gt=self.xp_bp
        ).first()
    


class SystemLog(models.Model):
    TIPO_CHOICES = [
        ('xp_gain',       'Ganho de XP'),
        ('xp_loss',       'Perda de XP'),
        ('level_up',      'Level Up'),
        ('coin_gain',     'Ganho de Moedas'),
        ('coin_loss',     'Perda de Moedas'),
        ('item_purchase', 'Compra de Item'),
        ('item_sell',     'Venda de Item'),
        ('item_activate', 'Ativação de Consumível'),
        ('store_reroll',  'Reroll da Loja'),
        ('achievement',   'Conquista Desbloqueada'),
        ('mission_claim', 'Missão Resgatada'),
        ('battle_pass',   'Recompensa Battle Pass'),
        ('classe_change', 'Troca de Classe'),
        ('system',        'Sistema'),
    ]

    player     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='system_logs')
    tipo       = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo     = models.CharField(max_length=200)
    descricao  = models.CharField(max_length=300, blank=True)
    xp_delta   = models.IntegerField(default=0)
    coin_delta = models.IntegerField(default=0)
    breakdown  = models.JSONField(default=dict, blank=True)
    criado_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Log do Sistema'
        verbose_name_plural = 'Logs do Sistema'
        ordering            = ['-criado_em']
        indexes             = [models.Index(fields=['player', '-criado_em'])]

    def __str__(self):
        return f'{self.player.username} [{self.tipo}] {self.titulo}'