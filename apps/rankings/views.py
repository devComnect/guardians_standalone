# Adicionar em cada views.py que ainda está vazio:
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    return render(request, 'coming_soon.html')  # temporário