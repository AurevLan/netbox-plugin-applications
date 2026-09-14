import django_filters
from django.db.models import Q

from netbox.filtersets import NetBoxModelFilterSet
from tenancy.models import Contact, Tenant

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


class ReferenceFilterSet(NetBoxModelFilterSet):
    """Filtre commun aux référentiels : recherche sur le nom et la description."""

    class Meta:
        fields = ("id", "name", "slug")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


def _reference_filterset(modele, **extra):
    """Fabrique le filtre d'un référentiel.

    Écrire dix classes identiques inviterait à en oublier une lors d'une
    correction. La fabrique garantit qu'elles restent alignées.
    """
    meta = type("Meta", (ReferenceFilterSet.Meta,), {"model": modele})
    return type(f"{modele.__name__}FilterSet", (ReferenceFilterSet,), {"Meta": meta, **extra})


AuthenticationMethodFilterSet = _reference_filterset(AuthenticationMethod)
MaintenanceWindowFilterSet = _reference_filterset(MaintenanceWindow)
CriticalityFilterSet = _reference_filterset(Criticality)
RTOFilterSet = _reference_filterset(RTO)
RPOFilterSet = _reference_filterset(RPO)
ServiceHoursFilterSet = _reference_filterset(ServiceHours)
DataClassificationFilterSet = _reference_filterset(DataClassification)
LifecycleStatusFilterSet = _reference_filterset(LifecycleStatus)
EnvironmentFilterSet = _reference_filterset(Environment)
DeploymentStatusFilterSet = _reference_filterset(DeploymentStatus)


class ApplicationFilterSet(NetBoxModelFilterSet):
    # Les noms en « _id » sont ceux qu'emploie le formulaire de filtre.
    lifecycle_status_id = django_filters.ModelMultipleChoiceFilter(
        queryset=LifecycleStatus.objects.all(), field_name="lifecycle_status"
    )
    criticality_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Criticality.objects.all(), field_name="criticality"
    )
    rto_id = django_filters.ModelMultipleChoiceFilter(queryset=RTO.objects.all(), field_name="rto")
    rpo_id = django_filters.ModelMultipleChoiceFilter(queryset=RPO.objects.all(), field_name="rpo")
    service_hours_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ServiceHours.objects.all(), field_name="service_hours"
    )
    data_classification_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DataClassification.objects.all(), field_name="data_classification"
    )
    authentication_id = django_filters.ModelMultipleChoiceFilter(
        queryset=AuthenticationMethod.objects.all(), field_name="authentication"
    )
    client_id = django_filters.ModelMultipleChoiceFilter(queryset=Tenant.objects.all(), field_name="client")
    technical_contact_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Contact.objects.all(), field_name="technical_contact"
    )
    project_manager_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Contact.objects.all(), field_name="project_manager"
    )
    # Traverse la relation vers les déploiements.
    environment_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Environment.objects.all(),
        field_name="deployments__environment",
        distinct=True,
        label="Environnement de déploiement",
    )
    # Ces deux filtres interrogent un ATTRIBUT du référentiel, pas son nom :
    # « quelles applications ont une authentification non centralisée ? » reste
    # juste même si la méthode s'appelle « comptes applicatifs » et non « locale ».
    authentication_centralized = django_filters.BooleanFilter(
        field_name="authentication__is_centralized", label="Authentification centralisée"
    )
    operational = django_filters.BooleanFilter(
        field_name="lifecycle_status__is_operational", label="En service"
    )

    # « contient » plutôt qu'égalité : on cherche par domaine ou par service,
    # « @direction-rh », pas par adresse exacte qu'on devrait connaître.
    business_contact = django_filters.CharFilter(lookup_expr="icontains", label="Contact métier (contient)")

    class Meta:
        model = Application
        fields = ("id", "name", "application_id", "personal_data")

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(application_id__icontains=value)
            | Q(description__icontains=value)
            | Q(business_contact__icontains=value)
        )


class DeploymentFilterSet(NetBoxModelFilterSet):
    application_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Application.objects.all(), field_name="application"
    )
    environment_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Environment.objects.all(), field_name="environment"
    )
    status_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeploymentStatus.objects.all(), field_name="status"
    )
    maintenance_window_id = django_filters.ModelMultipleChoiceFilter(
        queryset=MaintenanceWindow.objects.all(), field_name="maintenance_window"
    )
    production = django_filters.BooleanFilter(field_name="environment__is_production", label="En production")

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
