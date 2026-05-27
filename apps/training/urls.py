from django.urls import path
from . import views

app_name = 'training'

urlpatterns = [
    path('',        views.training_home,    name='home'),
    path('quizzes/', views.galeria_quizzes, name='galeria_quizzes'),
    path('termos/',  views.galeria_termos,  name='galeria_termos'),
]