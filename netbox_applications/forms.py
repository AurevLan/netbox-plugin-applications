from django import forms

from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from tenancy.models import Contact, Tenant
from utilities.forms.fields import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)
from utilities.forms.rendering import FieldSet
from virtualization.models import VirtualMachine

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


class ApplicationForm(NetBoxModelForm):
    # Les querysets sont fournis ICI, à la construction du champ :
    # DynamicModelChoiceField lit queryset.model immédiatement.
    client = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label="Client",
        help_text="Le client est un « Tenant » NetBox — sens natif de cet objet.",
    )
    technical_contact = DynamicModelChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent technique"
    )
    project_manager = DynamicModelChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent chef de projet"
    )
    comments = CommentField()

    # Le formulaire suit l'ordre dans lequel on remplit une fiche :
    # qui, puis quelle importance, puis quels engagements, puis quelle sécurité.
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
    model = Application
    lifecycle_status = forms.MultipleChoiceField(choices=LifecycleChoices, required=False, label="Statut")
    criticality = forms.MultipleChoiceField(choices=CriticalityChoices, required=False, label="Criticité")
    data_classification = forms.MultipleChoiceField(
        choices=DataClassificationChoices, required=False, label="Classification"
    )
    authentication = forms.MultipleChoiceField(
        choices=AuthenticationChoices, required=False, label="Authentification"
    )
    personal_data = forms.NullBooleanField(required=False, label="Données personnelles")


class DeploymentForm(NetBoxModelForm):
    application = DynamicModelChoiceField(queryset=Application.objects.all(), label="Application")
    virtual_machines = DynamicModelMultipleChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        label="VM",
    )
    comments = CommentField()

    fieldsets = (
        FieldSet("application", "environment", "status", "description", name="Identité"),
        FieldSet("maintenance_window", "external_facing", "url", name="Exploitation"),
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
            "url",
            "virtual_machines",
            "comments",
            "tags",
        )


class DeploymentFilterForm(NetBoxModelFilterSetForm):
    model = Deployment
    application_id = DynamicModelMultipleChoiceField(
        queryset=Application.objects.all(), required=False, label="Application"
    )
    environment = forms.MultipleChoiceField(choices=EnvironmentChoices, required=False, label="Environnement")
    status = forms.MultipleChoiceField(choices=DeploymentStatusChoices, required=False, label="Statut")
    maintenance_window = forms.MultipleChoiceField(
        choices=MaintenanceWindowChoices, required=False, label="Maintenance"
    )
    external_facing = forms.NullBooleanField(required=False, label="Diffusé à l'externe")
