import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse

from .models import Quiz, QuizAttempt, QuizQuestion, QuizOption, PatrolAttempt, PasswordGameConfig, PasswordAttempt
from .password_rules import generate_rules_sequence, get_rules_details, validate_password


################
###VIEW QUIZ###
################


@login_required
def start_quiz(request, quiz_id):
    """Cria a tentativa e redireciona para o quiz."""
    quiz = get_object_or_404(Quiz, pk=quiz_id, ativo=True)

    if not quiz.is_available_today():
        messages.error(request, 'Este quiz não está disponível.')
        return redirect('challenges:index')

    # Verifica tentativa ativa (não completada)
    active_attempt = QuizAttempt.objects.filter(
        player=request.user, quiz=quiz, completed_at__isnull=True
    ).first()

    if active_attempt:
        # Retoma tentativa em andamento
        return redirect('minigames:take_quiz', quiz_id=quiz_id)

    # Verifica se já completou (sem token de retake)
    completed = QuizAttempt.objects.filter(
        player=request.user, quiz=quiz, completed_at__isnull=False
    ).first()

    if completed:
        # TODO: verificar token de retake no inventário do player
        # Por ora, bloqueia
        messages.info(request, 'Você já completou este quiz.')
        return redirect('challenges:index')

    # Cria nova tentativa
    QuizAttempt.objects.create(player=request.user, quiz=quiz)
    return redirect('minigames:take_quiz', quiz_id=quiz_id)


@login_required
def take_quiz(request, quiz_id):
    quiz    = get_object_or_404(Quiz, pk=quiz_id, ativo=True)
    attempt = QuizAttempt.objects.filter(
        player=request.user, quiz=quiz, completed_at__isnull=True
    ).first()

    if not attempt:
        # Sem tentativa ativa — volta para central
        messages.warning(request, 'Inicie o quiz pela Central de Desafios.')
        return redirect('challenges:index')

    # Se o tempo acabou no servidor, encerra automaticamente
    remaining = attempt.remaining_seconds()
    if quiz.time_limit_seconds and remaining == 0:
        attempt.timer_expired = True
        attempt.xp_earned     = 0
        attempt.completed_at  = timezone.now()
        attempt.save()
        return redirect('minigames:quiz_result', quiz_id=quiz_id)

    questions = quiz.questions.prefetch_related('options').all()

    return render(request, 'minigames/quiz.html', {
        'quiz':           quiz,
        'attempt':        attempt,
        'questions':      questions,
        'remaining_time': remaining,
    })


@login_required
@require_POST
def submit_quiz(request, quiz_id):
    quiz    = get_object_or_404(Quiz, pk=quiz_id)
    attempt = get_object_or_404(
        QuizAttempt, player=request.user, quiz=quiz, completed_at__isnull=True
    )

    timer_expired = request.POST.get('timer_expired') == 'true'
    abandoned     = request.POST.get('abandoned') == 'true'

    # Timer expirou no servidor (fonte de verdade)
    if quiz.time_limit_seconds and attempt.remaining_seconds() == 0:
        timer_expired = True

    total_correct = 0
    xp_earned     = 0

    if timer_expired:
        # Tempo esgotado = zero
        xp_earned = 0
    else:
        # Calcula pontuação
        for question in quiz.questions.prefetch_related('options').all():
            correct_ids  = set(question.options.filter(is_correct=True).values_list('id', flat=True))
            selected_ids = set(
                int(v) for v in request.POST.getlist(f'question_{question.id}')
                if v.isdigit()
            )
            if selected_ids == correct_ids:
                total_correct += 1
                xp_earned     += question.xp_points

    attempt.completed_at  = timezone.now()
    attempt.xp_earned     = xp_earned
    attempt.total_correct = total_correct
    attempt.abandoned     = abandoned
    attempt.timer_expired = timer_expired
    attempt.save()

    # Concede XP e coins ao player
    player = getattr(request.user, 'player', None)
    if player and not abandoned and not timer_expired:
        player.xp_total += xp_earned
        player.coins    += quiz.coin_reward if xp_earned > 0 else 0
        player.save()

    return redirect('minigames:quiz_result', quiz_id=quiz_id)


