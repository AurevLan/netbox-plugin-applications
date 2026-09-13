import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from .models import (
    RPO,
    RTO,
    Application,
    AuthenticationMethod,
    Criticality,
    DataClassification,
    Deployment,
    DeploymentStatus,
    Environment,
    LifecycleStatus,
    MaintenanceWindow,
    ServiceHours,
)

# --- Référentiels --------------------------------------------------------------


class ReferenceTable(NetBoxTable):
    """Colonnes communes à tous les référentiels.

    Une classe de base plutôt que dix tables recopiées : ce qui vaut pour
    l'une vaut pour les dix, et une correction se fait à un seul endroit.
    """

    name = tables.Column(linkify=True, verbose_name="Nom")
    color = columns.ColorColumn(verbose_name="Couleur")
    weight = tables.Column(verbose_name="Rang")
    tags = columns.TagColumn()

    class Meta(NetBoxTable.Meta):
        fields = ("pk", "id", "name", "slug", "description", "color", "weight", "tags")
        default_columns = ("name", "description", "color", "weight")


class AuthenticationMethodTable(ReferenceTable):
    is_centralized = columns.BooleanColumn(verbose_name="Centralisée")

    class Meta(ReferenceTable.Meta):
        model = AuthenticationMethod
        fields = (*ReferenceTable.Meta.fields, "is_centralized")
        default_columns = ("name", "is_centralized", "description", "color")


class MaintenanceWindowTable(ReferenceTable):
    start_time = tables.Column(verbose_name="Début")
    end_time = tables.Column(verbose_name="Fin")
    allows_interruption = columns.BooleanColumn(verbose_name="Interruption admise")

    class Meta(ReferenceTable.Meta):
        model = MaintenanceWindow
        fields = (*ReferenceTable.Meta.fields, "start_time", "end_time", "allows_interruption")
        default_columns = ("name", "start_time", "end_time", "allows_interruption", "color")


class CriticalityTable(ReferenceTable):
    incident_priority = tables.Column(verbose_name="Priorité d'incident")
    requires_oncall = columns.BooleanColumn(verbose_name="Astreinte")

    class Meta(ReferenceTable.Meta):
        model = Criticality
        fields = (*ReferenceTable.Meta.fields, "incident_priority", "requires_oncall")
        default_columns = ("name", "incident_priority", "requires_oncall", "color", "weight")


class RecoveryObjectiveTable(ReferenceTable):
    """Base des tables RTO et RPO — mêmes colonnes, deux modèles."""

    minutes = tables.Column(verbose_name="Durée (min)")

    class Meta(ReferenceTable.Meta):
        fields = (*ReferenceTable.Meta.fields, "minutes")
        default_columns = ("name", "minutes", "description", "color")


class RTOTable(RecoveryObjectiveTable):
    class Meta(RecoveryObjectiveTable.Meta):
        model = RTO


class RPOTable(RecoveryObjectiveTable):
    class Meta(RecoveryObjectiveTable.Meta):
        model = RPO


class ServiceHoursTable(ReferenceTable):
    start_time = tables.Column(verbose_name="Début")
    end_time = tables.Column(verbose_name="Fin")
    includes_weekend = columns.BooleanColumn(verbose_name="Week-end")
    includes_oncall = columns.BooleanColumn(verbose_name="Astreinte")

    class Meta(ReferenceTable.Meta):
        model = ServiceHours
        fields = (
            *ReferenceTable.Meta.fields,
            "start_time",
            "end_time",
            "includes_weekend",
            "includes_oncall",
        )
        default_columns = ("name", "start_time", "end_time", "includes_weekend", "includes_oncall")


class DataClassificationTable(ReferenceTable):
    level = tables.Column(verbose_name="Niveau")
    requires_encryption = columns.BooleanColumn(verbose_name="Chiffrement exigé")

    class Meta(ReferenceTable.Meta):
        model = DataClassification
        fields = (*ReferenceTable.Meta.fields, "level", "requires_encryption")
        default_columns = ("name", "level", "requires_encryption", "color")


