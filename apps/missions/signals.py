# apps/missions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .services import MissionService
from apps.minigames.models import QuizAttempt, PasswordAttempt, DecriptarAttempt, CodigoAttempt
from apps.feedback.models import Feedback

@receiver(post_save, sender=Feedback)
def track_feedback_missions(sender, instance, created, **kwargs):
    """Escuta quando o player envia um novo feedback para progredir a missão."""
    if not created: 
        return
    user = instance.player 
    
    if user:
        MissionService.update_progress(user, 'FEEDBACK_COUNT')

@receiver(post_save, sender='profiles.XPEvent')
def track_missions_via_xp(sender, instance, created, **kwargs):
    if not created: return

    user = instance.player
    fonte = instance.fonte
    
    mapping = {
        'quiz': ('QUIZ_COUNT', QuizAttempt),
        'password': ('MIN_GAME_COUNT', PasswordAttempt),
        'decriptar': ('MIN_GAME_COUNT', DecriptarAttempt),
        'codigo': ('MIN_GAME_COUNT', CodigoAttempt),
        'patrol': ('PATROL_COUNT', None), # Patrulha não tem bônus complexo
    }

    if fonte in mapping:
        mission_code, model_class = mapping[fonte]
        
        is_perfect = False
        is_speedrun = False

        # Se temos um modelo de tentativa, vamos calcular os bônus
        if model_class:
            # Busca a tentativa mais recente deste usuário para esta fonte
            # (que foi concluída agora mesmo)
            attempt = model_class.objects.filter(player=user).order_by('-completed_at').first()
            
            if attempt and attempt.completed_at:
                is_perfect, is_speedrun = calculate_bonuses(attempt, fonte, instance)

        # Atualiza a missão principal e propaga os bônus
        MissionService.update_progress(
            user, 
            mission_code, 
            is_perfect=is_perfect, 
            is_speedrun=is_speedrun
        )
        
        if fonte == 'quiz':
            MissionService.update_progress(user, 'QUIZ_SCORE_SUM', amount=instance.xp_base)

def calculate_bonuses(attempt, fonte, xp_event):
    """Calcula se a tentativa foi perfeita ou speedrun."""
    perfect = False
    speedrun = False

    # 1. Lógica de Perfeição (XP Base == XP Máximo do desafio)
    if fonte == 'quiz':
        # No Quiz, comparamos com a soma de pontos das questões
        max_xp = attempt.quiz.total_xp_possivel()
        if xp_event.xp_base >= max_xp and max_xp > 0:
            perfect = True
    else:
        # Nos minigames, comparamos se o player venceu (is_won/won)
        # e se o XP ganho é o XP configurado no Config/Modelo
        perfect = getattr(attempt, 'is_won', False) or getattr(attempt, 'won', False)

    # 2. Lógica de Speedrun (Tempo Gasto <= 50% do Tempo Limite)
    # Pegamos o tempo limite dependendo do jogo
    time_limit = 0
    if fonte == 'quiz':
        time_limit = attempt.quiz.time_limit_seconds
    elif hasattr(attempt, 'config'):
        time_limit = attempt.config.time_limit_seconds
    elif fonte == 'password':
        from apps.minigames.models import PasswordGameConfig
        time_limit = PasswordGameConfig.get().time_limit_seconds

    if time_limit > 0 and attempt.started_at:
        tempo_gasto = (attempt.completed_at - attempt.started_at).total_seconds()
        if tempo_gasto <= (time_limit / 2):
            speedrun = True

    return perfect, speedrun