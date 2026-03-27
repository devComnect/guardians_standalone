"""
apps/store/signals.py
Dispara verificação de conquistas após compras na loja.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StoreTransaction
 
 
@receiver(post_save, sender=StoreTransaction)
def verificar_conquistas_apos_compra(sender, instance, created, **kwargs):
    if not created or instance.tipo != 'purchase':
        return
    from apps.profiles.services import verificar_conquistas
    verificar_conquistas(instance.player, 'shop_count')