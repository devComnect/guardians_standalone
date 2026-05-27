from django.db import models
from django.contrib.auth.models import User


class PlayerWordUnlock(models.Model):
    player      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='word_unlocks')
    word        = models.ForeignKey('minigames.WordBank', on_delete=models.CASCADE, related_name='unlocks')
    season      = models.ForeignKey('rankings.Season', on_delete=models.CASCADE, related_name='word_unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'word', 'season')
        verbose_name = 'Palavra Desbloqueada'
        verbose_name_plural = 'Palavras Desbloqueadas'
        ordering = ['-unlocked_at']

    def __str__(self):
        return f'{self.player.username} → {self.word.palavra} [{self.season}]'