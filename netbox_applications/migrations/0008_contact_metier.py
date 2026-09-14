"""Contact métier — un champ libre, mais au format imposé.

Les deux référents existants pointent vers l'annuaire de contacts de NetBox.
Le responsable métier, lui, n'y figure que rarement : c'est souvent un
responsable de service ou une liste de diffusion. Exiger sa création préalable
conduirait à laisser le champ vide — ce qui est pire qu'une adresse saisie à
la main.

Le champ est donc libre, mais son FORMAT est imposé : « EmailField » refuse
tout ce qui n'est pas une adresse. Une adresse est ce dont on a besoin en
incident, et c'est la seule chose qu'on puisse à la fois valider et utiliser.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("netbox_applications", "0007_niveaux_distincts")]

    operations = [
        migrations.AddField(
            model_name="application",
            name="business_contact",
            field=models.EmailField(
                blank=True,
                help_text="Adresse de courriel du responsable métier, ou de sa liste de diffusion.",
                max_length=254,
                verbose_name="Contact métier",
            ),
        ),
    ]