@login_required
def quiz_result(request, quiz_id):
    quiz    = get_object_or_404(Quiz, pk=quiz_id)
    attempt = QuizAttempt.objects.filter(
        player=request.user, quiz=quiz, completed_at__isnull=False
    ).order_by('-completed_at').first()

    if not attempt:
        return redirect('challenges:index')

    total_questions  = quiz.questions.count()
    max_xp           = quiz.total_xp_possivel()
    is_perfect       = attempt.xp_earned >= max_xp and max_xp > 0

    return render(request, 'minigames/quiz_result.html', {
        'quiz':            quiz,
        'attempt':         attempt,
        'total_questions': total_questions,
        'max_xp':          max_xp,
        'is_perfect':      is_perfect,
    })


################
###VIEW PATROL###
################

MAX_PATROL_ATTEMPTS = 10
PATROL_XP_BASE      = 100
PATROL_COIN_MIN     = 1
PATROL_COIN_MAX     = 3


def _calc_feedback(secret, guess):
    """Retorna lista de 4 status para cada dígito do palpite."""
    feedback   = ['absent'] * 4
    secret_lst = list(secret)
    guess_lst  = list(guess)

    # Primeiro passo: posições corretas
    for i in range(4):
        if guess_lst[i] == secret_lst[i]:
            digit = guess_lst[i]
            feedback[i]   = 'correct_multi' if secret.count(digit) > 1 else 'correct'
            secret_lst[i] = None
            guess_lst[i]  = None

    # Segundo passo: presentes em posição errada
    for i in range(4):
        if guess_lst[i] is not None and guess_lst[i] in secret_lst:
            digit       = guess_lst[i]
            feedback[i] = 'multi' if secret.count(digit) > 1 else 'present'
            secret_lst[secret_lst.index(digit)] = None

    return feedback


@login_required
def patrol_start(request):
    """Inicia ou retoma a patrulha do dia."""
    today   = timezone.localdate()
    attempt = PatrolAttempt.objects.filter(player=request.user, date=today).first()

    if attempt and attempt.completed:
        return JsonResponse({'status': 'error', 'message': 'Patrulha já realizada hoje.'}, status=400)

    if attempt:
        # Retoma sessão em andamento
        return JsonResponse({
            'status':   'resume',
            'history':  attempt.guesses,
            'attempts': attempt.attempts_count,
        })

    # Novo jogo
    secret  = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    attempt = PatrolAttempt.objects.create(player=request.user, date=today, secret=secret)

    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def patrol_guess(request):
    """Recebe um palpite e retorna o feedback."""
    import json
    body  = json.loads(request.body)
    guess = body.get('guess', '').strip()

    if len(guess) != 4 or not guess.isdigit():
        return JsonResponse({'status': 'error', 'message': 'Digite 4 números.'}, status=400)

    today   = timezone.localdate()
    attempt = PatrolAttempt.objects.filter(player=request.user, date=today, completed=False).first()

    if not attempt:
        return JsonResponse({'status': 'error', 'message': 'Sessão inválida. Reinicie.'}, status=400)

    feedback = _calc_feedback(attempt.secret, guess)
    attempt.attempts_count += 1
    attempt.guesses.append({'guess': guess, 'feedback': feedback})

    is_win       = all(f in ('correct', 'correct_multi') for f in feedback)
    is_game_over = attempt.attempts_count >= MAX_PATROL_ATTEMPTS and not is_win

    response = {
        'status':   'playing',
        'feedback': feedback,
        'attempts': attempt.attempts_count,
        'guess':    guess,
    }

    if is_win:
        xp    = max(10, int(PATROL_XP_BASE / attempt.attempts_count))
        coins = random.randint(PATROL_COIN_MIN, PATROL_COIN_MAX)

        attempt.won         = True
        attempt.completed   = True
        attempt.xp_earned   = xp
        attempt.coins_earned = coins
        attempt.completed_at = timezone.now()

        # Credita ao perfil do player
        player = getattr(request.user, 'player', None)
        if player:
            player.xp_total += xp
            player.coins    += coins
            player.save()

        response.update({
            'status':      'win',
            'xp_earned':   xp,
            'coins_earned': coins,
            'message':     f'Código quebrado em {attempt.attempts_count} tentativa(s)! +{xp} XP, +{coins} Coins',
        })

    elif is_game_over:
        attempt.completed    = True
        attempt.completed_at = timezone.now()

        response.update({
            'status':  'lose',
            'secret':  attempt.secret,
            'message': 'Tentativas esgotadas. Tente novamente amanhã.',
        })

    attempt.guesses = attempt.guesses 
    attempt.save()
    return JsonResponse(response)


