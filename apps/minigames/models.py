from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class MiniGameContent(models.Model):
    """Base genérica para minigames simples (termo, anagrama, etc)."""
    TIPO_CHOICES = [
        ('anagram',     'Anagrama'),
        ('termo',       'Termo'),
        ('codebreaker', 'Codebreaker'),
        ('password',    'Montador de Senha'),
    ]
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo      = models.CharField(max_length=200)
    dados       = models.JSONField()
    dificuldade = models.CharField(max_length=10, choices=[
        ('facil','Fácil'),('medio','Médio'),('dificil','Difícil')
    ], default='medio')
    ativo       = models.BooleanField(default=True)
    criado_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Conteúdo de Minigame'
        verbose_name_plural = 'Conteúdos de Minigames'

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.titulo}'


# ─────────────────────────────────────────────
# QUIZ
# ─────────────────────────────────────────────

class Quiz(models.Model):
    titulo              = models.CharField(max_length=200)
    descricao           = models.TextField(blank=True)
    time_limit_seconds  = models.PositiveIntegerField(
        default=180,
        help_text='0 = sem limite de tempo'
    )
    xp_reward           = models.PositiveSmallIntegerField(default=0)
    coin_reward         = models.PositiveSmallIntegerField(default=0)
    available_from      = models.DateField(help_text='Data em que o quiz fica disponível')
    available_days      = models.PositiveSmallIntegerField(
        default=3,
        help_text='Por quantos dias o quiz ficará disponível'
    )
    season              = models.ForeignKey(
        'challenges.Season', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quizzes'
    )
    ativo               = models.BooleanField(default=True)
    criado_por          = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='quizzes_criados'
    )
    criado_em           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['-available_from']

    def __str__(self):
        return f'{self.titulo} ({self.available_from})'

    @property
    def available_until(self):
        from datetime import timedelta
        return self.available_from + timedelta(days=self.available_days - 1)

    def is_available_today(self):
        today = timezone.localdate()
        return self.ativo and self.available_from <= today <= self.available_until

    def total_xp_possivel(self):
        return sum(q.xp_points for q in self.questions.all())


class QuizQuestion(models.Model):
    quiz            = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text   = models.TextField()
    xp_points       = models.PositiveSmallIntegerField(default=10)
    allow_multiple  = models.BooleanField(
        default=False,
        help_text='Permite múltiplas respostas corretas'
    )
    order           = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Questão'
        verbose_name_plural = 'Questões'
        ordering = ['order']

    def __str__(self):
        return f'Q{self.order}: {self.question_text[:60]}'


class QuizOption(models.Model):
    question    = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct  = models.BooleanField(default=False)
    order       = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Opção'
        verbose_name_plural = 'Opções'
        ordering = ['order']

    def __str__(self):
        return f'{"✓" if self.is_correct else "✗"} {self.option_text[:60]}'


class QuizAttempt(models.Model):
    player          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz            = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    xp_earned       = models.PositiveSmallIntegerField(default=0)
    total_correct   = models.PositiveSmallIntegerField(default=0)
    abandoned       = models.BooleanField(default=False)
    timer_expired   = models.BooleanField(default=False)
    used_retake_token = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Tentativa de Quiz'
        verbose_name_plural = 'Tentativas de Quiz'
        ordering = ['-started_at']

    def __str__(self):
        status = 'concluída' if self.completed_at else 'em andamento'
        return f'{self.player.username} → {self.quiz.titulo} [{status}]'

    @property
    def is_completed(self):
        return self.completed_at is not None

    def remaining_seconds(self):
        """Calcula tempo restante com base no servidor — anti-cheat."""
        if not self.quiz.time_limit_seconds:
            return 0
        from datetime import timezone as dt_tz
        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = self.quiz.time_limit_seconds - elapsed
        return max(0, int(remaining))
    

# ─────────────────────────────────────────────
# PATRULHA DIÁRIA (Codebreaker)
# ─────────────────────────────────────────────

class PatrolAttempt(models.Model):
    player          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patrol_attempts')
    date            = models.DateField(default=timezone.localdate)
    secret          = models.CharField(max_length=4)
    guesses         = models.JSONField(default=list)
    attempts_count  = models.PositiveSmallIntegerField(default=0)
    completed       = models.BooleanField(default=False)
    won             = models.BooleanField(default=False)
    xp_earned       = models.PositiveSmallIntegerField(default=0)
    coins_earned    = models.PositiveSmallIntegerField(default=0)
    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Tentativa de Patrulha'
        verbose_name_plural = 'Tentativas de Patrulha'
        unique_together = ('player', 'date')
        ordering = ['-date']

    def __str__(self):
        status = 'Venceu' if self.won else ('Completa' if self.completed else 'Em andamento')
        return f'{self.player.username} — Patrulha {self.date} [{status}]'
    

# ─────────────────────────────────────────────
# COFRE DE SENHAS (Password Game)
# ─────────────────────────────────────────────

class PasswordGameConfig(models.Model):
    """Configuração global do jogo — apenas 1 registro."""
    time_limit_seconds  = models.PositiveIntegerField(default=300, help_text='0 = sem limite')
    xp_reward           = models.PositiveSmallIntegerField(default=100)
    coin_reward         = models.PositiveSmallIntegerField(default=2)
    rules_count_easy    = models.PositiveSmallIntegerField(default=2)
    rules_count_medium  = models.PositiveSmallIntegerField(default=2)
    rules_count_hard    = models.PositiveSmallIntegerField(default=1)
    active_days         = models.CharField(
        max_length=20, default='0,1,2,3,4,5,6',
        help_text='Dias da semana separados por vírgula (0=Seg, 6=Dom)'
    )
    ativo               = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Config: Cofre de Senhas'
        verbose_name_plural = 'Config: Cofre de Senhas'

    def __str__(self):
        return f'Configuração do Cofre de Senhas'

    def save(self, *args, **kwargs):
        # Garante singleton
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_active_today(self):
        today = timezone.localdate().weekday()
        allowed = [d.strip() for d in self.active_days.split(',')]
        return str(today) in allowed


class PasswordAttempt(models.Model):
    player          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_attempts')
    rules_sequence  = models.JSONField(default=list)
    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    is_won          = models.BooleanField(default=False)
    xp_earned       = models.PositiveSmallIntegerField(default=0)
    coins_earned    = models.PositiveSmallIntegerField(default=0)
    input_password  = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'Tentativa: Cofre de Senhas'
        verbose_name_plural = 'Tentativas: Cofre de Senhas'
        ordering = ['-started_at']

    def __str__(self):
        status = 'Venceu' if self.is_won else ('Completa' if self.completed_at else 'Em andamento')
        return f'{self.player.username} — Cofre [{status}]'

    def remaining_seconds(self):
        config = PasswordGameConfig.get()
        if not config.time_limit_seconds:
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, int(config.time_limit_seconds - elapsed))