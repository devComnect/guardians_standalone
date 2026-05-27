from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.minigames.models import CodigoAttempt, DecriptarAttempt, WordBank
from apps.challenges.models import Season
from .models import PlayerWordUnlock


def _season_ativa():
    from apps.rankings.models import Season
    return Season.objects.filter(ativa=True).first()


def _unlock_palavra(player, palavra_str, season):
    try:
        word = WordBank.objects.get(palavra=palavra_str.upper().strip())
    except WordBank.DoesNotExist:
        return
    _, created = PlayerWordUnlock.objects.get_or_create(player=player, word=word, season=season)
    if created:
        _verificar_notificacoes_lexico(player, word, season)


def _verificar_notificacoes_lexico(player, word, season):
    from apps.profiles.log_service import registrar_log

    total_desbloqueado = PlayerWordUnlock.objects.filter(player=player, season=season).count()
    total_palavras     = WordBank.objects.filter(ativo=True).count()

    registrar_log(
        user=player,
        tipo='system',
        titulo=f'Léxico desbloqueado: {word.palavra}',
        descricao=word.dica or '',
        breakdown={
            'palavra':    word.palavra,
            'categoria':  word.categoria,
            'lexico_count': total_desbloqueado,
            'lexico_total': total_palavras,
        },
    )

    if total_palavras > 0 and total_desbloqueado == total_palavras:
        registrar_log(
            user=player,
            tipo='system',
            titulo='Léxico Completo!',
            descricao='Você desbloqueou todos os termos da temporada.',
            breakdown={'lexico_count': total_desbloqueado, 'lexico_total': total_palavras},
        )


@receiver(post_save, sender=CodigoAttempt)
def unlock_palavra_codigo(sender, instance, **kwargs):
    if not instance.completed_at or instance.abandoned or not instance.won:
        return
    season = _season_ativa()
    if not season:
        return
    _unlock_palavra(instance.player, instance.secret_word, season)


@receiver(post_save, sender=DecriptarAttempt)
def unlock_palavras_decriptar(sender, instance, **kwargs):
    if not instance.completed_at:
        return
    season = _season_ativa()
    if not season:
        return
    for entry in instance.words_sequence:
        if entry.get('solved'):
            _unlock_palavra(instance.player, entry['palavra'], season)