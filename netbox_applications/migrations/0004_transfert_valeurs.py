"""ÉTAPE 2 SUR 3 — transfert des valeurs vers les référentiels.

Cette migration crée un objet de référentiel pour chaque valeur que le plugin
proposait, puis y rattache les fiches existantes. **Aucune donnée n'est perdue.**

Les valeurs sont reprises telles qu'elles étaient définies dans l'ancien
fichier `choices.py`, y compris leurs libellés et leurs couleurs : une fiche
qui affichait « Critique — arrêt d'activité » continue de l'afficher.

Une valeur présente en base mais absente de cette table — issue de FIELD_CHOICES,
par exemple — donne lieu à un référentiel créé à la volée, plutôt qu'à une
perte silencieuse.
"""

from django.db import migrations
from django.utils.text import slugify

# (valeur, libellé, couleur, rang, attributs propres au référentiel)
REFERENTIELS = {
    "LifecycleStatus": [
        ("en-projet", "En projet", "blue", 10, {"is_operational": False}),
        ("en-service", "En service", "green", 20, {"is_operational": True}),
        ("en-retrait", "En cours de retrait", "orange", 30, {"is_operational": True}),
        ("retire", "Retiré", "grey", 40, {"is_operational": False}),
    ],
    "Criticality": [
        ("critique", "Critique — arrêt d'activité", "red", 10,
         {"incident_priority": "P1", "requires_oncall": True}),
        ("majeure", "Majeure — activité dégradée", "orange", 20,
         {"incident_priority": "P2", "requires_oncall": True}),
        ("standard", "Standard", "blue", 30, {"incident_priority": "P3"}),
        ("mineure", "Mineure — sans impact métier", "green", 40, {"incident_priority": "P4"}),
    ],
    "RTO": [
        ("15m", "15 minutes", "red", 10, {"minutes": 15}),
        ("1h", "1 heure", "red", 20, {"minutes": 60}),
        ("4h", "4 heures", "orange", 30, {"minutes": 240}),
        ("8h", "8 heures", "orange", 40, {"minutes": 480}),
        ("24h", "24 heures", "blue", 50, {"minutes": 1440}),
        ("72h", "72 heures", "blue", 60, {"minutes": 4320}),
        ("best-effort", "Au mieux — sans engagement", "grey", 70, {"minutes": None}),
    ],
    "RPO": [
        ("0", "Aucune perte — réplication synchrone", "red", 10, {"minutes": 0}),
        ("15m", "15 minutes", "red", 20, {"minutes": 15}),
        ("1h", "1 heure", "orange", 30, {"minutes": 60}),
        ("4h", "4 heures", "orange", 40, {"minutes": 240}),
        ("24h", "24 heures", "blue", 50, {"minutes": 1440}),
        ("best-effort", "Au mieux — sans engagement", "grey", 60, {"minutes": None}),
    ],
    "ServiceHours": [
        ("24-7", "24h/24, 7j/7", "red", 10,
         {"includes_weekend": True, "includes_oncall": True}),
        ("7h-20h", "Étendues (7h-20h)", "orange", 20, {}),
        ("8h-18h", "Heures ouvrées (8h-18h)", "blue", 30, {}),
        ("8h-18h-astreinte", "Heures ouvrées + astreinte", "purple", 40,
         {"includes_oncall": True}),
    ],
    "DataClassification": [
        ("public", "Public", "green", 10, {"level": 0}),
        ("interne", "Interne", "blue", 20, {"level": 1}),
        ("confidentiel", "Confidentiel", "orange", 30,
         {"level": 2, "requires_encryption": True}),
        ("restreint", "Restreint — diffusion nominative", "red", 40,
         {"level": 3, "requires_encryption": True}),
    ],
    "AuthenticationMethod": [
        ("keycloak", "Keycloak", "purple", 10, {"is_centralized": True}),
        ("oidc", "OpenID Connect (autre)", "blue", 20, {"is_centralized": True}),
        ("saml", "SAML 2.0", "blue", 30, {"is_centralized": True}),
        ("ldap", "LDAP", "cyan", 40, {"is_centralized": True}),
        ("active-directory", "Active Directory", "cyan", 50, {"is_centralized": True}),
        # Le drapeau remplace la convention : ce n'est plus le NOM « locale »
        # qui signale des comptes hors révocation centralisée, c'est l'attribut.
        ("locale", "Locale — comptes propres à l'application", "orange", 60,
         {"is_centralized": False}),
        ("aucune", "Aucune — accès anonyme", "red", 70, {"is_centralized": False}),
    ],
    "Environment": [
        ("production", "Production", "red", 10, {"is_production": True}),
        ("preproduction", "Préproduction", "orange", 20, {}),
        ("recette", "Recette", "blue", 30, {}),
        ("developpement", "Développement", "green", 40, {}),
    ],
    "DeploymentStatus": [
        ("actif", "Actif", "green", 10, {"is_active": True}),
        ("planifie", "Planifié", "blue", 20, {}),
        ("en-demantelement", "En démantèlement", "orange", 30, {}),
        ("hors-ligne", "Hors ligne", "grey", 40, {}),
    ],
    "MaintenanceWindow": [
        ("a-tout-moment", "À tout moment", "green", 10, {"allows_interruption": True}),
        ("hors-heures-ouvrees", "Hors heures ouvrées (20h-6h)", "blue", 20,
         {"allows_interruption": True}),
        ("week-end", "Week-end", "blue", 30, {"allows_interruption": True}),
        ("nuit-dimanche", "Nuit du dimanche (0h-4h)", "orange", 40,
         {"allows_interruption": True}),
        ("aucune-24-7", "Aucune — service 24/7", "red", 50, {"allows_interruption": False}),
        ("a-definir", "À définir", "grey", 60, {"allows_interruption": True}),
    ],
}

