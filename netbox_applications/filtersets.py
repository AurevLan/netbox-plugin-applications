import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet

from .choices import (
    AuthenticationChoices,
    CriticalityChoices,
    DataClassificationChoices,
    DeploymentStatusChoices,
    EnvironmentChoices,
    LifecycleChoices,
    MaintenanceWindowChoices,
)
from .models import Application, Deployment


class ApplicationFilterSet(NetBoxModelFilterSet):
    lifecycle_status = django_filters.MultipleChoiceFilter(choices=LifecycleChoices)
    criticality = django_filters.MultipleChoiceFilter(choices=CriticalityChoices)
    data_classification = django_filters.MultipleChoiceFilter(choices=DataClassificationChoices)
    authentication = django_filters.MultipleChoiceFilter(choices=AuthenticationChoices)
    # Filtrer les applications PAR environnement de déploiement : c'est la
    # question qu'on pose réellement (« quelles applications sont en prod ? »),
    # et elle traverse la relation.
    environment = django_filters.MultipleChoiceFilter(
        choices=EnvironmentChoices,
        field_name="deployments__environment",
        distinct=True,
        label="Environnement de déploiement",
    )

    class Meta:
        model = Application
        fields = (
            "id",
            "name",
            "application_id",
            "client",
            "personal_data",
            "technical_contact",
            "project_manager",
            "rto",
            "rpo",
            "service_hours",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(application_id__icontains=value) | Q(description__icontains=value)
        )


class DeploymentFilterSet(NetBoxModelFilterSet):
    environment = django_filters.MultipleChoiceFilter(choices=EnvironmentChoices)
    status = django_filters.MultipleChoiceFilter(choices=DeploymentStatusChoices)
    maintenance_window = django_filters.MultipleChoiceFilter(choices=MaintenanceWindowChoices)
    application_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Application.objects.all(),
        label="Application",
    )

    class Meta:
        model = Deployment
        fields = ("id", "external_facing")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(application__name__icontains=value)
            | Q(application__application_id__icontains=value)
            | Q(description__icontains=value)
        )
