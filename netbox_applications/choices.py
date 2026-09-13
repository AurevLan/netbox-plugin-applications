"""Listes déroulantes de la fiche applicative.

CHAQUE LISTE DÉCLARE UNE CLÉ, et ce n'est pas décoratif : c'est ce qui permet
d'ajouter ou de remplacer des choix PAR CONFIGURATION, sans modifier le code
du plugin ni attendre une nouvelle version.

Dans la configuration de NetBox :

    FIELD_CHOICES = {
        # Ajouter aux choix existants — noter le « + » final
        "netbox_applications.Application.authentication+": [
            ("cas", "CAS", "cyan"),
            ("kerberos", "Kerberos", "purple"),
        ],
        # Remplacer entièrement la liste — sans le « + »
        "netbox_applications.Deployment.maintenance_window": [
            ("mardi-soir", "Mardi soir", "blue"),
        ],
    }

Le préfixe « netbox_applications » est le nom du module du plugin ; NetBox le
déduit lui-même. Un redémarrage suffit, aucune migration n'est nécessaire —
les choix ne sont pas contraints en base.

Définies en Python plutôt qu'en jeux de choix NetBox : elles font partie du
modèle et doivent évoluer avec le code du plugin, pas par configuration.

L'ordre de chaque liste est délibéré et suit la gradation naturelle du critère
(du plus contraignant au moins contraignant, ou l'inverse selon le sens usuel) :
une liste triée alphabétiquement obligerait à lire chaque libellé pour se situer.
"""

from utilities.choices import ChoiceSet

# --- Cycle de vie et criticité (ITIL) ---------------------------------------


class LifecycleChoices(ChoiceSet):
    """Étapes du cycle de vie d'un service, au sens ITIL."""

    key = "Application.lifecycle_status"

    PLANNED = "en-projet"
    ACTIVE = "en-service"
    DEPRECATING = "en-retrait"
    RETIRED = "retire"

    CHOICES = [
        (PLANNED, "En projet", "blue"),
        (ACTIVE, "En service", "green"),
        (DEPRECATING, "En cours de retrait", "orange"),
        (RETIRED, "Retiré", "gray"),
    ]


class CriticalityChoices(ChoiceSet):
    """Criticité métier.

    Détermine la sévérité de supervision et la priorité d'incident.
    """

    key = "Application.criticality"

    CRITICAL = "critique"
    MAJOR = "majeure"
    STANDARD = "standard"
    MINOR = "mineure"

    CHOICES = [
        (CRITICAL, "Critique — arrêt d'activité", "red"),
        (MAJOR, "Majeure — activité dégradée", "orange"),
        (STANDARD, "Standard", "blue"),
        (MINOR, "Mineure — sans impact métier", "green"),
    ]


# --- Continuité de service ---------------------------------------------------


class RTOChoices(ChoiceSet):
    """Durée maximale d'interruption admise (Recovery Time Objective)."""

    key = "Application.rto"

    RTO_15M = "15m"
    RTO_1H = "1h"
    RTO_4H = "4h"
    RTO_8H = "8h"
    RTO_24H = "24h"
    RTO_72H = "72h"
    RTO_BEST_EFFORT = "best-effort"

    CHOICES = [
        (RTO_15M, "15 minutes", "red"),
        (RTO_1H, "1 heure", "red"),
        (RTO_4H, "4 heures", "orange"),
        (RTO_8H, "8 heures", "orange"),
        (RTO_24H, "24 heures", "blue"),
        (RTO_72H, "72 heures", "blue"),
        (RTO_BEST_EFFORT, "Au mieux — sans engagement", "gray"),
    ]


class RPOChoices(ChoiceSet):
    """Perte de données admise (Recovery Point Objective).

    Le RPO conditionne la fréquence des sauvegardes : un RPO de 1 heure
    impose une sauvegarde horaire, pas quotidienne.
    """

    key = "Application.rpo"

    RPO_ZERO = "0"
    RPO_15M = "15m"
    RPO_1H = "1h"
    RPO_4H = "4h"
    RPO_24H = "24h"
    RPO_BEST_EFFORT = "best-effort"

    CHOICES = [
        (RPO_ZERO, "Aucune perte — réplication synchrone", "red"),
        (RPO_15M, "15 minutes", "red"),
        (RPO_1H, "1 heure", "orange"),
        (RPO_4H, "4 heures", "orange"),
        (RPO_24H, "24 heures", "blue"),
        (RPO_BEST_EFFORT, "Au mieux — sans engagement", "gray"),
    ]


