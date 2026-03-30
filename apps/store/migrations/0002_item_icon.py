from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='icon',
            field=models.CharField(
                max_length=60,
                default='bi-box',
                verbose_name='Ícone Bootstrap Icons',
                help_text='Classe do Bootstrap Icons (ex: bi-cpu-fill). Gerado automaticamente — pode sobrescrever.'
            ),
        ),
    ]