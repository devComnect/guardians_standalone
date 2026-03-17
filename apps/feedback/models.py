from django.db import models
from django.contrib.auth.models import User


class Feedback(models.Model):
    TIPO_CHOICES = [
        ('sugestao',        'Sugestão'),
        ('feedback',        'Feedback'),
        ('bug',             'Reporte de Bug'),
        ('vulnerabilidade', 'Reporte de Vulnerabilidade'),
    ]

    STATUS_CHOICES = [
        ('aberto',      'Aberto'),
        ('em_analise',  'Em Análise'),
        ('resolvido',   'Resolvido'),
        ('descartado',  'Descartado'),
    ]

    player      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='feedbacks')
    tipo        = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo      = models.CharField(max_length=200)
    descricao   = models.TextField()
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='aberto')
    anonimo     = models.BooleanField(default=False)   # Player pode enviar sem identificação
    criado_em   = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'
        ordering = ['-criado_em']

    def __str__(self):
        autor = 'Anônimo' if self.anonimo else self.player.username if self.player else 'N/A'
        return f'[{self.get_tipo_display()}] {self.titulo} — {autor}'