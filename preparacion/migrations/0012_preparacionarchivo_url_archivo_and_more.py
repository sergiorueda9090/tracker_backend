# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preparacion', '0011_alter_historicalpreparacion_estado_tracker_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='preparacionarchivo',
            name='url_archivo',
            field=models.URLField(blank=True, help_text='URL pública del archivo en S3', max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='historicalpreparacionarchivo',
            name='url_archivo',
            field=models.URLField(blank=True, help_text='URL pública del archivo en S3', max_length=500, null=True),
        ),
    ]
