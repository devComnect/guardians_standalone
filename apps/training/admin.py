from django.contrib import admin
from .models import PlayerWordUnlock


@admin.register(PlayerWordUnlock)
class PlayerWordUnlockAdmin(admin.ModelAdmin):
    list_display  = ('player', 'word', 'season', 'unlocked_at')
    list_filter   = ('season', 'word__categoria', 'word__dificuldade')
    search_fields = ('player__username', 'word__palavra')
    readonly_fields = ('unlocked_at',)
    actions = ['resetar_desbloqueios']

    @admin.action(description='Resetar desbloqueios selecionados')
    def resetar_desbloqueios(self, request, queryset):
        total = queryset.count()
        queryset.delete()
        self.message_user(request, f'{total} desbloqueio(s) removido(s).')