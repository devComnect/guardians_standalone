"""
Migration de dados — Pacote de Cargas
- Seta disponivel=False nos consumíveis individuais (item_id 1–8)
- Cria o item 9 (Pacote de Cargas) com effect LOOT_PACK
"""

from django.db import migrations


def criar_pacote_cargas(apps, schema_editor):
    Item = apps.get_model('store', 'Item')

    # Desativa consumíveis individuais da loja (não somem do inventário, só da vitrine)
    Item.objects.filter(item_id__in=[1, 2, 3, 4, 5, 6, 7, 8]).update(disponivel=False)

    # Cria o Pacote de Cargas — só aparece na loja
    Item.objects.get_or_create(
        item_id=9,
        defaults=dict(
            name='Pacote de Cargas',
            description=(
                'Abre um pacote misterioso e dropa 1 consumível aleatório. '
                'Itens raros têm menor chance de aparecer.'
            ),
            tipo='consumable',
            raridade='COMMON',
            build='LUCK',
            effect='LOOT_PACK',
            value=0,
            value_secondary=0,
            duration_days=0,
            max_bonus=0,
            cost=25,
            disponivel=True,
            icon='bi-box-seam-fill',
        )
    )


def reverter(apps, schema_editor):
    Item = apps.get_model('store', 'Item')
    Item.objects.filter(item_id__in=[1, 2, 3, 4, 5, 6, 7, 8]).update(disponivel=True)
    Item.objects.filter(item_id=9).delete()


class Migration(migrations.Migration):

    dependencies = [
        # Ajuste para o nome real da sua última migration do app store
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_pacote_cargas, reverter),
    ]