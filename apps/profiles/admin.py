from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Player, Perk, XPEvent, PlayerNotification, ClasseConfig, OfensivaConfig, Achievement, PlayerAchievement, AchievementConfig
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
    list_display = ('user', 'classe_badge', 'level', 'xp_total', 'xp_barra',
                'coins', 'streak_days', 'ofensiva', 'link_conquistas', 'created_at')
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

    def link_conquistas(self, obj):
        from django.urls import reverse
        url = reverse('admin:profiles_player_conquistas', args=[obj.pk])
        total = obj.user.achievements.count()
        return format_html(
            '<a href="{}" style="color:#0dcaf0;">🏆 {} conquista(s)</a>',
            url, total
        )
    link_conquistas.short_description = 'Conquistas'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['level_table_url'] = 'level-progression/'
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('level-progression/',
                self.admin_site.admin_view(self.level_progression_view),
                name='profiles_player_level_progression'),
            path('<int:player_id>/conquistas/',
                self.admin_site.admin_view(self.gerenciar_conquistas_view),
                name='profiles_player_conquistas'),
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
    def gerenciar_conquistas_view(self, request, player_id):
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponseRedirect
        from apps.profiles.models import Achievement, PlayerAchievement, AchievementConfig
        from apps.profiles.services import verificar_conquistas

        player_obj = get_object_or_404(self.model, pk=player_id)
        user       = player_obj.user

        # ── POST: conceder ou remover conquista
        if request.method == 'POST':
            action       = request.POST.get('action')
            achievement_id = request.POST.get('achievement_id')

            if action == 'grant' and achievement_id:
                ach = Achievement.objects.filter(pk=achievement_id).first()
                if ach:
                    pa, created = PlayerAchievement.objects.get_or_create(
                        player=user, achievement=ach,
                        defaults={'em_destaque': True}
                    )
                    msg = f'Conquista "{ach.nome}" concedida.' if created else 'Player já possui essa conquista.'
                    self.message_user(request, msg)

            elif action == 'revoke' and achievement_id:
                deleted, _ = PlayerAchievement.objects.filter(
                    player=user, achievement_id=achievement_id
                ).delete()
                if deleted:
                    self.message_user(request, f'Conquista removida.', messages.WARNING)

            elif action == 'revoke_all':
                count = PlayerAchievement.objects.filter(player=user).count()
                PlayerAchievement.objects.filter(player=user).delete()
                self.message_user(request, f'{count} conquista(s) removida(s).', messages.WARNING)

            elif action == 'trigger_all':
                # Dispara todos os triggers para o player — útil para debug
                triggers = [
                    'quiz_count', 'quiz_perfect', 'decriptar_count', 'codigo_count',
                    'patrol_count', 'minigame_count', 'all_daily_count',
                    'level_reached', 'streak_days', 'ofensiva', 'xp_total',
                    'shop_count', 'feedback_count', 'vulnerability',
                    'season_top1', 'season_top3',
                ]
                novas = []
                for t in triggers:
                    novas += verificar_conquistas(user, t)
                self.message_user(
                    request,
                    f'{len(novas)} conquista(s) desbloqueada(s) via trigger automático.'
                )

            return HttpResponseRedirect(request.path)

        # ── GET: monta contexto
        todas           = Achievement.objects.filter(ativo=True).order_by('trigger_type', 'trigger_value')
        player_ach_ids  = set(
            PlayerAchievement.objects.filter(player=user).values_list('achievement_id', flat=True)
        )
        player_achs     = PlayerAchievement.objects.filter(player=user).select_related('achievement')
        config          = AchievementConfig.get()

        context = {
            **self.admin_site.each_context(request),
            'title':           f'Conquistas — {user.username}',
            'player_obj':      player_obj,
            'todas':           todas,
            'player_ach_ids':  player_ach_ids,
            'player_achs':     player_achs,
            'config':          config,
            'opts':            self.model._meta,
        }
        return TemplateResponse(request, 'admin/profiles/gerenciar_conquistas.html', context)



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

    actions = ['conceder_xp_bonus', 'reset_total_player']

    @admin.action(description='⭐ Conceder 500 XP de bônus')
    def conceder_xp_bonus(self, request, queryset):
        from apps.profiles.services import grant_xp
        for player in queryset:
            grant_xp(player.user, 500, 'bonus', 'Bônus concedido pelo administrador')
        self.message_user(request, f'500 XP concedidos a {queryset.count()} player(s).')

    @admin.action(description='🗑️ RESET TOTAL — zera tudo do player')
    def reset_total_player(self, request, queryset):
        from apps.minigames.models import (
            QuizAttempt, DecriptarAttempt, CodigoAttempt,
            PatrolAttempt, PasswordAttempt,
        )
        from apps.profiles.models import (
            XPEvent, PlayerNotification, PlayerAchievement,
        )
        from apps.rankings.models import RankingSnapshot
        from apps.missions.models import UserMissionSet
        from apps.missions.services import MissionService
        from apps.store.models import PlayerItem, ActiveEffect, DailyStore, StoreTransaction


        count = queryset.count()
        for player_obj in queryset:
            user = player_obj.user

            # ── Missões
            UserMissionSet.objects.filter(user=user).delete()
            MissionService.get_or_create_set(user)

            # ── Tentativas
            QuizAttempt.objects.filter(player=user).delete()
            DecriptarAttempt.objects.filter(player=user).delete()
            CodigoAttempt.objects.filter(player=user, config__isnull=False).delete()
            CodigoAttempt.objects.filter(player=user).delete()

            try:
                PatrolAttempt.objects.filter(player=user).delete()
            except Exception:
                pass
            try:
                PasswordAttempt.objects.filter(player=user).delete()
            except Exception:
                pass

            # ── Histórico e notificações
            XPEvent.objects.filter(player=user).delete()
            PlayerNotification.objects.filter(player=user).delete()
            PlayerAchievement.objects.filter(player=user).delete()
            RankingSnapshot.objects.filter(player=user).delete()

            # ── Loja: itens, compras e consumíveis ativos
            itens_count        = PlayerItem.objects.filter(player=user).count()
            efeitos_count      = ActiveEffect.objects.filter(player=user).count()
            loja_diaria_count  = DailyStore.objects.filter(player=user).count()
            transacoes_count   = StoreTransaction.objects.filter(player=user).count()

            PlayerItem.objects.filter(player=user).delete()
            ActiveEffect.objects.filter(player=user).delete()
            DailyStore.objects.filter(player=user).delete()
            StoreTransaction.objects.filter(player=user).delete()  # ⚠️ ambiente de teste apenas

            # ── Zera o perfil do player
            player_obj.xp_total            = 0
            player_obj.level               = 1
            player_obj.coins               = 0
            player_obj.streak_days         = 0
            player_obj.ofensiva            = 0
            player_obj.last_play_date      = None
            player_obj.last_challenge_date = None
            player_obj.classe_trocada_em   = None
            player_obj.save()

            print(f"[RESET DEBUG] Usuário: {user.username}")
            print(f"  ├─ Itens removidos:           {itens_count}")
            print(f"  ├─ Efeitos ativos removidos:  {efeitos_count}")
            print(f"  ├─ Lojas diárias removidas:   {loja_diaria_count}")
            print(f"  ├─ Transações removidas:      {transacoes_count}")
            print(f"  └─ Perfil zerado ✅")

        self.message_user(
            request,
            (
                f'✅ Reset total aplicado para {count} player(s). '
                f'Tentativas, XP, coins, conquistas, notificações, '
                f'itens, efeitos ativos, loja diária e transações foram removidos.'
            ),
            messages.WARNING,
        )

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
    

