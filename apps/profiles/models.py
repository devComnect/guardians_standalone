from django.db import models
from django.contrib.auth.models import User


# ─────────────────────────────────────────────
# PLAYER
# ─────────────────────────────────────────────

class Player(models.Model):
    CLASSE_CHOICES = [
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
    custo_troca_coins = models.PositiveIntegerField(
        default=500,
        help_text='Custo em coins para trocar de classe'
    )

    class Meta:
        verbose_name = 'Config — Troca de Classe'
        verbose_name_plural = 'Config — Troca de Classe'

    def __str__(self):
        return f'Troca de classe: {self.custo_troca_coins} coins'

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