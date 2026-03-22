"""
Sinais que disparam revogação de XP/coins automaticamente
quando uma tentativa é deletada pelo admin.
"""
from django.db.models.signals import pre_delete
from django.dispatch import receiver


@receiver(pre_delete, sender='minigames.QuizAttempt')
def reverter_quiz(sender, instance, **kwargs):
    if instance.completed_at and instance.xp_earned > 0:
        from apps.profiles.services import revoke_xp, revoke_coins
        revoke_xp(
            instance.player,
            instance.xp_earned,
            f'Estorno Quiz: {instance.quiz.titulo}'
        )
        if instance.quiz.coin_reward > 0:
            revoke_coins(instance.player, instance.quiz.coin_reward)


@receiver(pre_delete, sender='minigames.DecriptarAttempt')
def reverter_decriptar(sender, instance, **kwargs):
    if instance.completed_at and instance.xp_earned > 0:
        from apps.profiles.services import revoke_xp, revoke_coins
        revoke_xp(
            instance.player,
            instance.xp_earned,
            f'Estorno Decriptar {instance.date}'
        )
        if instance.coins_earned > 0:
            revoke_coins(instance.player, instance.coins_earned)


@receiver(pre_delete, sender='minigames.CodigoAttempt')
def reverter_codigo(sender, instance, **kwargs):
    if instance.completed_at and instance.xp_earned > 0:
        from apps.profiles.services import revoke_xp, revoke_coins
        revoke_xp(
            instance.player,
            instance.xp_earned,
            f'Estorno Código {instance.date}'
        )
        if instance.coins_earned > 0:
            revoke_coins(instance.player, instance.coins_earned)


@receiver(pre_delete, sender='minigames.PasswordAttempt')
def reverter_password(sender, instance, **kwargs):
    if instance.completed_at and instance.xp_earned > 0:
        from apps.profiles.services import revoke_xp, revoke_coins
        revoke_xp(
            instance.player,
            instance.xp_earned,
            f'Estorno Cofre de Senhas'
        )
        if instance.coins_earned > 0:
            revoke_coins(instance.player, instance.coins_earned)


@receiver(pre_delete, sender='minigames.PatrolAttempt')
def reverter_patrol(sender, instance, **kwargs):
    if instance.completed and instance.xp_earned > 0:
        from apps.profiles.services import revoke_xp, revoke_coins
        revoke_xp(
            instance.player,
            instance.xp_earned,
            f'Estorno Patrulha {instance.date}'
        )
        if instance.coins_earned > 0:
            revoke_coins(instance.player, instance.coins_earned)