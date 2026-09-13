from django import forms

from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from tenancy.models import Contact, Tenant
from utilities.forms.fields import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    SlugField,
)
from utilities.forms.rendering import FieldSet
from virtualization.models import VirtualMachine

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

# Champs communs à tout référentiel. Les déclarer une fois évite dix listes
# recopiées qui divergeraient au premier ajout.
_REF_FIELDS = ("name", "slug", "description", "color", "weight", "tags")


class ReferenceForm(NetBoxModelForm):
    slug = SlugField()

    class Meta:
        fields = _REF_FIELDS


class AuthenticationMethodForm(ReferenceForm):
    fieldsets = (
        FieldSet("name", "slug", "description", name="Identité"),
        FieldSet("is_centralized", name="Gestion des comptes"),
        FieldSet("color", "weight", "tags", name="Présentation"),
    )

    class Meta(ReferenceForm.Meta):
        model = AuthenticationMethod
        fields = (*_REF_FIELDS, "is_centralized")


class MaintenanceWindowForm(ReferenceForm):
    fieldsets = (
        FieldSet("name", "slug", "description", name="Identité"),
        FieldSet("start_time", "end_time", "allows_interruption", name="Créneau"),
        FieldSet("color", "weight", "tags", name="Présentation"),
    )

    class Meta(ReferenceForm.Meta):
        model = MaintenanceWindow
        fields = (*_REF_FIELDS, "start_time", "end_time", "allows_interruption")


class CriticalityForm(ReferenceForm):
    fieldsets = (
        FieldSet("name", "slug", "description", name="Identité"),
        FieldSet("incident_priority", "requires_oncall", name="Traitement des incidents"),
        FieldSet("color", "weight", "tags", name="Présentation"),
    )

    class Meta(ReferenceForm.Meta):
        model = Criticality
        fields = (*_REF_FIELDS, "incident_priority", "requires_oncall")


class RTOForm(ReferenceForm):
    class Meta(ReferenceForm.Meta):
        model = RTO
        fields = (*_REF_FIELDS, "minutes")


class RPOForm(ReferenceForm):
    class Meta(ReferenceForm.Meta):
        model = RPO
        fields = (*_REF_FIELDS, "minutes")


class ServiceHoursForm(ReferenceForm):
    fieldsets = (
        FieldSet("name", "slug", "description", name="Identité"),
        FieldSet("start_time", "end_time", "includes_weekend", "includes_oncall", name="Plage"),
        FieldSet("color", "weight", "tags", name="Présentation"),
    )

    class Meta(ReferenceForm.Meta):
        model = ServiceHours
        fields = (
            *_REF_FIELDS,
            "start_time",
            "end_time",
            "includes_weekend",
            "includes_oncall",
        )


class DataClassificationForm(ReferenceForm):
    class Meta(ReferenceForm.Meta):
        model = DataClassification
        fields = (*_REF_FIELDS, "level", "requires_encryption")


class LifecycleStatusForm(ReferenceForm):
    class Meta(ReferenceForm.Meta):
        model = LifecycleStatus
        fields = (*_REF_FIELDS, "is_operational")


class EnvironmentForm(ReferenceForm):
    class Meta(ReferenceForm.Meta):
        model = Environment
        fields = (*_REF_FIELDS, "is_production")


class DeploymentStatusForm(ReferenceForm):
    class Meta(ReferenceForm.Meta):
        model = DeploymentStatus
        fields = (*_REF_FIELDS, "is_active")


class ReferenceFilterForm(NetBoxModelFilterSetForm):
    """Filtre minimal commun aux référentiels : recherche et étiquettes."""

    fieldsets = (FieldSet("q", "filter_id", "tag"),)


# --- Fiche applicative ---------------------------------------------------------


class ApplicationForm(NetBoxModelForm):
    client = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label="Client",
        help_text="Le client est un « Tenant » NetBox — sens natif de cet objet.",
    )
    lifecycle_status = DynamicModelChoiceField(
        queryset=LifecycleStatus.objects.all(), required=False, label="Statut du service"
    )
    criticality = DynamicModelChoiceField(
        queryset=Criticality.objects.all(), required=False, label="Criticité métier"
    )
    rto = DynamicModelChoiceField(queryset=RTO.objects.all(), required=False, label="RTO")
    rpo = DynamicModelChoiceField(queryset=RPO.objects.all(), required=False, label="RPO")
    service_hours = DynamicModelChoiceField(
        queryset=ServiceHours.objects.all(), required=False, label="Horaires de service"
    )
    data_classification = DynamicModelChoiceField(
        queryset=DataClassification.objects.all(), required=False, label="Classification"
    )
    authentication = DynamicModelChoiceField(
        queryset=AuthenticationMethod.objects.all(), required=False, label="Authentification"
    )
    technical_contact = DynamicModelChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent technique"
    )
    project_manager = DynamicModelChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent chef de projet"
    )
    comments = CommentField()

    fieldsets = (
        FieldSet("name", "client", "description", "documentation_url", name="Identité"),
        FieldSet("lifecycle_status", "criticality", name="Cycle de vie"),
        FieldSet("rto", "rpo", "service_hours", name="Continuité de service"),
        FieldSet("data_classification", "personal_data", "authentication", name="Sécurité"),
        FieldSet("technical_contact", "project_manager", name="Référents"),
        FieldSet("tags", name="Divers"),
    )

    class Meta:
        model = Application
        fields = (
            "name",
            "client",
            "description",
            "documentation_url",
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
            "comments",
            "tags",
        )


