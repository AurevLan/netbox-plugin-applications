"""Modèles de la fiche applicative.

DEUX objets, et c'est délibéré :

  Application   — ce qui est vrai quel que soit l'environnement : identité,
                  client, criticité, engagements de continuité, sécurité.
  Deployment    — une instance de l'application dans UN environnement :
                  ses VM, sa plage de maintenance, son exposition, son URL.

Mettre les VM ou la plage de maintenance sur l'Application supposerait que la
production et la recette partagent les mêmes — ce qui est faux dans la plupart
des cas, et d'autant plus dangereux que l'erreur ne se voit qu'en incident.
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

# Seuil au-delà duquel une donnée ne se diffuse pas librement. Exprimé en
# niveau et non en nom : renommer « Restreint » ne doit pas désarmer le
# garde-fou.
NIVEAU_RESTREINT = 3


class Application(NetBoxModel):
    """Fiche applicative — le service, indépendamment de ses déploiements."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de l'application")

    application_id = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        verbose_name="Identifiant",
        help_text="Attribué automatiquement à la création, au format APP-0000.",
        validators=[RegexValidator(r"^APP-\d{4,}$")],
    )

    client = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Client",
        null=True,
        blank=True,
    )

    # --- Cycle de vie et criticité (ITIL) ---
    lifecycle_status = models.ForeignKey(
        to="netbox_applications.LifecycleStatus",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Cycle de vie du service",
        null=True,
        blank=True,
    )
    criticality = models.ForeignKey(
        to="netbox_applications.Criticality",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Criticité métier",
        null=True,
        blank=True,
        help_text="Détermine la sévérité de supervision et la priorité d'incident.",
    )

    # --- Continuité de service ---
    rto = models.ForeignKey(
        to="netbox_applications.RTO",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="RTO",
        null=True,
        blank=True,
        help_text="Durée maximale d'interruption admise.",
    )
    rpo = models.ForeignKey(
        to="netbox_applications.RPO",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="RPO",
        null=True,
        blank=True,
        help_text="Perte de données admise. Conditionne la fréquence des sauvegardes.",
    )
    service_hours = models.ForeignKey(
        to="netbox_applications.ServiceHours",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Horaires de service",
        null=True,
        blank=True,
        help_text="Quand le service doit être supporté — à ne pas confondre avec la plage de maintenance.",
    )

    # --- Sécurité et conformité ---
    data_classification = models.ForeignKey(
        to="netbox_applications.DataClassification",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Classification des données",
        null=True,
        blank=True,
    )
    personal_data = models.BooleanField(
        default=False,
        verbose_name="Données personnelles (RGPD)",
        help_text="L'application traite-t-elle des données à caractère personnel ?",
    )
    authentication = models.ForeignKey(
        to="netbox_applications.AuthenticationMethod",
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Authentification",
        null=True,
        blank=True,
        help_text="Une méthode non centralisée signale des comptes échappant à la révocation.",
    )

    # --- Référents ---
    technical_contact = models.ForeignKey(
        to="tenancy.Contact",
        on_delete=models.SET_NULL,
        related_name="applications_technical",
        verbose_name="Référent technique",
        null=True,
        blank=True,
    )
    project_manager = models.ForeignKey(
        to="tenancy.Contact",
        on_delete=models.SET_NULL,
        related_name="applications_project",
        verbose_name="Référent chef de projet",
        null=True,
        blank=True,
    )

    # Champ LIBRE, à la différence des deux référents ci-dessus : le contact
    # métier est souvent quelqu'un qui ne figure pas dans l'annuaire de contacts
    # de NetBox — un responsable de service, une liste de diffusion. Exiger sa
    # création préalable ferait laisser le champ vide, ce qui est pire.
    #
    # Libre ne veut pas dire quelconque : EmailField IMPOSE le format. Une
    # adresse est ce dont on a besoin en incident, et c'est vérifiable — à la
    # différence d'un nom, qu'on ne peut ni valider ni utiliser pour joindre
    # quelqu'un.
    business_contact = models.EmailField(
        blank=True,
        verbose_name="Contact métier",
        help_text="Adresse de courriel du responsable métier, ou de sa liste de diffusion.",
    )

    documentation_url = models.URLField(blank=True, verbose_name="Documentation")
    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
    comments = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        ordering = ("application_id", "name")
        verbose_name = "application"
        verbose_name_plural = "applications"

    def __str__(self):
        return f"{self.application_id or '(sans id)'} — {self.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_applications:application", args=[self.pk])

    def clean(self):
        super().clean()
        # Le contrôle vaut DANS LES DEUX SENS. Sans celui-ci, il suffirait de
        # retirer le service pour créer la contradiction que l'autre refuse :
        # le garde-fou se contournerait par l'autre bout.
        if self.pk and self.lifecycle_status and not self.lifecycle_status.is_operational:
            vivantes = self.deployments.filter(status__is_active=True, environment__is_production=True)
            if vivantes.exists():
                noms = ", ".join(str(d.environment) for d in vivantes)
                raise ValidationError(
                    {
                        "lifecycle_status": (
                            f"À l'étape « {self.lifecycle_status} », le service n'est pas "
                            f"rendu, mais des instances de production sont encore en "
                            f"fonctionnement ({noms}). Les arrêter d'abord."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        """Attribue l'identifiant lisible à la première sauvegarde.

        Il ne peut pas l'être avant : la clé primaire n'existe qu'une fois la
        ligne écrite. On sauvegarde donc, puis on complète.
        """
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.application_id:
            self.application_id = f"APP-{self.pk:04d}"
            super().save(update_fields=["application_id"])


class Deployment(NetBoxModel):
    """Instance d'une application dans un environnement donné."""

    application = models.ForeignKey(
        to=Application,
        on_delete=models.CASCADE,
        related_name="deployments",
        verbose_name="Application",
    )
    environment = models.ForeignKey(
        to="netbox_applications.Environment",
        on_delete=models.PROTECT,
        related_name="deployments",
        verbose_name="Environnement",
    )
    status = models.ForeignKey(
        to="netbox_applications.DeploymentStatus",
        on_delete=models.PROTECT,
        related_name="deployments",
        verbose_name="État de l'instance",
        null=True,
        blank=True,
    )

    maintenance_window = models.ForeignKey(
        to="netbox_applications.MaintenanceWindow",
        on_delete=models.PROTECT,
        related_name="deployments",
        verbose_name="Plage de maintenance",
        null=True,
        blank=True,
        help_text="Quand une interruption est admise SUR CET ENVIRONNEMENT.",
    )
    external_facing = models.BooleanField(
        default=False,
        verbose_name="Diffusé à l'externe",
        help_text="Accessible hors du réseau interne. Détermine l'ouverture de flux pare-feu.",
    )
    # Nommé « access_url » et non « url » : NetBox expose un champ « url »
    # hypermedia sur chaque objet. Un champ de modèle portant le même nom
    # obligeait à un contournement dans le sérialiseur.
    access_url = models.URLField(blank=True, verbose_name="URL d'accès")

    virtual_machines = models.ManyToManyField(
        to="virtualization.VirtualMachine",
        related_name="deployments",
        blank=True,
        verbose_name="VM",
    )

    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
    comments = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        ordering = ("application", "environment")
        verbose_name = "déploiement"
        verbose_name_plural = "déploiements"
        # Une application n'a qu'UN déploiement par environnement. Sans cette
        # contrainte, deux fiches « production » divergeraient en silence.
        constraints = [
            models.UniqueConstraint(
                fields=("application", "environment"),
                name="unique_application_environment",
                violation_error_message="Cette application a déjà un déploiement dans cet environnement.",
            )
        ]

    def __str__(self):
        return f"{self.application.name} — {self.environment}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_applications:deployment", args=[self.pk])

    def clean(self):
        super().clean()
        # Un déploiement exposé à l'externe portant des données restreintes
        # n'est pas interdit, mais mérite d'être posé consciemment.
        if self.external_facing and self.application_id:
            classification = self.application.data_classification
            # Comparaison sur le NIVEAU, pas sur le nom : depuis que la
            # classification est un objet, « == "restreint" » était toujours
            # faux et ce garde-fou ne protégeait plus rien.
            if classification is not None and classification.level >= NIVEAU_RESTREINT:
                raise ValidationError(
                    {
                        "external_facing": (
                            "L'application traite des données en diffusion restreinte. "
                            "Une exposition externe doit être validée : abaisser la "
                            "classification ou retirer l'exposition."
                        )
                    }
                )

        # Cohérence entre les DEUX niveaux. Un service que l'organisation
        # déclare ne plus rendre ne peut pas garder une instance en
        # fonctionnement en production : c'est exactement le genre de
        # contradiction qui ne se voit qu'au moment de l'incident.
        if self.application_id and self.status and self.environment_id:
            etape = self.application.lifecycle_status
            if (
                self.status.is_active
                and self.environment.is_production
                and etape is not None
                and not etape.is_operational
            ):
                raise ValidationError(
                    {
                        "status": (
                            f"L'application est à l'étape « {etape} », où le service n'est "
                            f"pas rendu, alors que cette instance de production serait en "
                            f"fonctionnement. Faire avancer le cycle de vie de "
                            f"l'application, ou arrêter cette instance."
                        )
                    }
                )
