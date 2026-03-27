from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='profiles.XPEvent')
def verificar_conquistas_apos_xp(sender, instance, created, **kwargs):
    """
    Dispara verificações de conquistas automaticamente
    toda vez que um XPEvent é criado.
    Mapeia a fonte do XP para os triggers relevantes.
    """
    if not created:
        return
    
    from apps.profiles.services import verificar_conquistas

    user  = instance.player
    fonte = instance.fonte

    # Triggers universais — verificados após qualquer XP
    universais = ['xp_total', 'level_reached', 'ofensiva', 'streak_days']

    # Triggers específicos por fonte
    mapa = {
        'quiz':      ['quiz_count', 'quiz_perfect', 'all_daily_count'],
        'decriptar': ['decriptar_count', 'minigame_count', 'all_daily_count'],
        'codigo':    ['codigo_count',    'minigame_count', 'all_daily_count'],
        'password':  ['minigame_count',  'all_daily_count'],
        'patrol':    ['patrol_count',    'all_daily_count'],
        'bonus':     [],   # XP de bônus/admin não dispara triggers de contagem
        'conquista': [],
        'missao':    [],
    }

    triggers = universais + mapa.get(fonte, [])

    for trigger in triggers:
        verificar_conquistas(user, trigger)