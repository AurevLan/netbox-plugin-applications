"""Rétablir la contrainte d'unicité, perdue sans que rien ne le signale.

CE QUI S'EST PASSÉ. La migration 0001 créait bien la contrainte
« unique_application_environment » sur (application, environment). La migration
0005 a ensuite supprimé l'ancien champ texte « environment » — et PostgreSQL a
supprimé avec lui toute contrainte qui en dépendait. Le renommage de
« environment_ref » en « environment » a recréé le champ, mais PAS la
contrainte.

POURQUOI PERSONNE NE L'A VU. L'état de migration de Django, lui, croit toujours
la contrainte présente : elle a été déclarée en 0001 et jamais retirée de
l'état. « makemigrations --check » compare les MODÈLES à l'ÉTAT, jamais à la
base réelle — il ne pouvait donc rien détecter. La divergence entre l'état et
la base est invisible à tout l'outillage de Django.

Seul un test qui tente RÉELLEMENT de créer un doublon l'a révélée.

CETTE MIGRATION NE TOUCHE PAS À L'ÉTAT : il est déjà correct. Elle ne corrige
que la base, d'où « SeparateDatabaseAndState » avec un état vide.
"""

from django.db import migrations

TABLE = "netbox_applications_deployment"
CONTRAINTE = "unique_application_environment"


class Migration(migrations.Migration):
    dependencies = [("netbox_applications", "0008_contact_metier")]

    operations = [
        migrations.SeparateDatabaseAndState(
            # L'état de Django porte déjà la contrainte : y toucher créerait un
            # doublon dans l'état et ferait diverger les migrations suivantes.
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    # « IF EXISTS » : la contrainte est absente des bases issues
                    # de 0005, présente sur toute base qui l'aurait rétablie à la
                    # main. La migration doit passer dans les deux cas.
                    sql=[
                        f"ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS {CONTRAINTE};",
                        f"ALTER TABLE {TABLE} ADD CONSTRAINT {CONTRAINTE} "
                        f"UNIQUE (application_id, environment_id);",
                    ],
                    reverse_sql=[
                        f"ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS {CONTRAINTE};",
                    ],
                )
            ],
        )
    ]