class ServiceHoursChoices(ChoiceSet):
    """Plage pendant laquelle le service est supporté.

    À ne pas confondre avec la plage de MAINTENANCE, qui dit quand on peut
    interrompre. Les horaires de service disent quand on doit répondre.
    """

    key = "Application.service_hours"

    H24_7 = "24-7"
    EXTENDED = "7h-20h"
    OFFICE = "8h-18h"
    OFFICE_ONCALL = "8h-18h-astreinte"

    CHOICES = [
        (H24_7, "24h/24, 7j/7", "red"),
        (EXTENDED, "Étendues (7h-20h)", "orange"),
        (OFFICE, "Heures ouvrées (8h-18h)", "blue"),
        (OFFICE_ONCALL, "Heures ouvrées + astreinte", "purple"),
    ]


# --- Sécurité et conformité --------------------------------------------------


class DataClassificationChoices(ChoiceSet):
    """Classification des données traitées.

    Combinée à « diffusé à l'externe » du déploiement, elle détermine le
    niveau d'exigence des règles pare-feu.
    """

    key = "Application.data_classification"

    PUBLIC = "public"
    INTERNAL = "interne"
    CONFIDENTIAL = "confidentiel"
    RESTRICTED = "restreint"

    CHOICES = [
        (PUBLIC, "Public", "green"),
        (INTERNAL, "Interne", "blue"),
        (CONFIDENTIAL, "Confidentiel", "orange"),
        (RESTRICTED, "Restreint — diffusion nominative", "red"),
    ]


class AuthenticationChoices(ChoiceSet):
    """Système d'authentification de l'application.

    « Locale » signale une base de comptes propre à l'application : c'est le
    cas à surveiller, puisqu'il échappe à la révocation centralisée.
    """

    key = "Application.authentication"

    KEYCLOAK = "keycloak"
    OIDC = "oidc"
    SAML = "saml"
    LDAP = "ldap"
    ACTIVE_DIRECTORY = "active-directory"
    LOCAL = "locale"
    NONE = "aucune"

    CHOICES = [
        (KEYCLOAK, "Keycloak", "purple"),
        (OIDC, "OpenID Connect (autre)", "blue"),
        (SAML, "SAML 2.0", "blue"),
        (LDAP, "LDAP", "cyan"),
        (ACTIVE_DIRECTORY, "Active Directory", "cyan"),
        (LOCAL, "Locale — comptes propres à l'application", "orange"),
        (NONE, "Aucune — accès anonyme", "red"),
    ]


# --- Déploiement -------------------------------------------------------------


class EnvironmentChoices(ChoiceSet):
    key = "Deployment.environment"

    PRODUCTION = "production"
    PREPRODUCTION = "preproduction"
    RECETTE = "recette"
    DEVELOPPEMENT = "developpement"

    CHOICES = [
        (PRODUCTION, "Production", "red"),
        (PREPRODUCTION, "Préproduction", "orange"),
        (RECETTE, "Recette", "blue"),
        (DEVELOPPEMENT, "Développement", "green"),
    ]


class MaintenanceWindowChoices(ChoiceSet):
    """Créneaux pendant lesquels une interruption est admise."""

    key = "Deployment.maintenance_window"

    OFF_HOURS = "hors-heures-ouvrees"
    WEEKEND = "week-end"
    SUNDAY_NIGHT = "nuit-dimanche"
    ANYTIME = "a-tout-moment"
    NONE_24_7 = "aucune-24-7"
    UNDEFINED = "a-definir"

    CHOICES = [
        (ANYTIME, "À tout moment", "green"),
        (OFF_HOURS, "Hors heures ouvrées (20h-6h)", "blue"),
        (WEEKEND, "Week-end", "blue"),
        (SUNDAY_NIGHT, "Nuit du dimanche (0h-4h)", "orange"),
        (NONE_24_7, "Aucune — service 24/7", "red"),
        (UNDEFINED, "À définir", "gray"),
    ]


class DeploymentStatusChoices(ChoiceSet):
    key = "Deployment.status"

    ACTIVE = "actif"
    PLANNED = "planifie"
    DECOMMISSIONING = "en-demantelement"
    OFFLINE = "hors-ligne"

    CHOICES = [
        (ACTIVE, "Actif", "green"),
        (PLANNED, "Planifié", "blue"),
        (DECOMMISSIONING, "En démantèlement", "orange"),
        (OFFLINE, "Hors ligne", "gray"),
    ]
