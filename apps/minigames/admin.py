import nested_admin
from django.contrib import admin
from django.utils import timezone
from .models import Quiz, QuizQuestion, QuizOption, QuizAttempt, MiniGameContent, PatrolAttempt, PasswordGameConfig, PasswordAttempt

################
###ADMIN QUIZ###
################

class QuizOptionInline(nested_admin.NestedTabularInline):
    model   = QuizOption
    extra   = 4
    fields  = ('option_text', 'is_correct')


class QuizQuestionInline(nested_admin.NestedStackedInline):
    model   = QuizQuestion
    extra   = 1
    inlines = [QuizOptionInline]
    fields  = ('question_text', 'xp_points', 'allow_multiple')


@admin.register(Quiz)
class QuizAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('titulo', 'available_from', 'available_until', 'available_days', 'ativo')
    list_filter     = ('ativo',)
    list_editable   = ('ativo',)
    search_fields   = ('titulo',)
    inlines         = [QuizQuestionInline]
    exclude         = ('criado_por', 'season', 'criado_em')

    def get_changeform_initial_data(self, request):
        return {'available_from': timezone.localdate()}

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display    = ('player', 'quiz', 'xp_earned', 'total_correct', 'abandoned', 'timer_expired', 'started_at', 'completed_at')
    list_filter     = ('quiz',)
    readonly_fields = ('player', 'quiz', 'started_at', 'completed_at', 'xp_earned', 'total_correct')
    actions         = ['resetar_tentativa']

    @admin.action(description='🗑️ Resetar tentativa — libera o quiz para o player refazer')
    def resetar_tentativa(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} tentativa(s) removida(s) com sucesso.')


@admin.register(MiniGameContent)
class MiniGameContentAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'titulo', 'dificuldade', 'ativo')
    list_filter  = ('tipo', 'dificuldade', 'ativo')


##################
## ADMIN PATROL ##
##################

@admin.register(PatrolAttempt)
class PatrolAttemptAdmin(admin.ModelAdmin):
    list_display  = ('player', 'date', 'won', 'attempts_count', 'xp_earned', 'coins_earned', 'completed')
    list_filter   = ('won', 'completed', 'date')
    readonly_fields = ('player', 'date', 'secret', 'guesses', 'attempts_count', 'xp_earned', 'coins_earned', 'started_at', 'completed_at')
    actions       = ['resetar_patrulha']

    @admin.action(description='🗑️ Resetar patrulha — libera para refazer hoje')
    def resetar_patrulha(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} patrulha(s) resetada(s).')


##################
## ADMIN PASSWORD ##
##################

@admin.register(PasswordGameConfig)
class PasswordGameConfigAdmin(admin.ModelAdmin):
    list_display = ('time_limit_seconds', 'xp_reward', 'coin_reward',
                    'rules_count_easy', 'rules_count_medium', 'rules_count_hard',
                    'active_days', 'ativo')
    fieldsets = (
        ('Recompensas', {'fields': ('xp_reward', 'coin_reward', 'ativo')}),
        ('Timer', {'fields': ('time_limit_seconds',)}),
        ('Qtd. de Regras por Dificuldade', {'fields': (
            'rules_count_easy', 'rules_count_medium', 'rules_count_hard'
        )}),
        ('Disponibilidade', {'fields': ('active_days',),
            'description': '0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sab, 6=Dom'}),
    )

    def has_add_permission(self, request):
        return not PasswordGameConfig.objects.exists()


@admin.register(PasswordAttempt)
class PasswordAttemptAdmin(admin.ModelAdmin):
    list_display  = ('player', 'is_won', 'xp_earned', 'coins_earned', 'started_at', 'completed_at')
    list_filter   = ('is_won',)
    readonly_fields = ('player', 'rules_sequence', 'started_at', 'completed_at',
                       'xp_earned', 'coins_earned', 'input_password')
    actions = ['resetar_tentativa']

    @admin.action(description='🗑️ Resetar tentativa')
    def resetar_tentativa(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} tentativa(s) removida(s).')