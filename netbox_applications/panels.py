"""Panneaux d'affichage des référentiels.

Depuis NetBox 4.7, une fiche d'objet se décrit par une DISPOSITION déclarée sur
la vue, et non plus par un gabarit HTML. Un référentiel sans disposition ni
gabarit produit une erreur 500 — c'est ce qui manquait en 0.4.0 et 0.4.1.

Les attributs propres à chaque référentiel sont DÉDUITS DU MODÈLE, jamais
recopiés : ajouter un champ à un référentiel l'affiche sans toucher ce fichier,
et son libellé reste défini à un seul endroit, le « verbose_name » du champ.
"""

from django.db import models

from netbox.ui import attrs, panels

# Champs déjà portés par OrganizationalObjectPanel ou par la base commune :
# les afficher deux fois serait du bruit.
_DEJA_AFFICHES = {
    "id",
    "name",
    "slug",
    "description",
    "comments",
    "created",
    "last_updated",
    "custom_field_data",
    "color",
    "weight",
}


def _attribut(champ):
    """Choisit la représentation adaptée au type du champ Django."""
    libelle = champ.verbose_name.capitalize() if champ.verbose_name else champ.name
    if isinstance(champ, models.BooleanField):
        return attrs.BooleanAttr(champ.name, label=libelle)
    if isinstance(champ, models.IntegerField):
        return attrs.NumericAttr(champ.name, label=libelle)
    return attrs.TextAttr(champ.name, label=libelle)


def panneau_pour(modele):
    """Produit la classe de panneau décrivant un référentiel."""
    declares = {
        "slug": attrs.TextAttr("slug", label="Slug"),
        "color": attrs.ColorAttr("color"),
        "weight": attrs.NumericAttr("weight", label="Rang"),
    }
    for champ in modele._meta.get_fields():
        if not getattr(champ, "concrete", False) or champ.name in _DEJA_AFFICHES:
            continue
        declares[champ.name] = _attribut(champ)

    return type(f"{modele.__name__}Panel", (panels.OrganizationalObjectPanel,), declares)
