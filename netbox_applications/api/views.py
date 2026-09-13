from django.db.models import Count

from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from .serializers import ApplicationSerializer, DeploymentSerializer


class ApplicationViewSet(NetBoxModelViewSet):
    queryset = models.Application.objects.prefetch_related(
        "client", "technical_contact", "project_manager", "tags"
    ).annotate(deployment_count=Count("deployments"))
    serializer_class = ApplicationSerializer
    filterset_class = filtersets.ApplicationFilterSet


class DeploymentViewSet(NetBoxModelViewSet):
    queryset = models.Deployment.objects.prefetch_related("application", "virtual_machines", "tags")
    serializer_class = DeploymentSerializer
    filterset_class = filtersets.DeploymentFilterSet
