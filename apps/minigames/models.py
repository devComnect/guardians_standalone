from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random


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
# BANCO DE PALAVRAS (compartilhado)
# ─────────────────────────────────────────────

class WordBank(models.Model):
    CATEGORIA_CHOICES = [
        ('ciberseguranca', 'Cibersegurança'),
        ('redes',          'Redes'),
        ('ti',             'Tecnologia da Informação'),
        ('politicas',      'Políticas e Compliance'),
    ]
    DIFICULDADE_CHOICES = [
        ('facil',   'Fácil'),
        ('medio',   'Médio'),
        ('dificil', 'Difícil'),
    ]

    palavra     = models.CharField(max_length=30, unique=True)
    dica        = models.CharField(max_length=300, blank=True)
    categoria   = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    dificuldade = models.CharField(max_length=10, choices=DIFICULDADE_CHOICES)
    comprimento = models.PositiveSmallIntegerField(editable=False)
    ativo       = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.palavra    = self.palavra.upper().strip()
        self.comprimento = len(self.palavra)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Palavra — Banco'
        verbose_name_plural = 'Banco de Palavras'
        ordering = ['dificuldade', 'comprimento', 'palavra']

    def __str__(self):
        return f'{self.palavra} ({self.comprimento}L / {self.get_dificuldade_display()})'


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
    
# ─────────────────────────────────────────────
# DECRIPTAR (Anagrama)
# ─────────────────────────────────────────────

class DecriptarConfig(models.Model):
    """Configuração singleton do jogo Decriptar."""
    time_limit_seconds = models.PositiveIntegerField(default=0,  help_text='0 = sem limite')
    xp_per_word        = models.PositiveSmallIntegerField(default=50)
    coin_reward        = models.PositiveSmallIntegerField(default=15)
    words_count_easy   = models.PositiveSmallIntegerField(default=2, verbose_name='Palavras fáceis / sessão')
    words_count_medio  = models.PositiveSmallIntegerField(default=2, verbose_name='Palavras médias / sessão')
    words_count_hard   = models.PositiveSmallIntegerField(default=1, verbose_name='Palavras difíceis / sessão')
    max_lives          = models.PositiveSmallIntegerField(default=3)
    ativo              = models.BooleanField(default=True)

    # Dias da semana (booleanos — mais amigável no admin)
    day_seg = models.BooleanField(default=True,  verbose_name='Segunda-feira')
    day_ter = models.BooleanField(default=False, verbose_name='Terça-feira')
    day_qua = models.BooleanField(default=False, verbose_name='Quarta-feira')
    day_qui = models.BooleanField(default=False, verbose_name='Quinta-feira')
    day_sex = models.BooleanField(default=True,  verbose_name='Sexta-feira')
    day_sab = models.BooleanField(default=False, verbose_name='Sábado')
    day_dom = models.BooleanField(default=False, verbose_name='Domingo')

    class Meta:
        verbose_name = 'Config — Decriptar'
        verbose_name_plural = 'Config — Decriptar'

    def __str__(self):
        return 'Configuração Decriptar'

    def is_active_today(self):
        today = timezone.localdate().weekday()  # 0=Seg
        days  = [self.day_seg, self.day_ter, self.day_qua,
                 self.day_qui, self.day_sex, self.day_sab, self.day_dom]
        return self.ativo and days[today]

    def total_words(self):
        return self.words_count_easy + self.words_count_medio + self.words_count_hard

    def select_words(self):
        """Seleciona palavras do banco de forma aleatória. Fonte de verdade server-side."""
        def pick(dif, count):
            pool = list(WordBank.objects.filter(ativo=True, dificuldade=dif).values('id', 'palavra', 'dica'))
            return random.sample(pool, min(count, len(pool)))

        words = (pick('facil', self.words_count_easy) +
                 pick('medio', self.words_count_medio) +
                 pick('dificil', self.words_count_hard))
        random.shuffle(words)
        return words  # [{'id': X, 'palavra': '...', 'dica': '...'}, ...]


class DecriptarAttempt(models.Model):
    player          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decriptar_attempts')
    config          = models.ForeignKey(DecriptarConfig, on_delete=models.CASCADE)
    date            = models.DateField()
    words_sequence  = models.JSONField(default=list)   # Palavras selecionadas (server-side)
    correct_count   = models.PositiveSmallIntegerField(default=0)
    lives_remaining = models.PositiveSmallIntegerField(default=3)
    xp_earned       = models.PositiveSmallIntegerField(default=0)
    coins_earned    = models.PositiveSmallIntegerField(default=0)
    abandoned       = models.BooleanField(default=False)
    timer_expired   = models.BooleanField(default=False)
    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('player', 'date')
        verbose_name        = 'Tentativa — Decriptar'
        verbose_name_plural = 'Tentativas — Decriptar'
        ordering = ['-date']

    def __str__(self):
        return f'{self.player.username} — Decriptar {self.date}'

    def remaining_seconds(self):
        if not self.config.time_limit_seconds:
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, int(self.config.time_limit_seconds - elapsed))

    @property
    def is_completed(self):
        return self.completed_at is not None


