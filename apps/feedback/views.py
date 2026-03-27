from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json
from django.contrib import messages
from .models import Feedback, Feedback, FeedbackCoinConfig
from apps.profiles.services import verificar_conquistas



@login_required
def index(request):
    if request.method == 'POST' and request.content_type.startswith('multipart'):
        tipo      = request.POST.get('tipo')
        titulo    = request.POST.get('titulo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        anonimo   = request.POST.get('anonimo') == 'on'

        if not titulo or not descricao or tipo not in dict(Feedback.TIPO_CHOICES):
            messages.error(request, 'Preencha todos os campos obrigatórios.')
        else:
            anexo = request.FILES.get('anexo')

            # Validações de segurança do arquivo
            if anexo:
                TIPOS_PERMITIDOS = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
                TAMANHO_MAX      = 5 * 1024 * 1024  # 5MB

                if anexo.content_type not in TIPOS_PERMITIDOS:
                    messages.error(request, 'Formato inválido. Envie apenas PNG, JPG, WEBP ou GIF.')
                    return redirect('feedback:index')

                if anexo.size > TAMANHO_MAX:
                    messages.error(request, 'Arquivo muito grande. Máximo permitido: 5MB.')
                    return redirect('feedback:index')

            Feedback.objects.create(
                player    = request.user,
                tipo      = tipo,
                titulo    = titulo,
                descricao = descricao,
                anonimo   = anonimo,
                anexo     = anexo,
            )
            messages.success(request, 'Feedback enviado com sucesso!')
            verificar_conquistas(request.user, 'feedback_count')
            if tipo == 'vulnerabilidade':
                verificar_conquistas(request.user, 'vulnerability')
            return redirect('feedback:index')

    # Histórico do próprio player
    meus_feedbacks = Feedback.objects.filter(player=request.user).order_by('-criado_em')

    return render(request, 'feedback/index.html', {
        'tipos':          Feedback.TIPO_CHOICES,
        'meus_feedbacks': meus_feedbacks,
        'coin_config': FeedbackCoinConfig.get(),
    })

@login_required
@require_POST
def coletar_moedas(request):
    try:
        body       = json.loads(request.body)
        fb_id      = body.get('feedback_id')
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'Payload inválido.'}, status=400)

    fb = Feedback.objects.filter(
        pk=fb_id,
        player=request.user,
        status='resolvido',
        coins_collected=False,
        coin_reward__gt=0,
    ).first()

    if not fb:
        return JsonResponse({'error': 'Feedback não encontrado ou moedas já coletadas.'}, status=404)

    player = getattr(request.user, 'player', None)
    if player:
        player.coins += fb.coin_reward
        player.save()

    fb.coins_collected = True
    fb.save()

    return JsonResponse({
        'ok':          True,
        'coins_ganhas': fb.coin_reward,
        'novo_saldo':   player.coins if player else 0,
    })