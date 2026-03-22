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
    
class Season(models.Model):
    numero    = models.PositiveSmallIntegerField(unique=True)
    nome      = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    inicio    = models.DateField()
    fim       = models.DateField()
    ativa     = models.BooleanField(default=False)
    premio_descricao = models.TextField(blank=True, help_text='Descrição dos prêmios desta temporada')

    class Meta:
        verbose_name = 'Temporada'
        verbose_name_plural = 'Temporadas'
        ordering = ['-numero']

    def __str__(self):
        return f'Season {self.numero} — {self.nome}'

    def save(self, *args, **kwargs):
        if self.ativa:
            Season.objects.exclude(pk=self.pk).update(ativa=False)
        super().save(*args, **kwargs)

    @property
    def dias_restantes(self):
        from django.utils import timezone
        delta = self.fim - timezone.localdate()
        return max(0, delta.days)


class RankingSnapshot(models.Model):
    """
    Calculado diariamente via management command.
    Separado por categoria para suportar múltiplos rankings.
    """
    CATEGORIA_CHOICES = [
        ('xp',      'XP — Experiência'),
        ('moedas',  'Moedas'),
        ('ofensiva','Ofensiva — Desafios completados'),
    ]

    season    = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='snapshots')
    player    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ranking_snapshots')
    categoria = models.CharField(max_length=15, choices=CATEGORIA_CHOICES)
    posicao   = models.PositiveSmallIntegerField()
    valor     = models.PositiveIntegerField(default=0)   # XP, coins ou qtd desafios
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Snapshot de Ranking'
        verbose_name_plural = 'Snapshots de Ranking'
        unique_together = ('season', 'player', 'categoria')
        ordering = ['posicao']

    def __str__(self):
        return f'#{self.posicao} {self.player.username} [{self.categoria}] S{self.season.numero}'