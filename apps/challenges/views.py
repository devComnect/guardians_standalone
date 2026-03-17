from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.minigames.models import Quiz, QuizAttempt, PasswordGameConfig, PasswordAttempt


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

    # ── Cofre de Senhas ──
    pw_config     = PasswordGameConfig.get()
    pw_disponivel = pw_config.ativo and pw_config.is_active_today()
    pw_status     = None
    pw_attempt    = None

    if pw_disponivel:
        pw_attempt = PasswordAttempt.objects.filter(
            player=request.user,
        ).order_by('-started_at').first()

        print(f"DEBUG pw_attempt raw: {pw_attempt}")
        print(f"DEBUG started_at: {pw_attempt.started_at if pw_attempt else 'None'}")
        print(f"DEBUG today: {today}")

        # Verifica se a tentativa é de hoje
        if pw_attempt and pw_attempt.started_at.date() != today:
            pw_attempt = None  # tentativa de outro dia, ignora

        if not pw_attempt:
            pw_status = 'disponivel'
        elif pw_attempt.completed_at is None:
            pw_status = 'em_andamento'
        elif pw_attempt.is_won:
            pw_status = 'concluido'
        else:
            pw_status = 'falhou'

        print(f"DEBUG pw_status final: {pw_status}")

    return render(request, 'challenges/index.html', {
        'today':          today,
        'quizzes':        available_quizzes,
        'quiz_status':    quiz_status,
        'pw_config':      pw_config,
        'pw_disponivel':  pw_disponivel,
        'pw_status':      pw_status,
        'pw_attempt':     pw_attempt if pw_disponivel and pw_status not in (None, 'disponivel') else None,
    })