# (modèle, ancien champ texte, nouveau champ, référentiel visé)
TRANSFERTS = [
    ("Application", "lifecycle_status", "lifecycle_status_ref", "LifecycleStatus"),
    ("Application", "criticality", "criticality_ref", "Criticality"),
    ("Application", "rto", "rto_ref", "RTO"),
    ("Application", "rpo", "rpo_ref", "RPO"),
    ("Application", "service_hours", "service_hours_ref", "ServiceHours"),
    ("Application", "data_classification", "data_classification_ref", "DataClassification"),
    ("Application", "authentication", "authentication_ref", "AuthenticationMethod"),
    ("Deployment", "environment", "environment_ref", "Environment"),
    ("Deployment", "status", "status_ref", "DeploymentStatus"),
    ("Deployment", "maintenance_window", "maintenance_window_ref", "MaintenanceWindow"),
]


def peupler(apps, schema_editor):
    objets = {}
    for nom_modele, valeurs in REFERENTIELS.items():
        modele = apps.get_model("netbox_applications", nom_modele)
        objets[nom_modele] = {}
        for valeur, libelle, couleur, rang, extra in valeurs:
            obj, _ = modele.objects.get_or_create(
                slug=slugify(valeur) or valeur,
                defaults={"name": libelle, "color": couleur, "weight": rang, **extra},
            )
            objets[nom_modele][valeur] = obj

    for nom_modele, ancien, nouveau, referentiel in TRANSFERTS:
        modele = apps.get_model("netbox_applications", nom_modele)
        ref_modele = apps.get_model("netbox_applications", referentiel)
        for fiche in modele.objects.all():
            valeur = getattr(fiche, ancien, None)
            if not valeur:
                continue
            obj = objets[referentiel].get(valeur)
            if obj is None:
                # Valeur inconnue du plugin — ajoutée par FIELD_CHOICES, par
                # exemple. On la crée plutôt que de la perdre en silence.
                obj, _ = ref_modele.objects.get_or_create(
                    slug=slugify(valeur) or valeur,
                    defaults={"name": valeur, "weight": 900},
                )
                objets[referentiel][valeur] = obj
            setattr(fiche, nouveau, obj)
            fiche.save(update_fields=[nouveau])


def depeupler(apps, schema_editor):
    """Retour en arrière : on vide les clés étrangères, on garde les référentiels.

    Les supprimer effacerait des valeurs que l'opérateur a pu ajouter lui-même
    depuis l'interface.
    """
    for nom_modele, _ancien, nouveau, _ref in TRANSFERTS:
        modele = apps.get_model("netbox_applications", nom_modele)
        modele.objects.update(**{nouveau: None})


class Migration(migrations.Migration):
    dependencies = [("netbox_applications", "0003_referentiels")]

    operations = [migrations.RunPython(peupler, depeupler)]
