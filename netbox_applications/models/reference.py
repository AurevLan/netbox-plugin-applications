"""Référentiels — les listes de valeurs, gérées DANS l'interface NetBox.

POURQUOI DES OBJETS ET NON DES LISTES DE CHOIX FIGÉES.

Une liste définie en Python ne s'enrichit qu'en modifiant le code, ou au mieux
la configuration du serveur suivie d'un redémarrage. Ajouter « CAS » devenait
une opération de développement, pas d'exploitation.

Ces objets ont chacun leur page, leur bouton « Ajouter », et leur suppression
protégée si la valeur est employée par une fiche.

CHACUN PORTE PLUS QU'UN LIBELLÉ. Un attribut bien choisi transforme une
convention tacite en donnée interrogeable : savoir qu'une authentification
n'est PAS centralisée vaut mieux que de se souvenir que la valeur « locale »
signifiait cela.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# ColorChoices vit dans « netbox.choices », pas dans « utilities.choices » —
# où l'on trouve en revanche ChoiceSet. Les deux modules se ressemblent.
from netbox.choices import ColorChoices
from netbox.models import OrganizationalModel
from utilities.fields import ColorField


class ReferenceModel(OrganizationalModel):
    """Base commune : un nom, une couleur, un rang d'affichage.

    OrganizationalModel apporte déjà nom, slug, description, commentaires,
    étiquettes, champs personnalisés et journal de modifications.
    """

    color = ColorField(default=ColorChoices.COLOR_GREY, verbose_name="Couleur")

    # Le rang remplace l'ordre figé en Python. Une liste triée alphabétiquement
    # obligerait à lire chaque libellé pour se situer ; ici l'ordre suit la
    # gradation naturelle du critère, et reste modifiable dans l'interface.
    weight = models.PositiveSmallIntegerField(
        default=100,
        verbose_name="Rang",
        help_text="Ordre d'affichage. Les valeurs les plus faibles apparaissent en premier.",
    )

    class Meta:
        abstract = True
        ordering = ("weight", "name")

    def __str__(self):
        return self.name


class AuthenticationMethod(ReferenceModel):
    """Système d'authentification d'une application."""

    # L'attribut qui compte. Il répond à « quelles applications ont des comptes
    # échappant à la révocation centralisée ? » — la question qu'on se pose le
    # jour où quelqu'un quitte l'organisation.
    is_centralized = models.BooleanField(
        default=True,
        verbose_name="Centralisée",
        help_text=(
            "Les comptes sont-ils gérés par un annuaire central ? "
            "Décocher pour une base de comptes propre à l'application : "
            "ces comptes échappent à la révocation centralisée."
        ),
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "méthode d'authentification"
        verbose_name_plural = "méthodes d'authentification"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:authenticationmethod", args=[self.pk])


class MaintenanceWindow(ReferenceModel):
    """Créneau pendant lequel une interruption de service est admise."""

    start_time = models.TimeField(null=True, blank=True, verbose_name="Début")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Fin")

    # Distingue « aucune fenêtre définie » de « aucune interruption admise ».
    # Les deux s'affichaient auparavant comme des libellés qu'il fallait
    # interpréter ; c'est désormais une donnée.
    allows_interruption = models.BooleanField(
        default=True,
        verbose_name="Interruption admise",
        help_text="Décocher pour un service qui ne tolère aucune interruption.",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "plage de maintenance"
        verbose_name_plural = "plages de maintenance"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:maintenancewindow", args=[self.pk])


class Criticality(ReferenceModel):
    """Criticité métier d'une application."""

    incident_priority = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Priorité d'incident",
        help_text="Priorité à appliquer en cas d'incident, par exemple P1.",
    )
    requires_oncall = models.BooleanField(
        default=False,
        verbose_name="Astreinte",
        help_text="Un incident déclenche-t-il l'astreinte ?",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "criticité"
        verbose_name_plural = "criticités"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:criticality", args=[self.pk])


class RecoveryObjective(ReferenceModel):
    """Base des objectifs de reprise, exprimés EN MINUTES.

    La durée en minutes n'est pas un doublon du libellé : elle rend les
    objectifs COMPARABLES. « 4 heures » et « 24 heures » ne se trient pas
    comme des chaînes, et l'on ne peut pas demander « toutes les applications
    dont le RPO est inférieur à 2 heures » sans elle.
    """

    minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Durée (minutes)",
        help_text="Laisser vide pour un engagement « au mieux », sans durée garantie.",
    )

    class Meta(ReferenceModel.Meta):
        abstract = True


