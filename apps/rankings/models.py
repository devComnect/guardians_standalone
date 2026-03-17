from django.db import models
from django.contrib.auth.models import User


class Ranking(models.Model):
    """
    Snapshot do ranking por temporada.
    Calculado periodicamente (daily job) — não em tempo real.
    """
    season      = models.ForeignKey('challenges.Season', on_delete=models.CASCADE, related_name='rankings')
    player      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rankings')
    posicao     = models.PositiveSmallIntegerField()
    xp_season   = models.PositiveIntegerField(default=0)    # XP acumulado na temporada
    desafios_concluidos = models.PositiveSmallIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ranking'
        verbose_name_plural = 'Rankings'
        ordering = ['posicao']
        unique_together = ('season', 'player')

    def __str__(self):
        return f'#{self.posicao} {self.player.username} — Season {self.season.numero}'