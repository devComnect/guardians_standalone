from django.db import models
from django.contrib.auth.models import User


class AdminPost(models.Model):
    TIPO_CHOICES = [
        ('aviso',    'Aviso'),
        ('evento',   'Evento'),
        ('novidade', 'Novidade'),
        ('manutencao', 'Manutenção'),
    ]

    titulo     = models.CharField(max_length=200)
    conteudo   = models.TextField()
    tipo       = models.CharField(max_length=15, choices=TIPO_CHOICES, default='aviso')
    autor      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fixado     = models.BooleanField(default=False)   # Posts fixados aparecem primeiro
    publicado  = models.BooleanField(default=True)
    criado_em  = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Post do Admin'
        verbose_name_plural = 'Posts do Admin'
        ordering = ['-fixado', '-criado_em']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.titulo}'