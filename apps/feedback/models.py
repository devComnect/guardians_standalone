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
    anexo = models.ImageField(
        upload_to='feedback_anexos/',
        blank=True, null=True,
        help_text='Apenas imagens (PNG, JPG, WEBP). Máx. 5MB.'
    )
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='aberto')
    anonimo     = models.BooleanField(default=False)   # Player pode enviar sem identificação
    criado_em   = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    coin_reward     = models.PositiveSmallIntegerField(default=0,
        help_text='Moedas a conceder ao player. Preenchido automaticamente ao marcar como resolvido.')
    coins_collected = models.BooleanField(default=False,
        verbose_name='Moedas coletadas pelo player')

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'
        ordering = ['-criado_em']

    def __str__(self):
        autor = 'Anônimo' if self.anonimo else self.player.username if self.player else 'N/A'
        return f'[{self.get_tipo_display()}] {self.titulo} — {autor}'
    


class FeedbackCoinConfig(models.Model):
    """Tabela de recompensas por tipo — singleton editável pelo admin."""
    coins_sugestao_implementada = models.PositiveSmallIntegerField(default=2,
        verbose_name='Sugestão implementada')
    coins_feedback_valido       = models.PositiveSmallIntegerField(default=1,
        verbose_name='Feedback válido')
    coins_bug_confirmado        = models.PositiveSmallIntegerField(default=3,
        verbose_name='Bug confirmado')
    coins_vulnerabilidade       = models.PositiveSmallIntegerField(default=5,
        verbose_name='Vulnerabilidade confirmada')

    class Meta:
        verbose_name = 'Config — Recompensas de Feedback'
        verbose_name_plural = 'Config — Recompensas de Feedback'

    def __str__(self):
        return 'Configuração de Recompensas'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def coins_para_tipo(self, tipo):
        mapa = {
            'sugestao':        self.coins_sugestao_implementada,
            'feedback':        self.coins_feedback_valido,
            'bug':             self.coins_bug_confirmado,
            'vulnerabilidade': self.coins_vulnerabilidade,
        }
        return mapa.get(tipo, 0)