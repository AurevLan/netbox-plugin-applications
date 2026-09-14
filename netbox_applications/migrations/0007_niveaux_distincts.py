"""Distinguer le CYCLE DE VIE DU SERVICE de l'ÉTAT D'UNE INSTANCE.

Les deux listes se répondaient terme à terme — « En service » / « Actif »,
« Retiré » / « Hors ligne » — au point de passer pour un doublon. Le doublon
était dans le VOCABULAIRE, pas dans le sens :

  cycle de vie du service — « l'organisation offre-t-elle encore ce service ? »
  état d'instance         — « cette instance-là tourne-t-elle ? »

Un service en exploitation peut avoir une instance de développement encore
planifiée. Un seul champ ne saurait dire les deux.

Cette migration rend le niveau explicite dans les libellés, et renomme les
valeurs de l'état d'instance pour qu'elles ne se confondent plus avec les
étapes du cycle de vie.

CE QU'ELLE NE FAIT PAS : renommer une valeur que l'exploitant a lui-même
modifiée. Seules les valeurs restées telles que la migration 0004 les avait
créées sont renommées.
"""

from django.db import migrations, models

# (slug, nom d'origine, nouveau nom) — le nom d'origine sert de garde : s'il a
# changé, c'est que quelqu'un l'a voulu, et on n'y touche pas.
RENOMMAGES = [
    ("actif", "Actif", "En exploitation"),
    ("hors-ligne", "Hors ligne", "Arrêté"),
]


def renommer(apps, schema_editor):
    modele = apps.get_model("netbox_applications", "DeploymentStatus")
    for slug, origine, nouveau in RENOMMAGES:
        modele.objects.filter(slug=slug, name=origine).update(name=nouveau)


def revenir(apps, schema_editor):
    modele = apps.get_model("netbox_applications", "DeploymentStatus")
    for slug, origine, nouveau in RENOMMAGES:
        modele.objects.filter(slug=slug, name=nouveau).update(name=origine)


class Migration(migrations.Migration):
    dependencies = [("netbox_applications", "0006_couleurs")]

    operations = [
        migrations.AlterModelOptions(
            name="lifecyclestatus",
            options={
                "ordering": ("weight", "name"),
                "verbose_name": "étape du cycle de vie",
                "verbose_name_plural": "étapes du cycle de vie",
            },
        ),
        migrations.AlterModelOptions(
            name="deploymentstatus",
            options={
                "ordering": ("weight", "name"),
                "verbose_name": "état d'instance",
                "verbose_name_plural": "états d'instance",
            },
        ),
        migrations.AlterField(
            model_name="lifecyclestatus",
            name="is_operational",
            field=models.BooleanField(
                default=False,
                help_text="À cette étape, le service est-il rendu au métier ?",
                verbose_name="Service rendu",
            ),
        ),
        migrations.AlterField(
            model_name="deploymentstatus",
            name="is_active",
            field=models.BooleanField(
                default=False,
                help_text="Cet état correspond-il à une instance qui tourne réellement ?",
                verbose_name="En fonctionnement",
            ),
        ),
        migrations.AlterField(
            model_name="application",
            name="lifecycle_status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="applications",
                to="netbox_applications.lifecyclestatus",
                verbose_name="Cycle de vie du service",
            ),
        ),
        migrations.AlterField(
            model_name="deployment",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="deployments",
                to="netbox_applications.deploymentstatus",
                verbose_name="État de l'instance",
            ),
        ),
        migrations.RunPython(renommer, revenir),
    ]
