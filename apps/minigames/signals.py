from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.timezone import timedelta
from apps.profiles.models import PlayerBattlePass, SystemLog

def processar_estorno(instance, log_msg):
    xp_total = 0
    coins_total = 0
    ref_date = getattr(instance, 'completed_at', None)

    # Busca no log do sistema os ganhos exatos gerados no momento da conclusão
    if ref_date:
        logs = SystemLog.objects.filter(
            player=instance.player,
            criado_em__range=(ref_date - timedelta(seconds=3), ref_date + timedelta(seconds=3))
        )
        for log in logs:
            if getattr(log, 'xp_delta', 0) > 0:
                xp_total += log.xp_delta
            if getattr(log, 'coin_delta', 0) > 0:
                coins_total += log.coin_delta

    # Fallback de segurança para valor base
    if xp_total == 0:
        xp_total = getattr(instance, 'xp_earned', 0) or 0
        
    if coins_total == 0:
        if hasattr(instance, 'quiz'):
            coins_total = getattr(instance.quiz, 'coin_reward', 0) or 0
        else:
            coins_total = getattr(instance, 'coins_earned', 0) or 0

    if xp_total > 0 or coins_total > 0:
        from apps.profiles.services import revoke_xp, revoke_coins
        
        if xp_total > 0:
            revoke_xp(instance.player, xp_total, log_msg)
            pbp = PlayerBattlePass.objects.filter(player=instance.player).order_by('-id').first()
            if pbp:
                pbp.xp_bp = max(0, pbp.xp_bp - xp_total)
                pbp.save(update_fields=['xp_bp'])
        
        if coins_total > 0:
            revoke_coins(instance.player, coins_total)

@receiver(pre_delete, sender='minigames.QuizAttempt')
def reverter_quiz(sender, instance, **kwargs):
    if getattr(instance, 'completed_at', None):
        processar_estorno(instance, f'Estorno Quiz: {instance.quiz.titulo}')

@receiver(pre_delete, sender='minigames.DecriptarAttempt')
def reverter_decriptar(sender, instance, **kwargs):
    if getattr(instance, 'completed_at', None):
        processar_estorno(instance, f'Estorno Decriptar {instance.date}')

@receiver(pre_delete, sender='minigames.CodigoAttempt')
def reverter_codigo(sender, instance, **kwargs):
    if getattr(instance, 'completed_at', None):
        processar_estorno(instance, f'Estorno Código {instance.date}')

@receiver(pre_delete, sender='minigames.PasswordAttempt')
def reverter_password(sender, instance, **kwargs):
    if getattr(instance, 'completed_at', None):
        processar_estorno(instance, 'Estorno Cofre de Senhas')

@receiver(pre_delete, sender='minigames.PatrolAttempt')
def reverter_patrol(sender, instance, **kwargs):
    # Patrulha pode usar 'completed_at', garantindo pelo getattr
    if getattr(instance, 'completed_at', None) or getattr(instance, 'completed', False):
        processar_estorno(instance, f'Estorno Patrulha {instance.date}')