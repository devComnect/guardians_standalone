from django.contrib import admin
from .models import AdminPost


@admin.register(AdminPost)
class AdminPostAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'tipo', 'autor', 'fixado', 'publicado', 'criado_em')
    list_filter   = ('tipo', 'fixado', 'publicado')
    list_editable = ('fixado', 'publicado')
    search_fields = ('titulo', 'conteudo')
    readonly_fields = ('criado_em', 'atualizado_em')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.autor = request.user
        super().save_model(request, obj, form, change)