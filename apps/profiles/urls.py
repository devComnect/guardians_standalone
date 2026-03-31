from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    # Páginas
    path('',        views.index,        name='index'),
    path('editar/', views.editar_perfil, name='editar'),

    # AJAX — Notificações
    path('notificacoes/lidas/', views.marcar_notificacoes_lidas, name='notif_lidas'),

    # AJAX — Conquistas
    path('conquista/destaque/',  views.toggle_conquista_destaque, name='conquista_destaque'),

    # AJAX — Inventário
    path('cosmetico/equipar/',   views.equipar_cosmetico,  name='equipar_cosmetico'),
    path('retake/usar/',         views.usar_retake_token,  name='usar_retake'),

    # AJAX — Classe
    path('trocar-classe/',       views.trocar_classe_view, name='trocar_classe'),

    # AJAX — Passivos e Consumíveis
    path('passivo/equipar/',     views.equipar_passivo_view, name='equipar_passivo'),
    path('consumivel/usar/',     views.usar_consumivel_view, name='usar_consumivel'),

    path('battlepass/coletar/', views.coletar_tier_bp, name='bp_coletar'),
]