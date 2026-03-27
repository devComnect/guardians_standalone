from django.urls import path
from .services import MissionService
from django.shortcuts import redirect
from django.contrib import messages

def claim_mission_reward(request):
    success, message = MissionService.claim_reward(request.user)
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('core:home') # Nome da sua rota da home

urlpatterns = [
    path('claim/', claim_mission_reward, name='mission_claim'), 
]