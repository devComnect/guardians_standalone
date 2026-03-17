from django.urls import path
from . import views

app_name = 'minigames'

urlpatterns = [
    path('quiz/<int:quiz_id>/start/',  views.start_quiz,  name='start_quiz'),
    path('quiz/<int:quiz_id>/play/',   views.take_quiz,   name='take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/<int:quiz_id>/result/', views.quiz_result, name='quiz_result'),
    path('patrol/start/', views.patrol_start, name='patrol_start'),
    path('patrol/guess/', views.patrol_guess, name='patrol_guess'),
    path('cofre/',                          views.password_game_play,    name='password_play'),
    path('cofre/<int:attempt_id>/submit/',  views.password_game_submit,  name='password_submit'),
    path('cofre/<int:attempt_id>/abandon/', views.password_game_abandon, name='password_abandon'),
    path('cofre/<int:attempt_id>/resultado/', views.password_result,     name='password_result'),
]