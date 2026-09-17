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
    VirtualServer,
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
    is_operational = columns.BooleanColumn(verbose_name="Service rendu")

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
    is_active = columns.BooleanColumn(verbose_name="En fonctionnement")

    class Meta(ReferenceTable.Meta):
        model = DeploymentStatus
        fields = (*ReferenceTable.Meta.fields, "is_active")
        default_columns = ("name", "is_active", "description", "color", "weight")


# --- Fiche applicative ---------------------------------------------------------


class ApplicationTable(NetBoxTable):
    application_id = tables.Column(linkify=True, verbose_name="Identifiant")
    name = tables.Column(linkify=True, verbose_name="Application")
    client = tables.Column(linkify=True, verbose_name="Client")
    # Les référentiels sont des objets : leur colonne est cliquable et mène à
    # leur fiche, ce qu'une valeur de liste ne permettait pas. Elle porte en
    # outre la COULEUR de la valeur — c'est dans une liste de plusieurs
    # dizaines de lignes que la palette paie : le regard trie sans lire.
    lifecycle_status = columns.ColoredLabelColumn(verbose_name="Cycle de vie")
    criticality = columns.ColoredLabelColumn(verbose_name="Criticité")
    data_classification = columns.ColoredLabelColumn(verbose_name="Classification")
    authentication = columns.ColoredLabelColumn(verbose_name="Authentification")
    rto = columns.ColoredLabelColumn(verbose_name="RTO")
    rpo = columns.ColoredLabelColumn(verbose_name="RPO")
    service_hours = columns.ColoredLabelColumn(verbose_name="Horaires")
    personal_data = columns.BooleanColumn(verbose_name="RGPD")
    technical_contact = tables.Column(linkify=True, verbose_name="Réf. technique")
    project_manager = tables.Column(linkify=True, verbose_name="Réf. projet")
    business_contact = tables.EmailColumn(verbose_name="Contact métier")
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
            "business_contact",
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
    environment = columns.ColoredLabelColumn(verbose_name="Environnement")
    status = columns.ColoredLabelColumn(verbose_name="État")
    maintenance_window = columns.ColoredLabelColumn(verbose_name="Maintenance")
    external_facing = columns.BooleanColumn(verbose_name="Externe")
    waf_enabled = columns.BooleanColumn(verbose_name="WAF")
    waf_virtual_server = tables.Column(linkify=True, verbose_name="Serveur virtuel WAF")
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
            "waf_enabled",
            "waf_virtual_server",
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
            "external_facing",
            "waf_enabled",
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


class VirtualServerTable(NetBoxTable):
    name = tables.Column(linkify=True, verbose_name="Nom")
    ip_address = tables.Column(linkify=True, verbose_name="Adresse IP")
    port = tables.Column(verbose_name="Port")
    prefix = tables.Column(linkify=True, orderable=False, verbose_name="Préfixe")
    deployment_count = columns.LinkedCountColumn(
        viewname="plugins:netbox_applications:deployment_list",
        url_params={"waf_virtual_server_id": "pk"},
        verbose_name="Déploiements",
    )
    tags = columns.TagColumn(url_name="plugins:netbox_applications:virtualserver_list")

    class Meta(NetBoxTable.Meta):
        model = VirtualServer
        fields = (
            "pk",
            "id",
            "name",
            "ip_address",
            "port",
            "prefix",
            "deployment_count",
            "description",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("name", "ip_address", "port", "prefix", "deployment_count", "description")
