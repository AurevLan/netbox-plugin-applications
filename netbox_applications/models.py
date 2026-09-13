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

from .choices import (
    AuthenticationChoices,
    CriticalityChoices,
    DataClassificationChoices,
    DeploymentStatusChoices,
    EnvironmentChoices,
    LifecycleChoices,
    MaintenanceWindowChoices,
    RPOChoices,
    RTOChoices,
    ServiceHoursChoices,
)


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
    lifecycle_status = models.CharField(
        max_length=30,
        choices=LifecycleChoices,
        default=LifecycleChoices.PLANNED,
        verbose_name="Statut du service",
    )
    criticality = models.CharField(
        max_length=30,
        choices=CriticalityChoices,
        default=CriticalityChoices.STANDARD,
        verbose_name="Criticité métier",
        help_text="Détermine la sévérité de supervision et la priorité d'incident.",
    )

    # --- Continuité de service ---
    rto = models.CharField(
        max_length=20,
        choices=RTOChoices,
        blank=True,
        verbose_name="RTO",
        help_text="Durée maximale d'interruption admise.",
    )
    rpo = models.CharField(
        max_length=20,
        choices=RPOChoices,
        blank=True,
        verbose_name="RPO",
        help_text="Perte de données admise. Conditionne la fréquence des sauvegardes.",
    )
    service_hours = models.CharField(
        max_length=30,
        choices=ServiceHoursChoices,
        blank=True,
        verbose_name="Horaires de service",
        help_text="Quand le service doit être supporté — à ne pas confondre avec la plage de maintenance.",
    )

    # --- Sécurité et conformité ---
    data_classification = models.CharField(
        max_length=30,
        choices=DataClassificationChoices,
        default=DataClassificationChoices.INTERNAL,
        verbose_name="Classification des données",
    )
    personal_data = models.BooleanField(
        default=False,
        verbose_name="Données personnelles (RGPD)",
        help_text="L'application traite-t-elle des données à caractère personnel ?",
    )
    authentication = models.CharField(
        max_length=30,
        choices=AuthenticationChoices,
        blank=True,
        verbose_name="Authentification",
        help_text="« Locale » signale des comptes échappant à la révocation centralisée.",
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

    # Couleurs des badges, lues par le gabarit.
    def get_lifecycle_status_color(self):
        return LifecycleChoices.colors.get(self.lifecycle_status)

    def get_criticality_color(self):
        return CriticalityChoices.colors.get(self.criticality)

    def get_data_classification_color(self):
        return DataClassificationChoices.colors.get(self.data_classification)

    def get_authentication_color(self):
        return AuthenticationChoices.colors.get(self.authentication)

    def get_rto_color(self):
        return RTOChoices.colors.get(self.rto)

    def get_rpo_color(self):
        return RPOChoices.colors.get(self.rpo)

    def get_service_hours_color(self):
        return ServiceHoursChoices.colors.get(self.service_hours)


class Deployment(NetBoxModel):
    """Instance d'une application dans un environnement donné."""

    application = models.ForeignKey(
        to=Application,
        on_delete=models.CASCADE,
        related_name="deployments",
        verbose_name="Application",
    )
    environment = models.CharField(
        max_length=30,
        choices=EnvironmentChoices,
        verbose_name="Environnement",
    )
    status = models.CharField(
        max_length=30,
        choices=DeploymentStatusChoices,
        default=DeploymentStatusChoices.ACTIVE,
        verbose_name="Statut",
    )

    maintenance_window = models.CharField(
        max_length=30,
        choices=MaintenanceWindowChoices,
        default=MaintenanceWindowChoices.UNDEFINED,
        verbose_name="Plage de maintenance",
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
        return f"{self.application.name} — {self.get_environment_display()}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_applications:deployment", args=[self.pk])

    def clean(self):
        super().clean()
        # Un déploiement exposé à l'externe portant des données restreintes
        # n'est pas interdit, mais mérite d'être posé consciemment.
        if self.external_facing and self.application_id:
            classification = self.application.data_classification
            if classification == "restreint":
                raise ValidationError(
                    {
                        "external_facing": (
                            "L'application traite des données en diffusion restreinte. "
                            "Une exposition externe doit être validée : abaisser la "
                            "classification ou retirer l'exposition."
                        )
                    }
                )

    def get_environment_color(self):
        return EnvironmentChoices.colors.get(self.environment)

    def get_status_color(self):
        return DeploymentStatusChoices.colors.get(self.status)

    def get_maintenance_window_color(self):
        return MaintenanceWindowChoices.colors.get(self.maintenance_window)
