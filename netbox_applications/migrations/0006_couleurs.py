"""Palette des référentiels : couleurs lisibles, et réparation des invalides.

DEUX CHOSES À LA FOIS.

1. RÉPARATION. La migration 0004 écrivait des NOMS de couleur (« red », « blue »)
   dans un ColorField, qui attend un hexadécimal sur six caractères. Une
   migration de données n'appelle pas full_clean() : rien n'a protesté, et les
   badges s'affichaient sans couleur. Ces valeurs sont corrigées ici.

2. PALETTE. Les couleurs ne sont pas décoratives, elles portent un sens :

   - La CHALEUR indique l'exigence ou le risque. Rouge sombre = contrainte la
     plus forte (RTO de 15 minutes, donnée restreinte, aucune fenêtre de
     maintenance). Vert = exigence faible. Le regard classe sans lire.
   - Le GRIS est réservé à l'absence d'engagement ou de valeur : « au mieux »,
     « à définir », « retiré ».
   - Les TEINTES FROIDES (bleu, violet, cyan, turquoise) désignent les
     authentifications centralisées ; les teintes chaudes, celles qui ne le
     sont pas. La couleur redit ce que dit l'attribut « is_centralized ».

CE QUE CETTE MIGRATION NE FAIT PAS : écraser un choix de l'exploitant. Une
valeur dont la couleur est déjà valide et différente du gris par défaut est
laissée telle quelle. La palette ne s'applique qu'aux couleurs invalides ou
restées au gris d'origine.
"""

from django.db import migrations

GRIS_DEFAUT = "9e9e9e"

# Les codes sont écrits en clair : une migration doit rester lisible et
# autonome, sans dépendre d'un module de l'application qui peut changer.
ROUGE_SOMBRE = "aa1409"
ROUGE = "f44336"
ORANGE = "ff9800"
AMBRE = "ffc107"
VERT_CLAIR = "8bc34a"
VERT = "4caf50"
VERT_SOMBRE = "2f6a31"
BLEU = "2196f3"
BLEU_CLAIR = "03a9f4"
INDIGO = "3f51b5"
CYAN = "00bcd4"
TURQUOISE = "009688"
VIOLET = "9c27b0"
VIOLET_SOMBRE = "673ab7"
GRIS = GRIS_DEFAUT

PALETTE = {
    # Cycle de vie : neutre tant que le service n'est pas rendu, vert une fois
    # en service, orange pendant le retrait, gris une fois éteint.
    "LifecycleStatus": {
        "en-projet": BLEU,
        "en-service": VERT,
        "en-retrait": ORANGE,
        "retire": GRIS,
    },
    "Criticality": {
        "critique": ROUGE_SOMBRE,
        "majeure": ROUGE,
        "standard": BLEU,
        "mineure": VERT_CLAIR,
    },
    # RTO et RPO : plus l'engagement est court, plus la couleur est chaude.
    "RTO": {
        "15m": ROUGE_SOMBRE,
        "1h": ROUGE,
        "4h": ORANGE,
        "8h": AMBRE,
        "24h": VERT_CLAIR,
        "72h": VERT,
        "best-effort": GRIS,
    },
    "RPO": {
        "0": ROUGE_SOMBRE,
        "15m": ROUGE,
        "1h": ORANGE,
        "4h": AMBRE,
        "24h": VERT_CLAIR,
        "best-effort": GRIS,
    },
    # Horaires : la couleur dit l'ampleur de la couverture attendue.
    "ServiceHours": {
        "24-7": ROUGE_SOMBRE,
        "7h-20h": ORANGE,
        "8h-18h": BLEU,
        "8h-18h-astreinte": VIOLET,
    },
    # Classification : la gradation de sensibilité, du public au restreint.
    "DataClassification": {
        "public": VERT,
        "interne": BLEU,
        "confidentiel": ORANGE,
        "restreint": ROUGE_SOMBRE,
    },
    # Authentification : froid = centralisé, chaud = comptes hors révocation
    # centralisée. La couleur double l'attribut, elle ne le remplace pas.
    "AuthenticationMethod": {
        "keycloak": VIOLET,
        "azure-ad": INDIGO,
        "entra-id": INDIGO,
        "oidc": BLEU,
        "saml": BLEU_CLAIR,
        "ldap": CYAN,
        "active-directory": TURQUOISE,
        "kerberos": VIOLET_SOMBRE,
        "cas": VERT_SOMBRE,
        "locale": ORANGE,
        "aucune": ROUGE_SOMBRE,
    },
    # Environnement : le rouge signale l'endroit où une erreur se paie.
    "Environment": {
        "production": ROUGE,
        "preproduction": ORANGE,
        "recette": AMBRE,
        "developpement": VERT,
    },
    "DeploymentStatus": {
        "actif": VERT,
        "planifie": BLEU,
        "en-demantelement": ORANGE,
        "hors-ligne": GRIS,
    },
    # Maintenance : vert quand on peut intervenir librement, rouge quand aucune
    # interruption n'est admise.
    "MaintenanceWindow": {
        "a-tout-moment": VERT,
        "hors-heures-ouvrees": VERT_CLAIR,
        "week-end": BLEU,
        "nuit-dimanche": INDIGO,
        "aucune-24-7": ROUGE_SOMBRE,
        "a-definir": GRIS,
    },
}

HEXA = set("0123456789abcdef")


def _valide(couleur):
    """Un ColorField n'accepte que six caractères hexadécimaux, sans « # »."""
    return bool(couleur) and len(couleur) == 6 and set(couleur.lower()) <= HEXA


def appliquer(apps, schema_editor):
    for nom_modele, couleurs in PALETTE.items():
        modele = apps.get_model("netbox_applications", nom_modele)
        for objet in modele.objects.all():
            voulue = couleurs.get(objet.slug)
            if voulue is None:
                # Valeur ajoutée par l'exploitant : on répare une couleur
                # invalide, mais on n'invente pas de palette pour elle.
                if not _valide(objet.color):
                    objet.color = GRIS_DEFAUT
                    objet.save(update_fields=["color"])
                continue
            # On ne touche qu'aux couleurs cassées ou restées au gris d'origine.
            if not _valide(objet.color) or objet.color == GRIS_DEFAUT:
                if objet.color != voulue:
                    objet.color = voulue
                    objet.save(update_fields=["color"])


def revenir(apps, schema_editor):
    """Rien à défaire : une couleur invalide n'est pas un état à restaurer."""


class Migration(migrations.Migration):
    dependencies = [("netbox_applications", "0005_nettoyage")]
    operations = [migrations.RunPython(appliquer, revenir)]
