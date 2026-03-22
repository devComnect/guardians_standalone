from django.contrib import admin
from django.utils.html import format_html
from .models import Player, Perk, XPEvent, PlayerNotification, ClasseConfig, OfensivaConfig
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.template.response import TemplateResponse



@admin.register(ClasseConfig)
class ClasseConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Troca de Classe', {
            'description': 'Custo em coins para o player trocar de classe.',
            'fields': ('custo_troca_coins',)
        }),
    )

    def has_add_permission(self, request):
        return not ClasseConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

class LevelProgressionAdminView:
    """View extra no admin para visualizar a tabela de progressão de níveis."""
    pass

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display  = ('user', 'classe_badge', 'level', 'xp_total', 'xp_barra','coins', 'streak_days', 'ofensiva', 'created_at')
    list_filter   = ('classe', 'level')
    search_fields = ('user__username', 'display_name')
    readonly_fields = ('xp_percentual_display', 'xp_proximo_nivel_display',
                       'created_at', 'updated_at', 'classe_trocada_em')

    fieldsets = (
        ('Identidade', {'fields': ('user', 'display_name', 'avatar', 'bio')}),
        ('Classe', {'fields': ('classe', 'classe_trocada_em')}),
        ('Progressão', {'fields': ('level', 'xp_total', 'xp_percentual_display',
           'xp_proximo_nivel_display', 'coins',
           'streak_days', 'last_play_date',
           'ofensiva', 'last_challenge_date')}),
        ('Datas', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['level_table_url'] = 'level-progression/'
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('level-progression/', self.admin_site.admin_view(self.level_progression_view),
                 name='profiles_player_level_progression'),
        ]
        return custom + urls

    def level_progression_view(self, request):
        """Tabela de requisitos de XP por nível."""
        from apps.profiles.models import Player as PlayerModel
        tabela = []
        for nivel in range(1, 51):
            xp_req    = PlayerModel.xp_para_nivel(nivel)
            xp_prev   = PlayerModel.xp_para_nivel(nivel - 1) if nivel > 1 else 0
            xp_delta  = xp_req - xp_prev
            tabela.append({
                'nivel':     nivel,
                'xp_total':  xp_req,
                'xp_delta':  xp_delta,
                'dificuldade': (
                    'Fácil'  if nivel <= 10 else
                    'Médio'  if nivel <= 25 else
                    'Difícil' if nivel <= 40 else
                    'Extremo'
                )
            })

        context = {
            **self.admin_site.each_context(request),
            'title':  'Tabela de Progressão de Níveis',
            'tabela': tabela,
        }
        return TemplateResponse(request, 'admin/profiles/level_progression.html', context)

    # ── Colunas customizadas ──────────────────────

    def classe_badge(self, obj):
        cores = {
            'guardian': '#0dcaf0', 'analyst': "#e4e805",
            'sentinel': '#bd00ff', 'hacker':  '#ff2a6d',
        }
        cor = cores.get(obj.classe, '#adb5bd')
        return format_html('<span style="color:{}; font-weight:bold;">⬤ {}</span>',
                           cor, obj.get_classe_display())
    classe_badge.short_description = 'Classe'

    def xp_barra(self, obj):
        pct = obj.xp_percentual
        return format_html(
            '<div style="background:#0b0c10;border:1px solid #333;border-radius:3px;'
            'height:10px;width:120px;overflow:hidden;">'
            '<div style="background:linear-gradient(90deg,#0dcaf0,#05d9e8);'
            'width:{}%;height:100%;"></div></div>',
            pct
        )
    xp_barra.short_description = 'XP'

    def xp_percentual_display(self, obj):
        pct = obj.xp_percentual
        return mark_safe(
            f'<div style="background:#1f2833;border-radius:4px;height:14px;width:250px;overflow:hidden;">'
            f'<div style="background:linear-gradient(90deg,#0dcaf0,#05d9e8);'
            f'width:{pct}%;height:100%;border-radius:4px;"></div></div>'
            f'<small style="color:#8b949e;">{pct}% — {obj.xp_no_nivel_atual} / '
            f'{obj.xp_necessario_nivel_atual} XP para Lv.{obj.level + 1}</small>'
        )
    xp_percentual_display.short_description = 'Progresso no Nível'

    def xp_proximo_nivel_display(self, obj):
        rows = ''
        for nivel in range(max(1, obj.level - 1), min(51, obj.level + 4)):
            xp_req = obj.xp_para_nivel(nivel)
            ativo  = '→ ' if nivel == obj.level else ''
            cor    = '#0dcaf0' if nivel == obj.level else '#4a5568'
            rows  += (
                f'<tr>'
                f'<td style="color:{cor};padding:2px 8px;">{ativo}Lv.{nivel}</td>'
                f'<td style="color:{cor};padding:2px 8px;">{xp_req:,} XP total</td>'
                f'</tr>'
            )
        return mark_safe(f'<table style="font-size:0.8rem;">{rows}</table>')
    xp_proximo_nivel_display.short_description = 'Níveis Próximos'

    actions = ['conceder_xp_bonus']

    @admin.action(description='⭐ Conceder 500 XP de bônus')
    def conceder_xp_bonus(self, request, queryset):
        from apps.profiles.services import grant_xp
        count = 0
        for player in queryset:
            grant_xp(player.user, 500, 'bonus', 'Bônus concedido pelo administrador')
            count += 1
        self.message_user(request, f'500 XP concedidos a {count} player(s).')

@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ('player', 'fonte', 'xp_base', 'xp_bonus', 'xp_total', 'descricao', 'criado_em')
    list_filter  = ('fonte', 'criado_em')
    search_fields= ('player__username', 'descricao')
    readonly_fields = ('player', 'fonte', 'xp_base', 'xp_bonus', 'xp_total', 'descricao', 'criado_em')


@admin.register(PlayerNotification)
class PlayerNotificationAdmin(admin.ModelAdmin):
    list_display = ('player', 'tipo', 'titulo', 'lida', 'criado_em')
    list_filter  = ('tipo', 'lida')
    actions      = ['marcar_lidas']

    @admin.action(description='✅ Marcar como lidas')
    def marcar_lidas(self, request, queryset):
        queryset.update(lida=True)

@admin.register(OfensivaConfig)
class OfensivaConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Sistema de Ofensiva', {
            'description': (
                'A ofensiva acumula +1 por desafio concluído (máximo 1 por dia). '
                'Cada ponto de ofensiva concede +1% de bônus global de XP, '
                'limitado ao teto configurado aqui.'
            ),
            'fields': ('dias_tolerancia', 'teto_bonus_ofensiva', 'ativo')
        }),
    )

    def has_add_permission(self, request):
        return not OfensivaConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False