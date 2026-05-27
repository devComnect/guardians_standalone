from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from apps.rankings.models import Season
from apps.minigames.models import Quiz, QuizAttempt, WordBank
from .models import PlayerWordUnlock


def _season_ativa():
    return Season.objects.filter(ativa=True).first()

NOVO_THRESHOLD_DIAS = 3


@login_required
def training_home(request):
    season = _season_ativa()
    today  = timezone.localdate()
    limite = timezone.now() - timedelta(days=NOVO_THRESHOLD_DIAS)

    novos_quizzes_count = 0
    novos_termos_count  = 0

    if season:
        novos_quizzes_count = Quiz.objects.filter(
            ativo=True,
            available_from__gte=season.inicio,
            available_from__lte=today,
        ).filter(
            available_from__gte=today - timedelta(days=NOVO_THRESHOLD_DIAS),
        ).count()

        novos_termos_count = PlayerWordUnlock.objects.filter(
            player=request.user,
            season=season,
            unlocked_at__gte=limite,
        ).count()

    return render(request, 'training/home.html', {
        'season':              season,
        'novos_quizzes_count': novos_quizzes_count,
        'novos_termos_count':  novos_termos_count,
    })


@login_required
def galeria_quizzes(request):
    season = _season_ativa()
    today  = timezone.localdate()

    quizzes = Quiz.objects.filter(
        ativo=True,
        available_from__gte=season.inicio
    ).prefetch_related('questions__options') if season else []

    cards = []

    for quiz in quizzes:
        attempt = QuizAttempt.objects.filter(
            player=request.user, quiz=quiz, completed_at__isnull=False
        ).first()

        disponivel_hoje = quiz.is_available_today()
        expirado        = today > quiz.available_until

        if not attempt and not expirado and not disponivel_hoje:
            status = 'futuro'
        elif not attempt and disponivel_hoje:
            status = 'disponivel'
        elif not attempt and expirado:
            status = 'perdido'
        else:
            status = 'completo'

        is_new = (today - quiz.available_from).days <= NOVO_THRESHOLD_DIAS

        questoes = []
        if status == 'completo':
            respostas_player = set(attempt.drafts.values_list('question_id', 'option_id'))
            for q in quiz.questions.all():
                opcoes = []
                for opt in q.options.all():
                    opcoes.append({
                        'texto':     opt.option_text,
                        'correta':   opt.is_correct,
                        'escolhida': (q.id, opt.id) in respostas_player,
                    })
                questoes.append({'texto': q.question_text, 'opcoes': opcoes})

        cards.append({
            'quiz':     quiz,
            'status':   status,
            'questoes': questoes,
            'attempt':  attempt,
            'is_new':   is_new,
        })

    return render(request, 'training/galeria_quizzes.html', {
        'cards':  cards,
        'season': season,
    })


@login_required
def galeria_termos(request):
    season  = _season_ativa()
    limite  = timezone.now() - timedelta(days=NOVO_THRESHOLD_DIAS)

    todas_palavras = WordBank.objects.filter(ativo=True).order_by('categoria', 'palavra')

    desbloqueios = {}
    if season:
        for unlock in PlayerWordUnlock.objects.filter(player=request.user, season=season):
            desbloqueios[unlock.word_id] = unlock.unlocked_at

    cards = []
    for word in todas_palavras:
        unlocked_at   = desbloqueios.get(word.id)
        desbloqueada  = unlocked_at is not None
        is_new        = desbloqueada and unlocked_at >= limite
        cards.append({
            'word':        word,
            'desbloqueada': desbloqueada,
            'is_new':      is_new,
        })

    total         = len(cards)
    desbloqueadas = len(desbloqueios)

    return render(request, 'training/galeria_termos.html', {
        'cards':         cards,
        'total':         total,
        'desbloqueadas': desbloqueadas,
        'season':        season,
    })