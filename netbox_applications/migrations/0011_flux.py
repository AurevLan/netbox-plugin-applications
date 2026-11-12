"""Flux — l'autre moitié d'une matrice : depuis où atteint-on quoi.

NetBox décrit déjà le côté destination d'un flux, par son objet « Service » :
un protocole, des ports, une machine. Il ne dit rien de la SOURCE, et sans
source il n'y a pas de matrice mais une liste de ports ouverts.

Les deux extrémités sont des RÉFÉRENCES GÉNÉRIQUES vers de vrais objets NetBox
— préfixe, plage, adresse, VM, équipement, serveur virtuel, ou le déploiement
d'une autre application. Un texte libre se dédoublerait à la première faute de
frappe et ne se résoudrait en aucune adresse.

Le flux est rattaché au DÉPLOIEMENT, donc au couple application et
environnement : c'est ce qui permet d'obtenir la matrice d'une recette sans la
mélanger avec celle de sa production.
"""


import django.contrib.postgres.fields
import django.db.models.deletion
import netbox.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

# Les nœuds « squashed » ci-dessous sont présents de NetBox 4.5 à 4.7.
# « makemigrations » avait épinglé extras 0144 et ipam 0097 — les dernières
# migrations de l'hôte 4.7 sur lequel ce fichier a été généré. Les laisser
# telles quelles rendait le plugin ININSTALLABLE sur le plancher qu'il annonce,
# sans qu'aucun contrôle local ne le signale. Si vous régénérez cette migration,
# REVÉRIFIEZ ces quatre lignes.
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('extras', '0002_squashed_0059'),
        ('ipam', '0002_squashed_0046'),
        ('netbox_applications', '0010_serveur_virtuel_et_waf'),
    ]

    operations = [
        migrations.CreateModel(
            name='Flow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('source_id', models.PositiveBigIntegerField()),
                ('destination_id', models.PositiveBigIntegerField()),
                ('port_mappings', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=63), blank=True, default=list)),
                ('status', models.CharField(default='demande', max_length=20)),
                ('justification', models.CharField(blank=True, max_length=200)),
                ('firewall_reference', models.CharField(blank=True, max_length=100)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('comments', models.TextField(blank=True)),
                ('deployment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='flows', to='netbox_applications.deployment')),
                ('destination_type', models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'ipam'), ('model', 'prefix')), models.Q(('app_label', 'ipam'), ('model', 'iprange')), models.Q(('app_label', 'ipam'), ('model', 'ipaddress')), models.Q(('app_label', 'virtualization'), ('model', 'virtualmachine')), models.Q(('app_label', 'dcim'), ('model', 'device')), models.Q(('app_label', 'netbox_applications'), ('model', 'virtualserver')), models.Q(('app_label', 'netbox_applications'), ('model', 'deployment')), _connector='OR'), on_delete=django.db.models.deletion.PROTECT, related_name='+', to='contenttypes.contenttype')),
                ('service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='application_flows', to='ipam.service')),
                ('source_type', models.ForeignKey(limit_choices_to=models.Q(models.Q(('app_label', 'ipam'), ('model', 'prefix')), models.Q(('app_label', 'ipam'), ('model', 'iprange')), models.Q(('app_label', 'ipam'), ('model', 'ipaddress')), models.Q(('app_label', 'virtualization'), ('model', 'virtualmachine')), models.Q(('app_label', 'dcim'), ('model', 'device')), models.Q(('app_label', 'netbox_applications'), ('model', 'virtualserver')), models.Q(('app_label', 'netbox_applications'), ('model', 'deployment')), _connector='OR'), on_delete=django.db.models.deletion.PROTECT, related_name='+', to='contenttypes.contenttype')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'flux',
                'verbose_name_plural': 'flux',
                'ordering': ('deployment', 'source_type', 'source_id', 'destination_type', 'destination_id'),
                'indexes': [models.Index(fields=['source_type', 'source_id'], name='netbox_appl_source__8e105d_idx'), models.Index(fields=['destination_type', 'destination_id'], name='netbox_appl_destina_cad14f_idx')],
                'constraints': [models.UniqueConstraint(condition=models.Q(('service__isnull', False)), fields=('deployment', 'source_type', 'source_id', 'destination_type', 'destination_id', 'service'), name='netbox_applications_flux_unique_avec_service', violation_error_message='Ce flux est déjà déclaré pour ce déploiement et ce service.')],
            },
            bases=(netbox.models.deletion.DeleteMixin, models.Model),
        ),
    ]
