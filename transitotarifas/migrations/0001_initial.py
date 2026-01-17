# Generated migration - Eliminates old table and creates new structure

from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('departamentos', '0001_initial'),
        ('municipios', '0001_initial'),
        ('tramites', '0002_remove_historicaltramite_precio_and_more'),
        ('proveedores', '0001_initial'),
    ]

    operations = [
        # Drop old tables if exists
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS `transito_tarifas`;',
            reverse_sql='',
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS `transito_tarifa_tramites`;',
            reverse_sql='',
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS `transito_tarifa_gestores`;',
            reverse_sql='',
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS `historical_transitotarifa`;',
            reverse_sql='',
        ),
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS `transitotarifas_historicaltransitotarifa`;',
            reverse_sql='',
        ),

        # Create TransitoTarifa model
        migrations.CreateModel(
            name='TransitoTarifa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, help_text='Indica si la configuración está activa')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Fecha y hora de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Fecha y hora de última actualización')),
                ('departamento', models.ForeignKey(help_text='Departamento donde aplica esta configuración', on_delete=django.db.models.deletion.PROTECT, related_name='transito_tarifas', to='departamentos.departamento')),
                ('municipio', models.ForeignKey(help_text='Municipio donde aplica esta configuración', on_delete=django.db.models.deletion.PROTECT, related_name='transito_tarifas', to='municipios.municipio')),
            ],
            options={
                'verbose_name': 'Tránsito Tarifa',
                'verbose_name_plural': 'Tránsitos Tarifas',
                'db_table': 'transito_tarifas',
                'ordering': ['departamento__departamento', 'municipio__municipio'],
            },
        ),

        # Create TransitoTarifaTramite model
        migrations.CreateModel(
            name='TransitoTarifaTramite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('derechos_2026', models.DecimalField(decimal_places=2, help_text='Derechos de tránsito para 2026', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Fecha y hora de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Fecha y hora de última actualización')),
                ('tramite', models.ForeignKey(help_text='Trámite configurado', on_delete=django.db.models.deletion.PROTECT, related_name='transito_tarifas', to='tramites.tramite')),
                ('transito_tarifa', models.ForeignKey(help_text='Configuración de ubicación a la que pertenece', on_delete=django.db.models.deletion.CASCADE, related_name='tramites', to='transitotarifas.transitotarifa')),
            ],
            options={
                'verbose_name': 'Tránsito Tarifa Trámite',
                'verbose_name_plural': 'Tránsitos Tarifas Trámites',
                'db_table': 'transito_tarifa_tramites',
                'ordering': ['tramite__nombre'],
            },
        ),

        # Create TransitoTarifaGestor model
        migrations.CreateModel(
            name='TransitoTarifaGestor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('servicio_gestor', models.DecimalField(decimal_places=2, help_text='Precio que cobra el gestor', max_digits=10)),
                ('servicio_empresa', models.DecimalField(decimal_places=2, help_text='Precio que cobra la empresa al cliente', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Fecha y hora de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Fecha y hora de última actualización')),
                ('proveedor', models.ForeignKey(help_text='Proveedor/Gestor que realiza el trámite', on_delete=django.db.models.deletion.PROTECT, related_name='transito_tarifa_gestores', to='proveedores.proveedor')),
                ('tramite_tarifa', models.ForeignKey(help_text='Trámite al que pertenece este gestor', on_delete=django.db.models.deletion.CASCADE, related_name='gestores', to='transitotarifas.transitotarifatramite')),
            ],
            options={
                'verbose_name': 'Tránsito Tarifa Gestor',
                'verbose_name_plural': 'Tránsitos Tarifas Gestores',
                'db_table': 'transito_tarifa_gestores',
                'ordering': ['proveedor__nombre'],
            },
        ),

        # Create HistoricalTransitoTarifa for audit trail
        migrations.CreateModel(
            name='HistoricalTransitoTarifa',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, help_text='Indica si la configuración está activa')),
                ('created_at', models.DateTimeField(blank=True, editable=False, help_text='Fecha y hora de creación')),
                ('updated_at', models.DateTimeField(blank=True, editable=False, help_text='Fecha y hora de última actualización')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('departamento', models.ForeignKey(blank=True, db_constraint=False, help_text='Departamento donde aplica esta configuración', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='departamentos.departamento')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='user.user')),
                ('municipio', models.ForeignKey(blank=True, db_constraint=False, help_text='Municipio donde aplica esta configuración', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='municipios.municipio')),
            ],
            options={
                'verbose_name': 'historical Tránsito Tarifa',
                'verbose_name_plural': 'historical Tránsitos Tarifas',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),

        # Add unique constraints
        migrations.AlterUniqueTogether(
            name='transitotarifa',
            unique_together={('departamento', 'municipio')},
        ),
        migrations.AlterUniqueTogether(
            name='transitotarifatramite',
            unique_together={('transito_tarifa', 'tramite')},
        ),
        migrations.AlterUniqueTogether(
            name='transitotarifagestor',
            unique_together={('tramite_tarifa', 'proveedor')},
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='transitotarifa',
            index=models.Index(fields=['departamento', 'municipio'], name='transito_ta_departa_0e7c8c_idx'),
        ),
        migrations.AddIndex(
            model_name='transitotarifa',
            index=models.Index(fields=['is_active'], name='transito_ta_is_acti_c5f8e9_idx'),
        ),
        migrations.AddIndex(
            model_name='transitotarifa',
            index=models.Index(fields=['created_at'], name='transito_ta_created_d6e7f8_idx'),
        ),
        migrations.AddIndex(
            model_name='transitotarifatramite',
            index=models.Index(fields=['transito_tarifa', 'tramite'], name='transito_ta_transit_1a2b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='transitotarifatramite',
            index=models.Index(fields=['created_at'], name='transito_ta_created_4d5e6f_idx'),
        ),
        migrations.AddIndex(
            model_name='transitotarifagestor',
            index=models.Index(fields=['tramite_tarifa', 'proveedor'], name='transito_ta_tramite_7g8h9i_idx'),
        ),
        migrations.AddIndex(
            model_name='transitotarifagestor',
            index=models.Index(fields=['created_at'], name='transito_ta_created_0j1k2l_idx'),
        ),
    ]
