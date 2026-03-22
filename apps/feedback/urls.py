from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('',                views.index,          name='index'),
    path('coletar-moedas/', views.coletar_moedas, name='coletar_moedas'),
]