# ─────────────────────────────────────────────
# CÓDIGO (Termo / Wordle)
# ─────────────────────────────────────────────

class CodigoConfig(models.Model):
    """Configuração singleton do jogo Código."""
    DIFICULDADE_CHOICES = [
        ('facil',   'Fácil'),
        ('medio',   'Médio'),
        ('dificil', 'Difícil'),
    ]

    time_limit_seconds = models.PositiveIntegerField(default=0,  help_text='0 = sem limite')
    xp_reward          = models.PositiveSmallIntegerField(default=200)
    coin_reward        = models.PositiveSmallIntegerField(default=20)
    word_length        = models.PositiveSmallIntegerField(default=5,
                            help_text='Comprimento da palavra (filtra banco automaticamente)')
    max_attempts       = models.PositiveSmallIntegerField(default=6)
    dificuldade        = models.CharField(max_length=10, choices=DIFICULDADE_CHOICES, default='medio')
    ativo              = models.BooleanField(default=True)

    day_seg = models.BooleanField(default=False, verbose_name='Segunda-feira')
    day_ter = models.BooleanField(default=True,  verbose_name='Terça-feira')
    day_qua = models.BooleanField(default=False, verbose_name='Quarta-feira')
    day_qui = models.BooleanField(default=True,  verbose_name='Quinta-feira')
    day_sex = models.BooleanField(default=False, verbose_name='Sexta-feira')
    day_sab = models.BooleanField(default=False, verbose_name='Sábado')
    day_dom = models.BooleanField(default=False, verbose_name='Domingo')

    class Meta:
        verbose_name = 'Config — Código'
        verbose_name_plural = 'Config — Código'

    def __str__(self):
        return f'Configuração Código ({self.word_length} letras / {self.get_dificuldade_display()})'

    def is_active_today(self):
        today = timezone.localdate().weekday()
        days  = [self.day_seg, self.day_ter, self.day_qua,
                 self.day_qui, self.day_sex, self.day_sab, self.day_dom]
        return self.ativo and days[today]

    def select_word(self):
        """
        Escolhe uma palavra do banco.
        - Filtra pelo comprimento configurado
        - Dificuldade rotaciona automaticamente para garantir variedade
        - Retorna o objeto WordBank diretamente
        """
        from apps.minigames.models import WordBank
        import random

        # Tenta na ordem: medio → facil → dificil (fallback completo)
        dificuldades = ['medio', 'facil', 'dificil']
        
        for dif in dificuldades:
            pool = list(
                WordBank.objects.filter(
                    ativo=True,
                    comprimento=self.word_length,
                    dificuldade=dif,
                )
            )
            if pool:
                return random.choice(pool)

        # Último recurso: qualquer palavra com o comprimento certo
        pool = list(WordBank.objects.filter(ativo=True, comprimento=self.word_length))
        return random.choice(pool) if pool else None


class CodigoAttempt(models.Model):
    player       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='codigo_attempts')
    config       = models.ForeignKey(CodigoConfig, on_delete=models.CASCADE)
    date         = models.DateField()
    secret_word  = models.CharField(max_length=20)  # Armazenada no servidor — nunca enviada ao cliente
    # Formato: [{'guess': 'SENHA', 'feedback': ['correct','absent',...]}, ...]
    guesses      = models.JSONField(default=list)
    won          = models.BooleanField(default=False)
    xp_earned    = models.PositiveSmallIntegerField(default=0)
    coins_earned = models.PositiveSmallIntegerField(default=0)
    abandoned    = models.BooleanField(default=False)
    timer_expired= models.BooleanField(default=False)
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('player', 'date', 'config')
        verbose_name        = 'Tentativa — Código'
        verbose_name_plural = 'Tentativas — Código'
        ordering = ['-date']

    def __str__(self):
        return f'{self.player.username} — Código {self.date}'

    def remaining_seconds(self):
        if not self.config.time_limit_seconds:
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, int(self.config.time_limit_seconds - elapsed))

    @property
    def is_completed(self):
        return self.completed_at is not None

    @staticmethod
    def check_guess(guess, secret):
        """
        Algoritmo Wordle padrão — server-side.
        Retorna lista de status: 'correct' | 'present' | 'absent'
        """
        result           = ['absent'] * len(guess)
        secret_remaining = list(secret)

        # 1ª passagem: posições exatas
        for i, (g, s) in enumerate(zip(guess, secret)):
            if g == s:
                result[i]           = 'correct'
                secret_remaining[i] = None

        # 2ª passagem: letras presentes em posição errada
        for i, g in enumerate(guess):
            if result[i] == 'correct':
                continue
            if g in secret_remaining:
                result[i] = 'present'
                secret_remaining[secret_remaining.index(g)] = None

        return result