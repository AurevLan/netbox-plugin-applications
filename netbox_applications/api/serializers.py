from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer
from tenancy.api.serializers import ContactSerializer, TenantSerializer
from virtualization.api.serializers import VirtualMachineSerializer

from .. import models

# --- Référentiels --------------------------------------------------------------


def _reference_serializer(modele, champs_extra=()):
    """Fabrique le sérialiseur d'un référentiel.

    Les dix référentiels partagent la même forme ; seuls leurs attributs
    propres diffèrent. Une fabrique garantit qu'ils restent alignés.
    """
    n = modele.__name__.lower()
    base_fields = (
        "id",
        "url",
        "display",
        "name",
        "slug",
        "description",
        "color",
        "weight",
        "tags",
        "custom_fields",
        "created",
        "last_updated",
    )
    meta = type(
        "Meta",
        (),
        {
            "model": modele,
            "fields": (*base_fields, *champs_extra),
            "brief_fields": ("id", "url", "display", "name", "slug", "color"),
        },
    )
    return type(
        f"{modele.__name__}Serializer",
        (NetBoxModelSerializer,),
        {
            "url": serializers.HyperlinkedIdentityField(
                view_name=f"plugins-api:netbox_applications-api:{n}-detail"
            ),
            "Meta": meta,
        },
    )


LifecycleStatusSerializer = _reference_serializer(models.LifecycleStatus, ("is_operational",))
CriticalitySerializer = _reference_serializer(models.Criticality, ("incident_priority", "requires_oncall"))
RTOSerializer = _reference_serializer(models.RTO, ("minutes",))
RPOSerializer = _reference_serializer(models.RPO, ("minutes",))
ServiceHoursSerializer = _reference_serializer(
    models.ServiceHours, ("start_time", "end_time", "includes_weekend", "includes_oncall")
)
DataClassificationSerializer = _reference_serializer(
    models.DataClassification, ("level", "requires_encryption")
)
AuthenticationMethodSerializer = _reference_serializer(models.AuthenticationMethod, ("is_centralized",))
EnvironmentSerializer = _reference_serializer(models.Environment, ("is_production",))
DeploymentStatusSerializer = _reference_serializer(models.DeploymentStatus, ("is_active",))
MaintenanceWindowSerializer = _reference_serializer(
    models.MaintenanceWindow, ("start_time", "end_time", "allows_interruption")
)


# --- Fiche applicative ---------------------------------------------------------


class ApplicationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_applications-api:application-detail"
    )
    client = TenantSerializer(nested=True, required=False, allow_null=True)
    technical_contact = ContactSerializer(nested=True, required=False, allow_null=True)
    project_manager = ContactSerializer(nested=True, required=False, allow_null=True)
    # Les référentiels sont des objets : l'API expose leur fiche complète en
    # forme abrégée, pas seulement une valeur. On peut ainsi lire
    # « authentication.is_centralized » sans requête supplémentaire.
    lifecycle_status = LifecycleStatusSerializer(nested=True, required=False, allow_null=True)
    criticality = CriticalitySerializer(nested=True, required=False, allow_null=True)
    rto = RTOSerializer(nested=True, required=False, allow_null=True)
    rpo = RPOSerializer(nested=True, required=False, allow_null=True)
    service_hours = ServiceHoursSerializer(nested=True, required=False, allow_null=True)
    data_classification = DataClassificationSerializer(nested=True, required=False, allow_null=True)
    authentication = AuthenticationMethodSerializer(nested=True, required=False, allow_null=True)
    deployment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Application
        fields = (
            "id",
            "url",
            "display",
            "application_id",
            "name",
            "client",
            "lifecycle_status",
            "criticality",
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
            "comments",
            "deployment_count",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        )
        brief_fields = ("id", "url", "display", "application_id", "name")


class DeploymentSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_applications-api:deployment-detail"
    )
    application = ApplicationSerializer(nested=True)
    environment = EnvironmentSerializer(nested=True)
    status = DeploymentStatusSerializer(nested=True, required=False, allow_null=True)
    maintenance_window = MaintenanceWindowSerializer(nested=True, required=False, allow_null=True)
    virtual_machines = VirtualMachineSerializer(nested=True, many=True, required=False)

    class Meta:
        model = models.Deployment
        fields = (
            "id",
            "url",
            "display",
            "application",
            "environment",
            "status",
            "maintenance_window",
            "external_facing",
            "access_url",
            "virtual_machines",
            "description",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        )
        brief_fields = ("id", "url", "display", "application", "environment")
