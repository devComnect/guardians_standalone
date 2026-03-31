import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
import json
from apps.profiles.services import registrar_desafio_diario , grant_xp, grant_coins
from .models import (Quiz, QuizAttempt, QuizQuestion, QuizOption, PatrolAttempt, PasswordGameConfig, 
                        PasswordAttempt, DecriptarConfig, DecriptarAttempt, CodigoAttempt, CodigoConfig, WordBank)
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
    if not abandoned and not timer_expired and xp_earned > 0:
        total_questions = quiz.questions.count()

        grant_xp(request.user, xp_earned, 'quiz', f'Quiz: {quiz.titulo}', contexto={
        'segundos_restantes': attempt.remaining_seconds(),
        'tentativas': total_questions,
        'won': total_questions > 0 and (total_correct / total_questions) >= 0.7,
    } )
        grant_coins(request.user, quiz.coin_reward, 'quiz')
        registrar_desafio_diario(request.user)

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

    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    tempo_restante = max(0, 300 - int(elapsed))

    response = {
        'status':   'playing',
        'feedback': feedback,
        'attempts': attempt.attempts_count,
        'remaining_seconds': tempo_restante,
        'guess':    guess,
    }

    if is_win:
        xp    = max(10, int(PATROL_XP_BASE / attempt.attempts_count))
        coins = random.randint(PATROL_COIN_MIN, PATROL_COIN_MAX)

        attempt.won          = True
        attempt.completed    = True
        attempt.xp_earned    = xp
        attempt.coins_earned = coins
        attempt.completed_at = timezone.now()
        attempt.guesses      = attempt.guesses
        attempt.save()                                   

        grant_xp(request.user, xp, 'patrol',              
            f'Patrulha concluída em {attempt.attempts_count} tentativa(s)', 
            contexto={
                'segundos_restantes': tempo_restante,
                'tentativas': len(attempt.guesses),
                'won': attempt.won,
            })
        grant_coins(request.user, coins, 'patrol')
        registrar_desafio_diario(request.user)

        response.update({
            'status':       'win',
            'xp_earned':    xp,
            'coins_earned': coins,
            'message':      f'Código quebrado em {attempt.attempts_count} tentativa(s)! +{xp} XP, +{coins} Coins',
        })

    elif is_game_over:
        attempt.completed    = True
        attempt.completed_at = timezone.now()
        attempt.guesses      = attempt.guesses
        attempt.save()                                          # ← SALVA AQUI TAMBÉM

        response.update({
            'status':  'lose',
            'secret':  attempt.secret,
            'message': 'Tentativas esgotadas. Tente novamente amanhã.',
        })

    else:
        attempt.guesses = attempt.guesses
        attempt.save()                                          # ← SAVE DO PLAYING

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
        
        grant_xp(request.user, config.xp_reward, 'password', 'Cofre de Senhas concluído', 
                 contexto={
                    'segundos_restantes': attempt.remaining_seconds(),
                    'tentativas': 1,
                    'won': attempt.is_won,
                })
        grant_coins(request.user, config.coin_reward, 'password')
        registrar_desafio_diario(request.user)

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

# ─────────────────────────────────────────────
# DECRIPTAR
# ─────────────────────────────────────────────

def _shuffle_word(word):
    """Embaralha garantindo resultado diferente da palavra original."""
    chars = list(word)
    if len(set(chars)) == 1:
        return word
    shuffled = chars[:]
    for _ in range(50):
        random.shuffle(shuffled)
        if ''.join(shuffled) != word:
            return ''.join(shuffled)
    return ''.join(shuffled)


@login_required
def start_decriptar(request):
    config = DecriptarConfig.objects.filter(ativo=True).first()

    if not config or not config.is_active_today():
        messages.error(request, 'Decriptar não está disponível hoje.')
        return redirect('challenges:index')

    today   = timezone.localdate()
    attempt = DecriptarAttempt.objects.filter(player=request.user, date=today).first()

    if attempt and attempt.is_completed:
        return redirect('minigames:decriptar_result', attempt_id=attempt.id)

    if attempt and not attempt.is_completed:
        # Retoma tentativa em andamento
        if config.time_limit_seconds and attempt.remaining_seconds() == 0:
            attempt.timer_expired = True
            attempt.completed_at  = timezone.now()
            attempt.save()
            return redirect('minigames:decriptar_result', attempt_id=attempt.id)
        return redirect('minigames:play_decriptar')

    # Cria nova tentativa — seleciona e embaralha palavras server-side
    selected = config.select_words()
    words_sequence = [
        {
            'id':       w['id'],
            'palavra':  w['palavra'],          # Fica no servidor
            'dica':     w.get('dica', ''),
            'shuffled': _shuffle_word(w['palavra']),
            'solved':   False,
        }
        for w in selected
    ]

    DecriptarAttempt.objects.create(
        player         = request.user,
        config         = config,
        date           = today,
        words_sequence = words_sequence,
        lives_remaining= config.max_lives,
    )
    return redirect('minigames:play_decriptar')