class ApplicationFilterForm(NetBoxModelFilterSetForm):
    """Filtres de la liste des applications.

    Les « fieldsets » ne sont pas cosmétiques : sans eux, NetBox affiche les
    champs à la suite, sans titre, mêlés à « filter_id » et « q ». Les filtres
    existent alors mais restent introuvables.
    """

    model = Application
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("lifecycle_status_id", "criticality_id", name="Cycle de vie"),
        FieldSet("rto_id", "rpo_id", "service_hours_id", name="Continuité"),
        FieldSet("data_classification_id", "personal_data", "authentication_id", name="Sécurité"),
        FieldSet("client_id", "technical_contact_id", "project_manager_id", name="Rattachements"),
        FieldSet("environment_id", name="Déploiements"),
    )

    lifecycle_status_id = DynamicModelMultipleChoiceField(
        queryset=LifecycleStatus.objects.all(), required=False, label="Statut du service"
    )
    criticality_id = DynamicModelMultipleChoiceField(
        queryset=Criticality.objects.all(), required=False, label="Criticité"
    )
    rto_id = DynamicModelMultipleChoiceField(queryset=RTO.objects.all(), required=False, label="RTO")
    rpo_id = DynamicModelMultipleChoiceField(queryset=RPO.objects.all(), required=False, label="RPO")
    service_hours_id = DynamicModelMultipleChoiceField(
        queryset=ServiceHours.objects.all(), required=False, label="Horaires"
    )
    data_classification_id = DynamicModelMultipleChoiceField(
        queryset=DataClassification.objects.all(), required=False, label="Classification"
    )
    authentication_id = DynamicModelMultipleChoiceField(
        queryset=AuthenticationMethod.objects.all(), required=False, label="Authentification"
    )
    personal_data = forms.NullBooleanField(required=False, label="Données personnelles")
    client_id = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False, label="Client")
    technical_contact_id = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent technique"
    )
    project_manager_id = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent chef de projet"
    )
    # Traverse la relation : « quelles applications sont en production ? »
    environment_id = DynamicModelMultipleChoiceField(
        queryset=Environment.objects.all(), required=False, label="Environnement de déploiement"
    )


class DeploymentForm(NetBoxModelForm):
    application = DynamicModelChoiceField(queryset=Application.objects.all(), label="Application")
    environment = DynamicModelChoiceField(queryset=Environment.objects.all(), label="Environnement")
    status = DynamicModelChoiceField(queryset=DeploymentStatus.objects.all(), required=False, label="Statut")
    maintenance_window = DynamicModelChoiceField(
        queryset=MaintenanceWindow.objects.all(), required=False, label="Plage de maintenance"
    )
    virtual_machines = DynamicModelMultipleChoiceField(
        queryset=VirtualMachine.objects.all(), required=False, label="VM"
    )
    comments = CommentField()

    fieldsets = (
        FieldSet("application", "environment", "status", "description", name="Identité"),
        FieldSet("maintenance_window", "external_facing", "access_url", name="Exploitation"),
        FieldSet("virtual_machines", name="Ressources"),
        FieldSet("tags", name="Divers"),
    )

    class Meta:
        model = Deployment
        fields = (
            "application",
            "environment",
            "status",
            "description",
            "maintenance_window",
            "external_facing",
            "access_url",
            "virtual_machines",
            "comments",
            "tags",
        )


class DeploymentFilterForm(NetBoxModelFilterSetForm):
    model = Deployment
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("application_id", "environment_id", "status_id", name="Identité"),
        FieldSet("maintenance_window_id", "external_facing", name="Exploitation"),
    )

    application_id = DynamicModelMultipleChoiceField(
        queryset=Application.objects.all(), required=False, label="Application"
    )
    environment_id = DynamicModelMultipleChoiceField(
        queryset=Environment.objects.all(), required=False, label="Environnement"
    )
    status_id = DynamicModelMultipleChoiceField(
        queryset=DeploymentStatus.objects.all(), required=False, label="Statut"
    )
    maintenance_window_id = DynamicModelMultipleChoiceField(
        queryset=MaintenanceWindow.objects.all(), required=False, label="Maintenance"
    )
    external_facing = forms.NullBooleanField(required=False, label="Diffusé à l'externe")
