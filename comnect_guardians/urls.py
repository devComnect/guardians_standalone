from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('',          include('apps.core.urls')),
    path('perfil/',   include('apps.profiles.urls')),
    path('desafios/', include('apps.challenges.urls')),
    path('minigames/',include('apps.minigames.urls')),
    path('rankings/', include('apps.rankings.urls')),
    path('loja/',     include('apps.store.urls')),
    path('feedback/', include('apps.feedback.urls')),
    path('missions/', include('apps.missions.urls')), #botão de resgate
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
        path('nested_admin/', include('nested_admin.urls')),
    ] + urlpatterns