@admin.register(AchievementConfig)
class AchievementConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Configuração de Destaques', {
            'description': (
                'Define quantas conquistas um player pode ter em destaque '
                'simultaneamente para aplicar bônus. '
                'Conquistas ganhas entram em destaque automaticamente — '
                'o player pode gerenciar quais ficam ativas no perfil.'
            ),
            'fields': ('max_destaques',)
        }),
    )

    def has_add_permission(self, request):
        return not AchievementConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display  = ('code', 'nome', 'raridade_badge', 'trigger_type',
                     'trigger_value', 'bonus_display', 'ativo')
    list_filter   = ('raridade', 'trigger_type', 'ativo')
    list_editable = ('ativo',)
    search_fields = ('code', 'nome', 'descricao')
    ordering      = ('trigger_type', 'trigger_value')

    def raridade_badge(self, obj):
        cores = {
            'comum':    '#adb5bd',
            'rara':     '#0dcaf0',
            'epica':    '#d63384',
            'lendaria': '#ffc107',
        }
        cor = cores.get(obj.raridade, '#adb5bd')
        return format_html(
            '<span style="color:{}; font-weight:bold;">⬤ {}</span>',
            cor, obj.get_raridade_display()
        )
    raridade_badge.short_description = 'Raridade'

    def bonus_display(self, obj):
        if not obj.bonus_type or obj.bonus_value == 0:
            return format_html('<span style="color:#555;">— Prestígio</span>')
        return format_html(
            '<span style="color:#0dcaf0;">+{} {}</span>',
            obj.bonus_value, obj.get_bonus_type_display()
        )
    bonus_display.short_description = 'Bônus'


@admin.register(PlayerAchievement)
class PlayerAchievementAdmin(admin.ModelAdmin):
    list_display  = ('player', 'achievement', 'raridade_badge',
                     'em_destaque', 'desbloqueada_em')
    list_filter   = ('em_destaque', 'achievement__raridade', 'achievement__trigger_type')
    list_editable = ('em_destaque',)
    search_fields = ('player__username', 'achievement__nome')
    readonly_fields = ('player', 'achievement', 'desbloqueada_em')

    def raridade_badge(self, obj):
        cores = {
            'comum':    '#adb5bd',
            'rara':     '#0dcaf0',
            'epica':    '#d63384',
            'lendaria': '#ffc107',
        }
        cor = cores.get(obj.achievement.raridade, '#adb5bd')
        return format_html(
            '<span style="color:{};">⬤ {}</span>',
            cor, obj.achievement.get_raridade_display()
        )
    raridade_badge.short_description = 'Raridade'

    actions = ['colocar_em_destaque', 'remover_destaque']

    @admin.action(description='⭐ Colocar em destaque')
    def colocar_em_destaque(self, request, queryset):
        queryset.update(em_destaque=True)

    @admin.action(description='✖ Remover destaque')
    def remover_destaque(self, request, queryset):
        queryset.update(em_destaque=False)