import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from .models import Application, Deployment


class ApplicationTable(NetBoxTable):
    application_id = tables.Column(linkify=True, verbose_name="Identifiant")
    name = tables.Column(linkify=True, verbose_name="Application")
    client = tables.Column(linkify=True, verbose_name="Client")
    lifecycle_status = columns.ChoiceFieldColumn(verbose_name="Statut")
    criticality = columns.ChoiceFieldColumn(verbose_name="Criticité")
    data_classification = columns.ChoiceFieldColumn(verbose_name="Classification")
    authentication = columns.ChoiceFieldColumn(verbose_name="Authentification")
    rto = columns.ChoiceFieldColumn(verbose_name="RTO")
    rpo = columns.ChoiceFieldColumn(verbose_name="RPO")
    service_hours = columns.ChoiceFieldColumn(verbose_name="Horaires")
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
        # Volontairement restreint : une liste de vingt colonnes ne se lit pas.
        # Le reste est accessible par le sélecteur de colonnes de NetBox.
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
    environment = columns.ChoiceFieldColumn(verbose_name="Environnement")
    status = columns.ChoiceFieldColumn(verbose_name="Statut")
    maintenance_window = columns.ChoiceFieldColumn(verbose_name="Maintenance")
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
            "maintenance_window",
            "external_facing",
            "vm_count",
        )


class DeploymentsOnApplicationTable(DeploymentTable):
    """Variante affichée SUR la fiche d'une application.

    La colonne « application » y serait redondante : on la retire.
    """

    class Meta(DeploymentTable.Meta):
        default_columns = (
            "environment",
            "status",
            "maintenance_window",
            "external_facing",
            "vm_count",
        )
