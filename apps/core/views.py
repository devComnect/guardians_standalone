from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import AdminPost
from apps.minigames.models import PatrolAttempt


@login_required
def home(request):
    posts  = AdminPost.objects.filter(publicado=True)[:10]
    player = getattr(request.user, 'player', None)

    patrol_attempt = PatrolAttempt.objects.filter(
        player=request.user,
        date=timezone.localdate(),
        completed=True
    ).first()

    patrol_done = patrol_attempt is not None
    patrol_won  = patrol_attempt.won if patrol_attempt else False

    return render(request, 'core/home.html', {
        'posts':       posts,
        'player':      player,
        'patrol_done': patrol_done,
        'patrol_won':  patrol_won,
    })