################
###VIEW PASSWORD###
################


@login_required
def password_game_play(request):
    config = PasswordGameConfig.get()

    if not config.ativo or not config.is_active_today():
        messages.warning(request, 'Cofre de Senhas não disponível hoje.')
        return redirect('challenges:index')

    today = timezone.localdate()

    # Bloqueia se já completou hoje
    completed = PasswordAttempt.objects.filter(
        player=request.user,
        started_at__date=today,
        completed_at__isnull=False
    ).first()
    if completed:
        return redirect('minigames:password_result', attempt_id=completed.pk)

    # Retoma tentativa aberta ou cria nova
    attempt = PasswordAttempt.objects.filter(
        player=request.user,
        completed_at__isnull=True
    ).order_by('-started_at').first()

    if not attempt:
        rules_ids = generate_rules_sequence(config)
        attempt   = PasswordAttempt.objects.create(
            player=request.user,
            rules_sequence=rules_ids,
        )

    rules_data     = get_rules_details(attempt.rules_sequence)
    remaining_time = attempt.remaining_seconds()

    return render(request, 'minigames/password_game.html', {
        'attempt':        attempt,
        'rules':          rules_data,
        'remaining_time': remaining_time,
        'has_timer':      bool(config.time_limit_seconds),
        'config':         config,
    })


@login_required
@require_POST
def password_game_submit(request, attempt_id):
    attempt = get_object_or_404(PasswordAttempt, pk=attempt_id, player=request.user)

    if attempt.completed_at:
        return JsonResponse({'status': 'error', 'message': 'Jogo já finalizado.'}, status=400)

    # Timeout no servidor
    if attempt.remaining_seconds() == 0 and PasswordGameConfig.get().time_limit_seconds:
        attempt.completed_at = timezone.now()
        attempt.is_won       = False
        attempt.save()
        return JsonResponse({'status': 'timeout', 'redirect': f'/minigames/cofre/{attempt.pk}/resultado/'})

    import json as _json
    body     = _json.loads(request.body)
    password = body.get('password', '')

    is_valid, failed = validate_password(password, attempt.rules_sequence)

    if is_valid:
        config = PasswordGameConfig.get()
        attempt.is_won        = True
        attempt.completed_at  = timezone.now()
        attempt.input_password = password
        attempt.xp_earned     = config.xp_reward
        attempt.coins_earned  = config.coin_reward
        attempt.save()

        player = getattr(request.user, 'player', None)
        if player:
            player.xp_total += config.xp_reward
            player.coins    += config.coin_reward
            player.save()

        return JsonResponse({'status': 'win', 'redirect': f'/minigames/cofre/{attempt.pk}/resultado/'})

    return JsonResponse({'status': 'invalid', 'failed_rules': failed})


@login_required
@require_POST
def password_game_abandon(request, attempt_id):
    attempt = get_object_or_404(PasswordAttempt, pk=attempt_id, player=request.user)
    if not attempt.completed_at:
        attempt.completed_at = timezone.now()
        attempt.is_won       = False
        attempt.save()
    return JsonResponse({'status': 'abandoned', 'redirect': f'/minigames/cofre/{attempt.pk}/resultado/'})


@login_required
def password_result(request, attempt_id):
    attempt = get_object_or_404(PasswordAttempt, pk=attempt_id, player=request.user)
    duration = None
    if attempt.completed_at and attempt.started_at:
        duration = round((attempt.completed_at - attempt.started_at).total_seconds())

    return render(request, 'minigames/password_result.html', {
        'attempt':  attempt,
        'duration': duration,
        'config':   PasswordGameConfig.get(),
    })