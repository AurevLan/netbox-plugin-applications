"""ÉTAPE 3 SUR 3 — nettoyage.

Les anciens champs texte sont retirés, et les clés étrangères temporaires
prennent leur nom définitif. Cette étape n'est exécutée qu'APRÈS le transfert :
c'est ce qui garantit qu'aucune valeur n'est perdue.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("netbox_applications", "0004_transfert_valeurs")]

    operations = [
        migrations.RemoveField(model_name="application", name="lifecycle_status"),
        migrations.RemoveField(model_name="application", name="criticality"),
        migrations.RemoveField(model_name="application", name="rto"),
        migrations.RemoveField(model_name="application", name="rpo"),
        migrations.RemoveField(model_name="application", name="service_hours"),
        migrations.RemoveField(model_name="application", name="data_classification"),
        migrations.RemoveField(model_name="application", name="authentication"),
        migrations.RemoveField(model_name="deployment", name="environment"),
        migrations.RemoveField(model_name="deployment", name="status"),
        migrations.RemoveField(model_name="deployment", name="maintenance_window"),
        migrations.RenameField(
            model_name="application",
            old_name="lifecycle_status_ref",
            new_name="lifecycle_status",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="criticality_ref",
            new_name="criticality",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="rto_ref",
            new_name="rto",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="rpo_ref",
            new_name="rpo",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="service_hours_ref",
            new_name="service_hours",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="data_classification_ref",
            new_name="data_classification",
        ),
        migrations.RenameField(
            model_name="application",
            old_name="authentication_ref",
            new_name="authentication",
        ),
        migrations.RenameField(
            model_name="deployment",
            old_name="environment_ref",
            new_name="environment",
        ),
        migrations.RenameField(
            model_name="deployment",
            old_name="status_ref",
            new_name="status",
        ),
        migrations.RenameField(
            model_name="deployment",
            old_name="maintenance_window_ref",
            new_name="maintenance_window",
        ),
        migrations.AlterField(
            model_name="deployment",
            name="environment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="deployments",
                to="netbox_applications.environment",
                verbose_name="Environnement",
            ),
        ),
    ]
