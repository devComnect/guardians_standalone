"""
apps/store/urls.py
"""
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Páginas
    path('',                  views.index,                   name='index'),
    path('inventario/',       views.inventario,              name='inventario'),

    # Ajax / fetch endpoints
    path('reroll/',                 views.ajax_reroll,               name='ajax_reroll'),
    path('comprar/',                views.ajax_comprar,              name='ajax_comprar'),
    path('vender/',                 views.ajax_vender,               name='ajax_vender'),
    path('ativar/',                 views.ajax_ativar_consumivel,    name='ajax_ativar'),
    path('equipar-cosmético/',      views.ajax_equipar_cosmético,    name='ajax_equipar_cosmético'),
    path('desequipar-cosmético/',   views.ajax_desequipar_cosmético, name='ajax_desequipar_cosmético'),
    path('inventario/estado/',      views.ajax_estado_inventario,    name='ajax_estado_inventario'),
]