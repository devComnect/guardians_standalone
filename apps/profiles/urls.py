from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('',                        views.index,                    name='index'),
    path('notificacoes/lidas/',     views.marcar_notificacoes_lidas,name='notif_lidas'),
    path('trocar-classe/',          views.trocar_classe_view,       name='trocar_classe'),
]