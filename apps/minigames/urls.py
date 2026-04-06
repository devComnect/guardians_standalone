from django.urls import path
from . import views

app_name = 'minigames'

urlpatterns = [
    #QUIZ
    path('quiz/<int:quiz_id>/start/',  views.start_quiz,  name='start_quiz'),
    path('quiz/<int:quiz_id>/play/',   views.take_quiz,   name='take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/<int:quiz_id>/result/', views.quiz_result, name='quiz_result'),
    # PATRULHA
    path('patrol/start/', views.patrol_start, name='patrol_start'),
    path('patrol/guess/', views.patrol_guess, name='patrol_guess'),
    # COFRE
    path('cofre/',                          views.password_game_play,    name='password_play'),
    path('cofre/<int:attempt_id>/submit/',  views.password_game_submit,  name='password_submit'),
    path('cofre/<int:attempt_id>/abandon/', views.password_game_abandon, name='password_abandon'),
    path('cofre/<int:attempt_id>/resultado/', views.password_result,     name='password_result'),
    # Decriptar
    path('decriptar/start/',                        views.start_decriptar,      name='start_decriptar'),
    path('decriptar/play/',                         views.play_decriptar,       name='play_decriptar'),
    path('decriptar/check/',                        views.check_decriptar_word, name='check_decriptar'),
    path('decriptar/finish/',                       views.finish_decriptar,     name='finish_decriptar'),
    path('decriptar/resultado/<int:attempt_id>/',   views.decriptar_result,     name='decriptar_result'),
    # Código
    path('codigo/start/',                      views.start_codigo,       name='start_codigo'),
    path('codigo/play/',                       views.play_codigo,        name='play_codigo'),
    path('codigo/check/',                      views.check_codigo_guess, name='check_codigo'),
    path('codigo/resultado/<int:attempt_id>/', views.codigo_result,      name='codigo_result'),
    #Retake
    path('retake/', views.retake_consumivel, name='retake_consumivel'),
    #Hint
    path('decriptar/hint/', views.request_hint_decriptar, name='hint_decriptar'),
    path('codigo/hint/', views.request_hint_codigo, name='hint_codigo'),
]