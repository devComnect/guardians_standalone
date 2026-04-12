from django.contrib import admin
from .models import Season, RankingSnapshot

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display    = ('numero', 'nome', 'inicio', 'fim', 'dias_restantes', 'ativa')
    list_editable   = ('ativa',)
    ordering        = ('-numero',)
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'nome', 'descricao', 'ativa'),
        }),
        ('Período', {
            'fields': ('inicio', 'fim'),
        }),
        ('Prêmios', {
            'fields': ('premio_descricao',),
            'classes': ('collapse',),
        }),
    )


@admin.register(RankingSnapshot)
class RankingSnapshotAdmin(admin.ModelAdmin):
    list_display  = ('posicao', 'player', 'categoria', 'valor', 'season', 'atualizado_em')
    list_filter   = ('season', 'categoria')
    ordering      = ('categoria', 'posicao')
    search_fields = ('player__username',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False