@login_required
def play_decriptar(request):
    today   = timezone.localdate()
    attempt = DecriptarAttempt.objects.filter(
        player=request.user, date=today, completed_at__isnull=True
    ).first()

    if not attempt:
        messages.warning(request, 'Inicie o Decriptar pela Central de Desafios.')
        return redirect('challenges:index')

    config = attempt.config

    # Timer expirou no servidor
    if config.time_limit_seconds and attempt.remaining_seconds() == 0:
        attempt.timer_expired = True
        attempt.completed_at  = timezone.now()
        attempt.save()
        return redirect('minigames:decriptar_result', attempt_id=attempt.id)

    # Monta payload para o template — SEM as palavras corretas
    words_payload = [
        {
            'index':    i,
            'shuffled': w['shuffled'],
            'dica':     w['dica'],
            'length':   len(w['palavra']),
            'solved':   w['solved'],
        }
        for i, w in enumerate(attempt.words_sequence)
    ]

    return render(request, 'minigames/decriptar.html', {
        'attempt':        attempt,
        'config':         config,
        'words_payload':  json.dumps(words_payload),
        'remaining_time': attempt.remaining_seconds(),
        'total_words':    len(attempt.words_sequence),
        'lives_range': range(config.max_lives),
        'correct_count':  sum(1 for w in attempt.words_sequence if w['solved']),
    })


@login_required
@require_POST
def check_decriptar_word(request):
    """AJAX — valida uma palavra. Nunca expõe a resposta ao cliente."""
    try:
        body       = json.loads(request.body)
        attempt_id = body.get('attempt_id')
        word_index = int(body.get('word_index', -1))
        answer     = body.get('answer', '').upper().strip()
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Payload inválido.'}, status=400)

    attempt = DecriptarAttempt.objects.filter(
        pk=attempt_id, player=request.user, completed_at__isnull=True
    ).first()

    if not attempt:
        return JsonResponse({'error': 'Tentativa não encontrada ou já encerrada.'}, status=404)

    # Valida timer server-side
    if attempt.config.time_limit_seconds and attempt.remaining_seconds() == 0:
        attempt.timer_expired = True
        attempt.completed_at  = timezone.now()
        attempt.save()
        return JsonResponse({'error': 'timer_expired', 'redirect': f'/minigames/decriptar/resultado/{attempt.id}/'})

    words = attempt.words_sequence
    if word_index < 0 or word_index >= len(words):
        return JsonResponse({'error': 'Índice inválido.'}, status=400)

    word_data = words[word_index]

    if word_data['solved']:
        return JsonResponse({'already_solved': True, 'correct_count': attempt.correct_count})

    is_correct = (answer == word_data['palavra'])

    if is_correct:
        words[word_index]['solved'] = True
        attempt.words_sequence      = words
        attempt.correct_count       = sum(1 for w in words if w['solved'])
        attempt.save()

        all_done = attempt.correct_count == len(words)

        if all_done:
            xp = attempt.correct_count * attempt.config.xp_per_word
            attempt.xp_earned    = xp
            attempt.coins_earned = attempt.config.coin_reward
            attempt.completed_at = timezone.now()
            attempt.save()
            contexto = {
                'segundos_restantes': attempt.remaining_seconds(),
                'erros': 3 - attempt.lives_remaining,
                'tentativas': attempt.correct_count + (3 - attempt.lives_remaining),
                'perfeito': attempt.lives_remaining == 3,
                'won': True,
            }
            grant_xp(request.user, xp, 'decriptar', 'Decriptar concluído', contexto=contexto)
            grant_coins(request.user, attempt.config.coin_reward, 'decriptar')
            registrar_desafio_diario(request.user)

        return JsonResponse({
            'correct':       True,
            'correct_count': attempt.correct_count,
            'all_done':      all_done,
            'redirect':      f'/minigames/decriptar/resultado/{attempt.id}/' if all_done else None,
        })

    else:
        attempt.lives_remaining = max(0, attempt.lives_remaining - 1)
        attempt.save()

        game_over = attempt.lives_remaining == 0
        if game_over:
            xp = attempt.correct_count * attempt.config.xp_per_word
            attempt.xp_earned    = xp
            attempt.coins_earned = attempt.config.coin_reward if attempt.correct_count > 0 else 0
            attempt.completed_at = timezone.now()
            attempt.save()
            if xp > 0:
                contexto={
                    'segundos_restantes': attempt.remaining_seconds(),
                    'tentativas': attempt.correct_count + (attempt.config.max_lives - attempt.lives_remaining),
                    'won': False,
                }
                grant_xp(request.user, xp, 'decriptar', 'Decriptar parcial', contexto=contexto)
            if attempt.coins_earned > 0:
                grant_coins(request.user, attempt.coins_earned, 'decriptar')
            registrar_desafio_diario(request.user)

        return JsonResponse({
            'correct':         False,
            'lives_remaining': attempt.lives_remaining,
            'game_over':       game_over,
            'redirect':        f'/minigames/decriptar/resultado/{attempt.id}/' if game_over else None,
        })


