from django.db import models
from django.contrib.auth.models import User


class Item(models.Model):
    CATEGORIA_CHOICES = [
        ('cosmetic', 'Cosmético'),   # Avatar, frames, títulos
        ('boost',    'Boost'),       # XP dobrado, streak shield, etc.
        ('action',   'Ação'),        # Pular desafio, revisar resposta, etc.
    ]

    nome        = models.CharField(max_length=100)
    descricao   = models.TextField()
    categoria   = models.CharField(max_length=15, choices=CATEGORIA_CHOICES)
    preco       = models.PositiveIntegerField()           # Em coins
    imagem      = models.ImageField(upload_to='store/', blank=True, null=True)
    disponivel  = models.BooleanField(default=True)
    season      = models.ForeignKey(                      # Null = disponível sempre
        'challenges.Season', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='items'
    )

    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Itens'

    def __str__(self):
        return f'{self.nome} ({self.get_categoria_display()}) — {self.preco} coins'


class PlayerItem(models.Model):
    """Inventário: itens que o player possui."""
    player      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory')
    item        = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantidade  = models.PositiveSmallIntegerField(default=1)
    equipado    = models.BooleanField(default=False)      # Para cosméticos
    adquirido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item do Player'
        verbose_name_plural = 'Itens dos Players'
        unique_together = ('player', 'item')

    def __str__(self):
        return f'{self.player.username} → {self.item.nome}'