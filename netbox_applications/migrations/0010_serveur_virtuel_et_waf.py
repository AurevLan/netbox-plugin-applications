"""Serveur virtuel et pare-feu applicatif.

Le WAF est porté par le DÉPLOIEMENT et non par l'application : la production
est souvent protégée quand la recette ne l'est pas, et c'est précisément cet
écart qu'on veut pouvoir constater.

Le préfixe du serveur virtuel n'est pas stocké : NetBox sait déjà quel préfixe
contient une adresse, et le dupliquer créerait une seconde vérité, fausse dès
le premier redécoupage. Il est calculé à l'affichage.
"""

import django.core.validators
import django.db.models.deletion
import netbox.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):


# DÉPENDANCES VOLONTAIREMENT RELÂCHÉES — ne pas les laisser se réépingler.
#
# « makemigrations » épingle, au moment où on le lance, la DERNIÈRE migration
# de chaque application référencée. C'est une commodité de génération, pas un
# besoin : ce dont ces modèles ont réellement besoin, c'est que les tables
# référencées EXISTENT.
#
# Épinglées sur la dernière, ces dépendances rendaient le plugin
# INSTALLABLE SUR UNE SEULE VERSION DE NETBOX : sur une version antérieure, le
# nœud n'existe pas et le graphe de migration refuse de se résoudre.
#
# Les nœuds ci-dessous sont des migrations « squashed », présentes de NetBox
# 4.5 à 4.7. Si vous régénérez une migration, VÉRIFIEZ ses dépendances : Django
# y remettra celles de l'hôte sur lequel vous l'avez générée.
    dependencies = [
        ('extras', '0002_squashed_0059'),
        ('ipam', '0002_squashed_0046'),
        ('netbox_applications', '0009_contrainte_unicite_retablie'),
    ]

    operations = [
        migrations.AddField(
            model_name='deployment',
            name='waf_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='VirtualServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('port', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)])),
                ('description', models.CharField(blank=True, max_length=200)),
                ('comments', models.TextField(blank=True)),
                ('ip_address', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='virtual_servers', to='ipam.ipaddress')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
            ],
            options={
                'verbose_name': 'serveur virtuel',
                'verbose_name_plural': 'serveurs virtuels',
                'ordering': ('name',),
            },
            bases=(netbox.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.AddField(
            model_name='deployment',
            name='waf_virtual_server',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='deployments', to='netbox_applications.virtualserver'),
        ),
    ]
