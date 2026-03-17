from django.db import models
from django.contrib.auth.models import User


class Player(models.Model):
    CLASSE_CHOICES = [
        ('guardian',  'Guardian'),
        ('analyst',   'Analyst'),
        ('sentinel',  'Sentinel'),
        ('hacker',    'Hacker'),      # Classe especial / premium
    ]

    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player')
    display_name  = models.CharField(max_length=60, blank=True)
    avatar        = models.ImageField(upload_to='avatars/', blank=True, null=True)
    classe        = models.CharField(max_length=20, choices=CLASSE_CHOICES, default='guardian')
    bio           = models.TextField(blank=True)

    # Progressão
    xp_total      = models.PositiveIntegerField(default=0)
    level         = models.PositiveSmallIntegerField(default=1)
    coins         = models.PositiveIntegerField(default=0)   # Moeda da loja

    # Streak de dias consecutivos jogando
    streak_days   = models.PositiveSmallIntegerField(default=0)
    last_play_date = models.DateField(null=True, blank=True)

    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Player'
        verbose_name_plural = 'Players'

    def __str__(self):
        return f'{self.user.username} — Lv.{self.level}'

    def xp_para_proximo_nivel(self):
        """Fórmula simples: cada nível requer level * 500 XP."""
        return self.level * 500