class RTO(RecoveryObjective):
    """Durée maximale d'interruption admise."""

    class Meta(RecoveryObjective.Meta):
        abstract = False
        verbose_name = "RTO"
        verbose_name_plural = "RTO"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:rto", args=[self.pk])


class RPO(RecoveryObjective):
    """Perte de données admise.

    Conditionne directement la FRÉQUENCE DES SAUVEGARDES : un RPO de 60 minutes
    interdit une sauvegarde quotidienne. C'est pour cela que la durée doit être
    exploitable par un script, et pas seulement lisible.
    """

    class Meta(RecoveryObjective.Meta):
        abstract = False
        verbose_name = "RPO"
        verbose_name_plural = "RPO"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:rpo", args=[self.pk])


class ServiceHours(ReferenceModel):
    """Plage pendant laquelle le service est supporté.

    À ne pas confondre avec la plage de maintenance : celle-ci dit quand on
    peut INTERROMPRE, celle-là quand on doit RÉPONDRE.
    """

    start_time = models.TimeField(null=True, blank=True, verbose_name="Début")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Fin")
    includes_weekend = models.BooleanField(default=False, verbose_name="Week-end inclus")
    includes_oncall = models.BooleanField(
        default=False,
        verbose_name="Astreinte",
        help_text="Une astreinte prend-elle le relais hors de cette plage ?",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "horaires de service"
        verbose_name_plural = "horaires de service"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:servicehours", args=[self.pk])


class DataClassification(ReferenceModel):
    """Classification des données traitées."""

    # Un niveau numérique permet de comparer : « au moins confidentiel »
    # devient une requête, au lieu d'une énumération à maintenir.
    level = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Niveau",
        help_text="0 = public. Plus la valeur est élevée, plus la donnée est sensible.",
    )
    requires_encryption = models.BooleanField(
        default=False,
        verbose_name="Chiffrement exigé",
        help_text="Le chiffrement au repos est-il obligatoire à ce niveau ?",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "classification"
        verbose_name_plural = "classifications"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:dataclassification", args=[self.pk])


class LifecycleStatus(ReferenceModel):
    """Étape du cycle de vie d'un service."""

    # Répond à « quelles applications sont réellement en service ? » sans
    # supposer que l'étape s'appelle « en-service ».
    is_operational = models.BooleanField(
        default=False,
        verbose_name="En service",
        help_text="Cette étape correspond-elle à une application réellement en service ?",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "statut de service"
        verbose_name_plural = "statuts de service"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:lifecyclestatus", args=[self.pk])


class Environment(ReferenceModel):
    """Environnement de déploiement."""

    is_production = models.BooleanField(
        default=False,
        verbose_name="Production",
        help_text="Un environnement de production justifie des règles plus strictes.",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "environnement"
        verbose_name_plural = "environnements"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:environment", args=[self.pk])


class DeploymentStatus(ReferenceModel):
    """Statut d'un déploiement."""

    is_active = models.BooleanField(
        default=False,
        verbose_name="Actif",
        help_text="Ce statut correspond-il à un déploiement en fonctionnement ?",
    )

    class Meta(ReferenceModel.Meta):
        abstract = False
        verbose_name = "statut de déploiement"
        verbose_name_plural = "statuts de déploiement"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("plugins:netbox_applications:deploymentstatus", args=[self.pk])
