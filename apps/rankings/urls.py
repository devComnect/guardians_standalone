from django.urls import path
from . import views

app_name = 'rankings'

urlpatterns = [
    path('', views.index, name='index'),
    path('temporadas/',         views.temporadas_anteriores, name='temporadas_anteriores'),
]