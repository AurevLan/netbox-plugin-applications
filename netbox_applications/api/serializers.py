from rest_framework import serializers

from netbox.api.fields import ChoiceField
from netbox.api.serializers import NetBoxModelSerializer
from tenancy.api.serializers import ContactSerializer, TenantSerializer
from virtualization.api.serializers import VirtualMachineSerializer

from ..choices import (
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
from ..models import Application, Deployment


class ApplicationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netbox_applications-api:application-detail"
    )
    client = TenantSerializer(nested=True, required=False, allow_null=True)
    technical_contact = ContactSerializer(nested=True, required=False, allow_null=True)
    project_manager = ContactSerializer(nested=True, required=False, allow_null=True)
    # ChoiceField expose {value, label} : l'API se lit sans connaître les codes.
    lifecycle_status = ChoiceField(choices=LifecycleChoices, required=False)
    criticality = ChoiceField(choices=CriticalityChoices, required=False)
    rto = ChoiceField(choices=RTOChoices, required=False, allow_blank=True)
    rpo = ChoiceField(choices=RPOChoices, required=False, allow_blank=True)
    service_hours = ChoiceField(choices=ServiceHoursChoices, required=False, allow_blank=True)
    data_classification = ChoiceField(choices=DataClassificationChoices, required=False)
    authentication = ChoiceField(choices=AuthenticationChoices, required=False, allow_blank=True)
    deployment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Application
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
    environment = ChoiceField(choices=EnvironmentChoices)
    status = ChoiceField(choices=DeploymentStatusChoices, required=False)
    maintenance_window = ChoiceField(choices=MaintenanceWindowChoices, required=False)
    virtual_machines = VirtualMachineSerializer(nested=True, many=True, required=False)

    class Meta:
        model = Deployment
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
