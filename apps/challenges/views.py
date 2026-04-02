from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.minigames.models import (Quiz, QuizAttempt, PasswordGameConfig, PasswordAttempt, DecriptarAttempt, DecriptarConfig,
                                   CodigoConfig, CodigoAttempt)


@login_required
def index(request):
    today = timezone.localdate()

    # ── Quizzes ──
    all_quizzes       = Quiz.objects.filter(ativo=True, available_from__lte=today)
    available_quizzes = [q for q in all_quizzes if q.is_available_today()]

    quiz_status = {}
    for quiz in available_quizzes:
        attempt = QuizAttempt.objects.filter(
            player=request.user, quiz=quiz
        ).order_by('-started_at').first()

        if not attempt:
            quiz_status[quiz.id] = 'disponivel'
        elif attempt.completed_at is None:
            quiz_status[quiz.id] = 'em_andamento'
        else:
            quiz_status[quiz.id] = 'concluido'

    # ── Decriptar ─────────────────────────────────────────
    decriptar_config  = DecriptarConfig.objects.filter(ativo=True).first()
    decriptar_today   = decriptar_config and decriptar_config.is_active_today()
    decriptar_attempt = None
    decriptar_status  = None

    if decriptar_today:
        decriptar_attempt = DecriptarAttempt.objects.filter(
            player=request.user, date=today
        ).first()
        if not decriptar_attempt:
            decriptar_status = 'disponivel'
        elif not decriptar_attempt.is_completed:
            decriptar_status = 'em_andamento'
        else:
            decriptar_status = 'concluido'

    # ── Código ───────────────────────────────────────────
    codigo_config  = CodigoConfig.objects.filter(ativo=True).first()
    codigo_today   = bool(codigo_config and codigo_config.is_active_today())
    codigo_attempt = None
    codigo_status  = None

    if codigo_today:
        codigo_attempt = CodigoAttempt.objects.filter(
            player=request.user, config=codigo_config, date=today
        ).first()
        if not codigo_attempt:
            codigo_status = 'disponivel'
        elif not codigo_attempt.is_completed:
            codigo_status = 'em_andamento'
        else:
            codigo_status = 'concluido'

    # ── Cofre de Senhas ──
    pw_config     = PasswordGameConfig.get()
    pw_disponivel = pw_config.ativo and pw_config.is_active_today()
    pw_status     = None
    pw_attempt    = None

    if pw_disponivel:
        pw_attempt = PasswordAttempt.objects.filter(
            player=request.user,
        ).order_by('-started_at').first()

        # Verifica se a tentativa é de hoje
        if pw_attempt and timezone.localdate(pw_attempt.started_at) != today:
            pw_attempt = None

        if not pw_attempt:
            pw_status = 'disponivel'
        elif pw_attempt.completed_at is None:
            pw_status = 'em_andamento'
        elif pw_attempt.is_won:
            pw_status = 'concluido'
        else:
            pw_status = 'falhou'

    return render(request, 'challenges/index.html', {
        'today':          today,
        'quizzes':        available_quizzes,
        'quiz_status':    quiz_status,
        'pw_config':      pw_config,
        'pw_disponivel':  pw_disponivel,
        'pw_status':      pw_status,
        'pw_attempt':     pw_attempt if pw_disponivel and pw_status not in (None, 'disponivel') else None,
        'decriptar_config':  decriptar_config,
        'decriptar_today':   decriptar_today,
        'decriptar_attempt': decriptar_attempt,
        'decriptar_status':  decriptar_status,
        'codigo_config':  codigo_config,
        'codigo_today':   codigo_today,
        'codigo_attempt': codigo_attempt,
        'codigo_status':  codigo_status,
    })