@login_required
@require_POST
def finish_decriptar(request):
    """Abandonar ou timer expirado (POST via JS)."""
    try:
        body          = json.loads(request.body)
        attempt_id    = body.get('attempt_id')
        timer_expired = body.get('timer_expired', False)
        abandoned     = body.get('abandoned', False)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Payload inválido.'}, status=400)

    attempt = DecriptarAttempt.objects.filter(
        pk=attempt_id, player=request.user, completed_at__isnull=True
    ).first()

    if not attempt:
        return JsonResponse({'error': 'Tentativa não encontrada.'}, status=404)

    xp = attempt.correct_count * attempt.config.xp_per_word
    attempt.xp_earned     = xp if not timer_expired else 0
    attempt.coins_earned  = attempt.config.coin_reward if (xp > 0 and not timer_expired) else 0
    attempt.timer_expired = timer_expired
    attempt.abandoned     = abandoned
    attempt.completed_at  = timezone.now()
    attempt.save()

    if attempt.xp_earned > 0:
        grant_xp(request.user, attempt.xp_earned, 'decriptar', 'Decriptar parcial', 
                 contexto={
                    'segundos_restantes': attempt.remaining_seconds(),
                    'tentativas': attempt.correct_count + (attempt.config.max_lives - attempt.lives_remaining),
                    'won': attempt.correct_count == len(attempt.words_sequence),
                })
    if attempt.coins_earned > 0:
        grant_coins(request.user, attempt.coins_earned, 'decriptar')

    return JsonResponse({'redirect': f'/minigames/decriptar/resultado/{attempt.id}/'})


@login_required
def decriptar_result(request, attempt_id):
    attempt      = get_object_or_404(DecriptarAttempt, pk=attempt_id, player=request.user)
    total_words  = len(attempt.words_sequence)
    is_perfect   = attempt.correct_count == total_words and total_words > 0

    return render(request, 'minigames/decriptar_result.html', {
        'attempt':     attempt,
        'total_words': total_words,
        'is_perfect':  is_perfect,
        'max_xp':      total_words * attempt.config.xp_per_word,
    })
# ─────────────────────────────────────────────
# CÓDIGO (Termo)
# ─────────────────────────────────────────────

@login_required
def start_codigo(request):
    config = CodigoConfig.objects.filter(ativo=True).first()

    if not config or not config.is_active_today():
        messages.error(request, 'Código não está disponível hoje.')
        return redirect('challenges:index')

    today   = timezone.localdate()
    attempt = CodigoAttempt.objects.filter(
        player=request.user, config=config, date=today
    ).first()

    if attempt and attempt.is_completed:
        return redirect('minigames:codigo_result', attempt_id=attempt.id)

    if attempt and not attempt.is_completed:
        if config.time_limit_seconds and attempt.remaining_seconds() == 0:
            attempt.timer_expired = True
            attempt.completed_at  = timezone.now()
            attempt.save()
            return redirect('minigames:codigo_result', attempt_id=attempt.id)
        return redirect('minigames:play_codigo')

    # Seleciona palavra — retorna objeto WordBank
    word_obj = config.select_word()
    if not word_obj:
        messages.error(request, f'Nenhuma palavra de {config.word_length} letras no banco. Avise o administrador.')
        return redirect('challenges:index')

    CodigoAttempt.objects.create(
        player      = request.user,
        config      = config,
        date        = today,
        secret_word = word_obj.palavra, 
        guesses     = [],
    )
    return redirect('minigames:play_codigo')


