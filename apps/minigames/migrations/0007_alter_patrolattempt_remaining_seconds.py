from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('minigames', '0006_patrolattempt_remaining_seconds'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE minigames_patrolattempt ALTER COLUMN remaining_seconds TYPE integer USING 0",
            reverse_sql="ALTER TABLE minigames_patrolattempt ALTER COLUMN remaining_seconds TYPE timestamp with time zone USING NULL",
        ),
        migrations.AlterField(
            model_name='patrolattempt',
            name='remaining_seconds',
            field=models.PositiveIntegerField(default=0),
        ),
    ]