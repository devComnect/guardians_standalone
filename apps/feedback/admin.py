from django.contrib import admin
from django.utils.html import format_html
from .models import Feedback, FeedbackCoinConfig


@admin.register(FeedbackCoinConfig)
class FeedbackCoinConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('💰 Moedas por tipo de contribuição', {
            'description': 'Defina quantas moedas cada tipo de feedback válido concede ao player. '
                           'O valor é atribuído automaticamente ao marcar o feedback como Resolvido.',
            'fields': (
                'coins_sugestao_implementada',
                'coins_feedback_valido',
                'coins_bug_confirmado',
                'coins_vulnerabilidade',
            )
        }),
    )

    def has_add_permission(self, request):
        return not FeedbackCoinConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'tipo_badge', 'status', 'status_badge',
                     'autor_display', 'coin_reward', 'coins_collected', 'anexo_link', 'criado_em')
    list_filter   = ('tipo', 'status', 'anonimo', 'coins_collected', 'criado_em')
    list_editable = ('status',)
    search_fields = ('titulo', 'descricao', 'player__username')
    readonly_fields = ('player', 'tipo', 'titulo', 'descricao', 'anonimo',
                       'criado_em', 'atualizado_em', 'preview_anexo', 'coins_collected')
    ordering = ('-criado_em',)

    fieldsets = (
        ('Conteúdo', {
            'fields': ('tipo', 'titulo', 'descricao')
        }),
        ('Remetente', {
            'fields': ('player', 'anonimo')
        }),
        ('Anexo', {
            'fields': ('preview_anexo',)
        }),
        ('Gestão & Recompensa', {
            'fields': ('status', 'coin_reward', 'coins_collected', 'criado_em', 'atualizado_em'),
            'description': 'Ao marcar como Resolvido, o coin_reward é preenchido automaticamente '
                           'com base na tabela de configuração. Você pode ajustar manualmente.'
        }),
    )

    # ── Colunas ───────────────────────────────────

    def tipo_badge(self, obj):
        cores = {
            'sugestao':        ('#0dcaf0', '💡'),
            'feedback':        ('#05d9e8', '💬'),
            'bug':             ('#fcee0a', '🐛'),
            'vulnerabilidade': ('#ff2a6d', '🛡️'),
        }
        cor, icone = cores.get(obj.tipo, ('#adb5bd', '•'))
        return format_html('<span style="color:{}; font-weight:bold;">{} {}</span>',
                           cor, icone, obj.get_tipo_display())
    tipo_badge.short_description = 'Tipo'

    def status_badge(self, obj):
        cores = {
            'aberto':     '#adb5bd',
            'em_analise': '#fcee0a',
            'resolvido':  '#05d9e8',
            'descartado': '#555',
        }
        cor = cores.get(obj.status, '#adb5bd')
        return format_html('<span style="color:{};">⬤ {}</span>', cor, obj.get_status_display())
    status_badge.short_description = 'Status'

    def autor_display(self, obj):
        if obj.anonimo:
            return format_html('<span style="color:#555;">— Anônimo</span>')
        return obj.player.username if obj.player else '—'
    autor_display.short_description = 'Autor'

    def anexo_link(self, obj):
        if obj.anexo:
            return format_html('<a href="{}" target="_blank" style="color:#0dcaf0;">📎 Ver</a>',
                               obj.anexo.url)
        return '—'
    anexo_link.short_description = 'Anexo'

    def preview_anexo(self, obj):
        if obj.anexo:
            return format_html(
                '<img src="{}" style="max-width:600px; max-height:400px; '
                'border:1px solid #333; border-radius:4px;" />', obj.anexo.url)
        return 'Sem anexo.'
    preview_anexo.short_description = 'Preview'

    # ── Save: preenche coin_reward automaticamente ──

    def save_model(self, request, obj, form, change):
        # Ao mudar para resolvido, define coin_reward se ainda estiver zerado
        if obj.status == 'resolvido' and obj.coin_reward == 0:
            config = FeedbackCoinConfig.get()
            obj.coin_reward = config.coins_para_tipo(obj.tipo)
        super().save_model(request, obj, form, change)

    # ── Ações em massa ────────────────────────────

    actions = ['marcar_em_analise', 'marcar_resolvido', 'marcar_descartado']

    @admin.action(description='🔍 Marcar como Em Análise')
    def marcar_em_analise(self, request, queryset):
        count = queryset.update(status='em_analise')
        self.message_user(request, f'{count} feedback(s) marcado(s) como Em Análise.')

    @admin.action(description='✅ Marcar como Resolvido (atribui moedas)')
    def marcar_resolvido(self, request, queryset):
        config = FeedbackCoinConfig.get()
        count  = 0
        for fb in queryset:
            if fb.status != 'resolvido':
                fb.status = 'resolvido'
                if fb.coin_reward == 0:
                    fb.coin_reward = config.coins_para_tipo(fb.tipo)
                fb.save()
                count += 1
        self.message_user(request, f'{count} feedback(s) marcado(s) como Resolvido.')

    @admin.action(description='🗑️ Marcar como Descartado')
    def marcar_descartado(self, request, queryset):
        count = queryset.update(status='descartado')
        self.message_user(request, f'{count} feedback(s) marcado(s) como Descartado.')