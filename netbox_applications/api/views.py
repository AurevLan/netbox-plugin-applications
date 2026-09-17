from django.db.models import Count

from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from . import serializers


def _reference_viewset(modele, serializer, filterset):
    return type(
        f"{modele.__name__}ViewSet",
        (NetBoxModelViewSet,),
        {
            "queryset": modele.objects.prefetch_related("tags"),
            "serializer_class": serializer,
            "filterset_class": filterset,
        },
    )


LifecycleStatusViewSet = _reference_viewset(
    models.LifecycleStatus, serializers.LifecycleStatusSerializer, filtersets.LifecycleStatusFilterSet
)
CriticalityViewSet = _reference_viewset(
    models.Criticality, serializers.CriticalitySerializer, filtersets.CriticalityFilterSet
)
RTOViewSet = _reference_viewset(models.RTO, serializers.RTOSerializer, filtersets.RTOFilterSet)
RPOViewSet = _reference_viewset(models.RPO, serializers.RPOSerializer, filtersets.RPOFilterSet)
ServiceHoursViewSet = _reference_viewset(
    models.ServiceHours, serializers.ServiceHoursSerializer, filtersets.ServiceHoursFilterSet
)
DataClassificationViewSet = _reference_viewset(
    models.DataClassification,
    serializers.DataClassificationSerializer,
    filtersets.DataClassificationFilterSet,
)
AuthenticationMethodViewSet = _reference_viewset(
    models.AuthenticationMethod,
    serializers.AuthenticationMethodSerializer,
    filtersets.AuthenticationMethodFilterSet,
)
EnvironmentViewSet = _reference_viewset(
    models.Environment, serializers.EnvironmentSerializer, filtersets.EnvironmentFilterSet
)
DeploymentStatusViewSet = _reference_viewset(
    models.DeploymentStatus,
    serializers.DeploymentStatusSerializer,
    filtersets.DeploymentStatusFilterSet,
)
MaintenanceWindowViewSet = _reference_viewset(
    models.MaintenanceWindow,
    serializers.MaintenanceWindowSerializer,
    filtersets.MaintenanceWindowFilterSet,
)


class ApplicationViewSet(NetBoxModelViewSet):
    queryset = models.Application.objects.prefetch_related(
        "client",
        "technical_contact",
        "project_manager",
        "tags",
        "lifecycle_status",
        "criticality",
        "rto",
        "rpo",
        "service_hours",
        "data_classification",
        "authentication",
    ).annotate(deployment_count=Count("deployments"))
    serializer_class = serializers.ApplicationSerializer
    filterset_class = filtersets.ApplicationFilterSet


class DeploymentViewSet(NetBoxModelViewSet):
    queryset = models.Deployment.objects.prefetch_related(
        "application",
        "environment",
        "status",
        "maintenance_window",
        "waf_virtual_server",
        "virtual_machines",
        "tags",
    )
    serializer_class = serializers.DeploymentSerializer
    filterset_class = filtersets.DeploymentFilterSet


class VirtualServerViewSet(NetBoxModelViewSet):
    queryset = models.VirtualServer.objects.prefetch_related("ip_address", "tags")
    serializer_class = serializers.VirtualServerSerializer
    filterset_class = filtersets.VirtualServerFilterSet
