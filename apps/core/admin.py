from django.contrib import admin
from .models import AdminPost

@admin.register(AdminPost)
class AdminPostAdmin(admin.ModelAdmin):
    list_display    = ('titulo', 'tipo_badge', 'autor', 'fixado', 'publicado', 'criado_em')
    list_filter     = ('tipo', 'fixado', 'publicado')
    list_editable   = ('fixado', 'publicado')
    search_fields   = ('titulo', 'conteudo')
    readonly_fields = ('criado_em', 'atualizado_em', 'autor')
    ordering        = ('-fixado', '-criado_em')

    fieldsets = (
        ('Publicação', {
            'fields': ('tipo', 'titulo', 'conteudo', 'fixado', 'publicado'),
        }),
        ('Auditoria', {
            'fields': ('autor', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',),
        }),
    )

    def tipo_badge(self, obj):
        from django.utils.html import format_html
        cores = {
            'aviso':       '#ffc107',
            'novidade':    '#0dcaf0',
            'manutencao':  '#dc3545',
            'evento':      '#6f42c1',
        }
        cor = cores.get(obj.tipo, '#adb5bd')
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            cor, obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.autor = request.user
        super().save_model(request, obj, form, change)