@login_required
def play_codigo(request):
    today   = timezone.localdate()
    config  = CodigoConfig.objects.filter(ativo=True).first()
    attempt = CodigoAttempt.objects.filter(
        player=request.user, config=config, date=today, completed_at__isnull=True
    ).first()

    if not attempt:
        messages.warning(request, 'Inicie o Código pela Central de Desafios.')
        return redirect('challenges:index')

    # Timer server-side
    if config.time_limit_seconds and attempt.remaining_seconds() == 0:
        attempt.timer_expired = True
        attempt.completed_at  = timezone.now()
        attempt.save()
        return redirect('minigames:codigo_result', attempt_id=attempt.id)

    # Envia apenas os guesses já feitos (com feedback), nunca a palavra secreta
    guesses_payload = json.dumps(attempt.guesses)

    # Busca a dica da palavra selecionada para exibir durante o jogo
    word_hint = WordBank.objects.filter(
        palavra=attempt.secret_word, ativo=True
    ).values_list('dica', flat=True).first() or ''

    return render(request, 'minigames/codigo.html', {
        'attempt':        attempt,
        'config':         config,
        'word_length':    len(attempt.secret_word),
        'max_attempts':   config.max_attempts,
        'remaining_time': attempt.remaining_seconds(),
        'guesses_payload': guesses_payload,
        'xp_reward':      config.xp_reward,
        'word_hint':       word_hint,
    })


@login_required
@require_POST
def check_codigo_guess(request):
    """AJAX — valida um guess. Palavra secreta nunca sai do servidor."""
    try:
        body       = json.loads(request.body)
        attempt_id = body.get('attempt_id')
        guess      = body.get('guess', '').upper().strip()
        abandoned  = body.get('abandoned', False)
        timed_out  = body.get('timed_out', False)
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Payload inválido.'}, status=400)

    attempt = CodigoAttempt.objects.filter(
        pk=attempt_id, player=request.user, completed_at__isnull=True
    ).first()

    if not attempt:
        return JsonResponse({'error': 'Tentativa não encontrada ou já encerrada.'}, status=404)

    config = attempt.config

    # Timer server-side — fonte de verdade
    if config.time_limit_seconds and attempt.remaining_seconds() == 0:
        timed_out = True

    # Abandonar / timeout sem processar guess
    if abandoned or timed_out:
        attempt.timer_expired = timed_out
        attempt.abandoned     = abandoned
        attempt.xp_earned     = 0
        attempt.completed_at  = timezone.now()
        attempt.save()
        return JsonResponse({
            'game_over': True,
            'redirect':  f'/minigames/codigo/resultado/{attempt.id}/',
        })

    secret = attempt.secret_word

    # Validações
    if len(guess) != len(secret):
        return JsonResponse({'error': f'A palavra deve ter {len(secret)} letras.'}, status=400)

    if not guess.isalpha():
        return JsonResponse({'error': 'Apenas letras são permitidas.'}, status=400)

    # Verifica se já atingiu máximo de tentativas
    if len(attempt.guesses) >= config.max_attempts:
        return JsonResponse({'error': 'Limite de tentativas atingido.'}, status=400)

    # Calcula feedback server-side
    feedback  = CodigoAttempt.check_guess(guess, secret)
    is_winner = all(f == 'correct' for f in feedback)

    # Salva guess no banco
    guesses = attempt.guesses
    guesses.append({'guess': guess, 'feedback': feedback})
    attempt.guesses = guesses

    attempts_used = len(guesses)
    game_over     = is_winner or attempts_used >= config.max_attempts

    if game_over:
        attempt.won          = is_winner
        attempt.completed_at = timezone.now()

        if is_winner:
            # XP cheio se acertou em até metade das tentativas, 50% depois
            half = config.max_attempts // 2
            xp   = config.xp_reward if attempts_used <= half else config.xp_reward // 2
            attempt.xp_earned    = xp
            attempt.coins_earned = config.coin_reward
        else:
            attempt.xp_earned    = 0
            attempt.coins_earned = 0

        attempt.save()

        if attempt.xp_earned > 0:
            grant_xp(request.user, attempt.xp_earned, 'codigo', f'Código: {attempt.secret_word}', 
                     contexto={
                        'segundos_restantes': attempt.remaining_seconds(),
                        'tentativas': len(attempt.guesses),
                        'won': attempt.won,
                    })
            if attempt.coins_earned > 0:
                grant_coins(request.user, attempt.coins_earned, 'codigo')
            registrar_desafio_diario(request.user)    
    else:
        attempt.save()

    return JsonResponse({
        'feedback':      feedback,
        'is_winner':     is_winner,
        'game_over':     game_over,
        'attempts_used': attempts_used,
        'redirect':      f'/minigames/codigo/resultado/{attempt.id}/' if game_over else None,
        # Revela a palavra apenas quando o jogo termina
        'secret_word':   secret if game_over and not is_winner else None,
    })


@login_required
def codigo_result(request, attempt_id):
    attempt    = get_object_or_404(CodigoAttempt, pk=attempt_id, player=request.user)
    is_perfect = attempt.won and len(attempt.guesses) <= attempt.config.max_attempts // 2

    return render(request, 'minigames/codigo_result.html', {
        'attempt':    attempt,
        'config':     attempt.config,
        'is_perfect': is_perfect,
        'max_xp':     attempt.config.xp_reward,
    })