class LifecycleStatusTable(ReferenceTable):
    is_operational = columns.BooleanColumn(verbose_name="En service")

    class Meta(ReferenceTable.Meta):
        model = LifecycleStatus
        fields = (*ReferenceTable.Meta.fields, "is_operational")
        default_columns = ("name", "is_operational", "description", "color", "weight")


class EnvironmentTable(ReferenceTable):
    is_production = columns.BooleanColumn(verbose_name="Production")

    class Meta(ReferenceTable.Meta):
        model = Environment
        fields = (*ReferenceTable.Meta.fields, "is_production")
        default_columns = ("name", "is_production", "description", "color", "weight")


class DeploymentStatusTable(ReferenceTable):
    is_active = columns.BooleanColumn(verbose_name="Actif")

    class Meta(ReferenceTable.Meta):
        model = DeploymentStatus
        fields = (*ReferenceTable.Meta.fields, "is_active")
        default_columns = ("name", "is_active", "description", "color", "weight")


# --- Fiche applicative ---------------------------------------------------------


class ApplicationTable(NetBoxTable):
    application_id = tables.Column(linkify=True, verbose_name="Identifiant")
    name = tables.Column(linkify=True, verbose_name="Application")
    client = tables.Column(linkify=True, verbose_name="Client")
    # Les référentiels sont désormais des objets : leur colonne est cliquable
    # et mène à leur fiche, ce qu'une valeur de liste ne permettait pas.
    lifecycle_status = tables.Column(linkify=True, verbose_name="Statut")
    criticality = tables.Column(linkify=True, verbose_name="Criticité")
    data_classification = tables.Column(linkify=True, verbose_name="Classification")
    authentication = tables.Column(linkify=True, verbose_name="Authentification")
    rto = tables.Column(linkify=True, verbose_name="RTO")
    rpo = tables.Column(linkify=True, verbose_name="RPO")
    service_hours = tables.Column(linkify=True, verbose_name="Horaires")
    personal_data = columns.BooleanColumn(verbose_name="RGPD")
    technical_contact = tables.Column(linkify=True, verbose_name="Réf. technique")
    project_manager = tables.Column(linkify=True, verbose_name="Réf. projet")
    deployment_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_applications:deployment_list",
        url_params={"application_id": "pk"},
        verbose_name="Déploiements",
    )
    tags = columns.TagColumn(url_name="plugins:netbox_applications:application_list")

    class Meta(NetBoxTable.Meta):
        model = Application
        fields = (
            "pk",
            "id",
            "application_id",
            "name",
            "client",
            "lifecycle_status",
            "criticality",
            "deployment_count",
            "rto",
            "rpo",
            "service_hours",
            "data_classification",
            "personal_data",
            "authentication",
            "technical_contact",
            "project_manager",
            "documentation_url",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = (
            "application_id",
            "name",
            "client",
            "lifecycle_status",
            "criticality",
            "deployment_count",
            "technical_contact",
        )


class DeploymentTable(NetBoxTable):
    application = tables.Column(linkify=True, verbose_name="Application")
    environment = tables.Column(linkify=True, verbose_name="Environnement")
    status = tables.Column(linkify=True, verbose_name="Statut")
    maintenance_window = tables.Column(linkify=True, verbose_name="Maintenance")
    external_facing = columns.BooleanColumn(verbose_name="Externe")
    access_url = tables.URLColumn(verbose_name="URL d'accès")
    vm_count = columns.LinkedCountColumn(
        viewname="virtualization:virtualmachine_list",
        url_params={"deployment_id": "pk"},
        verbose_name="VM",
    )
    tags = columns.TagColumn(url_name="plugins:netbox_applications:deployment_list")

    class Meta(NetBoxTable.Meta):
        model = Deployment
        fields = (
            "pk",
            "id",
            "application",
            "environment",
            "status",
            "maintenance_window",
            "external_facing",
            "access_url",
            "vm_count",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = (
            "application",
            "environment",
            "status",
            "access_url",
            "maintenance_window",
            "external_facing",
            "vm_count",
        )


class DeploymentsOnApplicationTable(DeploymentTable):
    """Variante affichée sur la fiche d'une application."""

    class Meta(DeploymentTable.Meta):
        default_columns = (
            "environment",
            "status",
            "access_url",
            "maintenance_window",
            "external_facing",
            "vm_count",
        )
