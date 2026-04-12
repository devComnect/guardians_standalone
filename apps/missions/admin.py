from django.contrib import admin
from .models import MissionTemplate, UserMissionSet, UserMission, MissionConfig

@admin.register(MissionConfig)
class MissionConfigAdmin(admin.ModelAdmin):
    list_display = ('reward_xp', 'reward_coins')
    fieldsets = (
        ('Recompensa por Set Completo', {
            'description': 'XP e coins concedidos quando o player conclui todas as missões do set.',
            'fields': ('reward_xp', 'reward_coins'),
        }),
    )

    def has_add_permission(self, request):
        return not MissionConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MissionTemplate)
class MissionTemplateAdmin(admin.ModelAdmin):
    list_display    = ('title', 'code', 'category', 'difficulty', 'is_active')
    list_filter     = ('category', 'difficulty', 'is_active')
    list_editable   = ('is_active',)
    search_fields   = ('title', 'code', 'description_template')
    ordering        = ('category', 'difficulty')
    fieldsets = (
        ('Template', {
            'description': 'Modelos usados para gerar missões diárias automaticamente.',
            'fields': ('title', 'description_template', 'code', 'category', 'difficulty', 'is_active'),
        }),
    )


class UserMissionInline(admin.TabularInline):
    model           = UserMission
    extra           = 0
    readonly_fields = ('title_generated', 'target_value')
    can_delete      = False


@admin.register(UserMissionSet)
class UserMissionSetAdmin(admin.ModelAdmin):
    list_display    = ('user', 'created_at', 'is_completed', 'is_claimed')
    list_filter     = ('is_completed', 'is_claimed', 'created_at')
    search_fields   = ('user__username',)
    readonly_fields = ('user', 'created_at')
    inlines         = [UserMissionInline]
    ordering        = ('-created_at',)
    actions         = ['resetar_set_missoes']

    @admin.action(description='🔄 Resetar set — gera novas missões para o player')
    def resetar_set_missoes(self, request, queryset):
        from apps.missions.services import MissionService
        count = queryset.count()
        for ms in queryset:
            ms.delete()
            MissionService.get_or_create_set(ms.user)
        self.message_user(request, f'{count} set(s) de missões resetado(s) e regenerado(s).')