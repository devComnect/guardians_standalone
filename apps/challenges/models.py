from django.db import models
from django.contrib.auth.models import User


class Season(models.Model):
    nome       = models.CharField(max_length=100)
    numero     = models.PositiveSmallIntegerField(unique=True)
    inicio     = models.DateField()
    fim        = models.DateField()
    ativa      = models.BooleanField(default=False)
    descricao  = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Temporada'
        verbose_name_plural = 'Temporadas'
        ordering = ['-numero']

    def __str__(self):
        return f'Season {self.numero} — {self.nome}'

    def save(self, *args, **kwargs):
        # Garante que só uma temporada fica ativa por vez
        if self.ativa:
            Season.objects.exclude(pk=self.pk).update(ativa=False)
        super().save(*args, **kwargs)


class Challenge(models.Model):
    TIPO_CHOICES = [
        ('quiz',        'Quiz'),
        ('anagram',     'Anagrama'),
        ('termo',       'Termo (Wordle)'),
        ('codebreaker', 'Codebreaker'),
        ('password',    'Montador de Senha'),
    ]

    DIFICULDADE_CHOICES = [
        ('facil',  'Fácil'),
        ('medio',  'Médio'),
        ('dificil','Difícil'),
    ]

    season      = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='challenges')
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo      = models.CharField(max_length=200)
    descricao   = models.TextField(blank=True)
    dificuldade = models.CharField(max_length=10, choices=DIFICULDADE_CHOICES, default='medio')
    xp_reward   = models.PositiveSmallIntegerField(default=100)
    coin_reward = models.PositiveSmallIntegerField(default=10)
    data        = models.DateField()          # Dia em que o desafio fica disponível
    ativo       = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Desafio'
        verbose_name_plural = 'Desafios'
        ordering = ['data']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.titulo} — {self.data}'


class PlayerChallenge(models.Model):
    """Registro de conclusão de um desafio por um player."""
    player      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_challenges')
    challenge   = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='completions')
    concluido   = models.BooleanField(default=False)
    score       = models.PositiveSmallIntegerField(default=0)   # Pontuação dentro do minigame
    tentativas  = models.PositiveSmallIntegerField(default=0)
    tempo_gasto = models.PositiveSmallIntegerField(default=0)   # Em segundos
    concluido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Desafio do Player'
        verbose_name_plural = 'Desafios dos Players'
        unique_together = ('player', 'challenge')   # Não repete o mesmo desafio

    def __str__(self):
        return f'{self.player.username} → {self.challenge}'