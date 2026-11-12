from django import forms
from django.contrib.contenttypes.models import ContentType

from dcim.models import Device
from ipam.models import IPAddress, IPRange, Prefix, Service
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from tenancy.models import Contact, Tenant
from utilities.forms.fields import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    SlugField,
)
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import APISelectMultiple
from virtualization.models import VirtualMachine

from .choices import FlowStatusChoices
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
    Flow,
    LifecycleStatus,
    MaintenanceWindow,
    ServiceHours,
    VirtualServer,
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
        queryset=LifecycleStatus.objects.all(), required=False, label="Cycle de vie du service"
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
        FieldSet("technical_contact", "project_manager", "business_contact", name="Référents"),
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
            "business_contact",
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
        FieldSet("lifecycle_status_id", "operational", "criticality_id", name="Cycle de vie"),
        FieldSet("rto_id", "rpo_id", "service_hours_id", name="Continuité"),
        FieldSet(
            "data_classification_id",
            "personal_data",
            "authentication_id",
            "authentication_centralized",
            name="Sécurité",
        ),
        FieldSet(
            "client_id",
            "technical_contact_id",
            "project_manager_id",
            "business_contact",
            name="Rattachements",
        ),
        FieldSet("environment_id", name="Déploiements"),
    )

    lifecycle_status_id = DynamicModelMultipleChoiceField(
        queryset=LifecycleStatus.objects.all(), required=False, label="Cycle de vie du service"
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
    # Filtres portant sur un ATTRIBUT du référentiel, pas sur son nom : ils
    # survivent au renommage d'une valeur. Sans entrée dans un « fieldset »,
    # ils n'existeraient que pour l'API.
    operational = forms.NullBooleanField(required=False, label="Service rendu")
    authentication_centralized = forms.NullBooleanField(required=False, label="Authentification centralisée")
    client_id = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False, label="Client")
    technical_contact_id = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent technique"
    )
    project_manager_id = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(), required=False, label="Référent chef de projet"
    )
    # Recherche partielle : on tape « @direction-rh » pour trouver toutes les
    # applications dont le métier relève de ce service.
    business_contact = forms.CharField(required=False, label="Contact métier (contient)")
    # Traverse la relation : « quelles applications sont en production ? »
    environment_id = DynamicModelMultipleChoiceField(
        queryset=Environment.objects.all(), required=False, label="Environnement de déploiement"
    )


class DeploymentForm(NetBoxModelForm):
    application = DynamicModelChoiceField(queryset=Application.objects.all(), label="Application")
    environment = DynamicModelChoiceField(queryset=Environment.objects.all(), label="Environnement")
    status = DynamicModelChoiceField(
        queryset=DeploymentStatus.objects.all(), required=False, label="État de l'instance"
    )
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
        FieldSet("waf_enabled", "waf_virtual_server", name="Pare-feu applicatif"),
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
            "waf_enabled",
            "waf_virtual_server",
            "virtual_machines",
            "comments",
            "tags",
        )


class DeploymentFilterForm(NetBoxModelFilterSetForm):
    model = Deployment
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("application_id", "environment_id", "production", "status_id", name="Identité"),
        FieldSet("maintenance_window_id", "external_facing", name="Exploitation"),
        FieldSet("waf_enabled", "waf_virtual_server_id", "expose_sans_waf", name="Pare-feu applicatif"),
    )

    application_id = DynamicModelMultipleChoiceField(
        queryset=Application.objects.all(), required=False, label="Application"
    )
    environment_id = DynamicModelMultipleChoiceField(
        queryset=Environment.objects.all(), required=False, label="Environnement"
    )
    # Porte sur l'attribut « is_production » de l'environnement, pas sur son nom.
    production = forms.NullBooleanField(required=False, label="En production")
    status_id = DynamicModelMultipleChoiceField(
        queryset=DeploymentStatus.objects.all(), required=False, label="État de l'instance"
    )
    maintenance_window_id = DynamicModelMultipleChoiceField(
        queryset=MaintenanceWindow.objects.all(), required=False, label="Maintenance"
    )
    external_facing = forms.NullBooleanField(required=False, label="Diffusé à l'externe")
    waf_enabled = forms.NullBooleanField(required=False, label="WAF activé")
    waf_virtual_server_id = DynamicModelMultipleChoiceField(
        queryset=VirtualServer.objects.all(), required=False, label="Serveur virtuel WAF"
    )
    # La question qui motive tout ce champ : « qu'est-ce qui est exposé sans
    # filtrage ? ». Elle croise deux champs, donc aucun filtre simple ne la pose.
    expose_sans_waf = forms.NullBooleanField(required=False, label="Exposé sans WAF")


class VirtualServerForm(NetBoxModelForm):
    ip_address = DynamicModelChoiceField(queryset=IPAddress.objects.all(), label="Adresse IP")
    comments = CommentField()

    fieldsets = (
        FieldSet("name", "description", name="Identité"),
        FieldSet("ip_address", "port", name="Point d'entrée"),
        FieldSet("tags", name="Divers"),
    )

    class Meta:
        model = VirtualServer
        fields = ("name", "description", "ip_address", "port", "comments", "tags")


class VirtualServerFilterForm(NetBoxModelFilterSetForm):
    model = VirtualServer
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("ip_address_id", "port", name="Point d'entrée"),
    )

    ip_address_id = DynamicModelMultipleChoiceField(
        queryset=IPAddress.objects.all(), required=False, label="Adresse IP"
    )
    port = forms.IntegerField(required=False, label="Port")


# --- Flux ----------------------------------------------------------------------
#
# LES EXTRÉMITÉS SONT SAISIES PAR TYPE, un champ par type d'objet.
#
# L'alternative aurait été un sélecteur de type suivi d'un identifiant
# numérique. Elle tient en deux champs, et elle est inutilisable : personne ne
# connaît l'identifiant interne d'un préfixe, et une erreur d'un chiffre
# désigne silencieusement un autre réseau. Sept champs facultatifs dont un seul
# se remplit coûtent de la place dans le formulaire, et rien d'autre.

# (suffixe du champ, modèle, libellé)
EXTREMITES_SAISIE = (
    ("prefix", Prefix, "Préfixe"),
    ("ip_range", IPRange, "Plage d'adresses"),
    ("ip_address", IPAddress, "Adresse IP"),
    ("virtual_machine", VirtualMachine, "VM"),
    ("device", Device, "Équipement"),
    ("virtual_server", VirtualServer, "Serveur virtuel"),
    ("deployment", Deployment, "Déploiement d'une autre application"),
)


def _champ_extremite(modele, libelle):
    return DynamicModelChoiceField(queryset=modele.objects.all(), required=False, label=libelle)


class FlowForm(NetBoxModelForm):
    deployment = DynamicModelChoiceField(queryset=Deployment.objects.all(), label="Déploiement")

    source_prefix = _champ_extremite(Prefix, "Préfixe")
    source_ip_range = _champ_extremite(IPRange, "Plage d'adresses")
    source_ip_address = _champ_extremite(IPAddress, "Adresse IP")
    source_virtual_machine = _champ_extremite(VirtualMachine, "VM")
    source_device = _champ_extremite(Device, "Équipement")
    source_virtual_server = _champ_extremite(VirtualServer, "Serveur virtuel")
    source_deployment = _champ_extremite(Deployment, "Déploiement d'une autre application")

    destination_prefix = _champ_extremite(Prefix, "Préfixe")
    destination_ip_range = _champ_extremite(IPRange, "Plage d'adresses")
    destination_ip_address = _champ_extremite(IPAddress, "Adresse IP")
    destination_virtual_machine = _champ_extremite(VirtualMachine, "VM")
    destination_device = _champ_extremite(Device, "Équipement")
    destination_virtual_server = _champ_extremite(VirtualServer, "Serveur virtuel")
    destination_deployment = _champ_extremite(Deployment, "Déploiement d'une autre application")

    service = DynamicModelChoiceField(
        queryset=Service.objects.all(),
        required=False,
        label="Service NetBox",
        help_text="S'il est renseigné, protocole et ports viennent de lui.",
    )
    port_mappings = forms.CharField(
        required=False,
        label="Protocole/port",
        help_text=(
            "Séparés par des virgules, par exemple « tcp/443, tcp/8443 ». "
            "À laisser vide si un service NetBox est choisi."
        ),
    )
    comments = CommentField()

    fieldsets = (
        FieldSet("deployment", "status", "justification", name="Flux"),
        FieldSet(
            "source_prefix",
            "source_ip_range",
            "source_ip_address",
            "source_virtual_machine",
            "source_device",
            "source_virtual_server",
            "source_deployment",
            name="Source — un seul champ",
        ),
        FieldSet(
            "destination_prefix",
            "destination_ip_range",
            "destination_ip_address",
            "destination_virtual_machine",
            "destination_device",
            "destination_virtual_server",
            "destination_deployment",
            name="Destination — un seul champ",
        ),
        FieldSet("service", "port_mappings", name="Ce qui passe"),
        FieldSet("firewall_reference", "description", "tags", name="Suivi"),
    )

    class Meta:
        model = Flow
        fields = (
            "deployment",
            "service",
            "status",
            "justification",
            "firewall_reference",
            "description",
            "comments",
            "tags",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # À la modification, repeupler le bon champ parmi les sept. Sans cela, le
        # formulaire s'ouvrirait vide et un simple enregistrement effacerait
        # l'extrémité existante.
        instance = self.instance
        if instance and instance.pk:
            for cote in ("source", "destination"):
                objet = getattr(instance, cote, None)
                if objet is None:
                    continue
                for suffixe, modele, _libelle in EXTREMITES_SAISIE:
                    if isinstance(objet, modele):
                        self.initial[f"{cote}_{suffixe}"] = objet.pk
                        break
            self.initial["port_mappings"] = ", ".join(instance.port_mappings or [])

    def _extremite(self, cote):
        """L'unique objet saisi pour ce côté, ou une erreur explicite."""
        remplis = [
            (suffixe, self.cleaned_data.get(f"{cote}_{suffixe}"))
            for suffixe, _modele, _libelle in EXTREMITES_SAISIE
            if self.cleaned_data.get(f"{cote}_{suffixe}")
        ]
        if not remplis:
            raise forms.ValidationError("Indiquer exactement un objet.")
        if len(remplis) > 1:
            noms = ", ".join(suffixe for suffixe, _ in remplis)
            raise forms.ValidationError(f"Un seul objet attendu, {len(remplis)} fournis : {noms}.")
        return remplis[0][1]

    def clean(self):
        super().clean()
        erreurs = {}

        for cote in ("source", "destination"):
            try:
                objet = self._extremite(cote)
            except forms.ValidationError as erreur:
                # L'erreur est portée par le PREMIER champ du groupe : NetBox
                # n'affiche pas les erreurs sans champ dans un formulaire en
                # jeux de champs, et elle passerait inaperçue.
                erreurs[f"{cote}_{EXTREMITES_SAISIE[0][0]}"] = erreur.messages
                continue
            setattr(self.instance, f"{cote}_type", ContentType.objects.get_for_model(objet))
            setattr(self.instance, f"{cote}_id", objet.pk)

        brut = (self.cleaned_data.get("port_mappings") or "").strip()
        self.instance.port_mappings = [morceau.strip() for morceau in brut.split(",") if morceau.strip()]

        if erreurs:
            raise forms.ValidationError(erreurs)
        return self.cleaned_data


class FlowFilterForm(NetBoxModelFilterSetForm):
    model = Flow
    fieldsets = (
        FieldSet("q", "filter_id", "tag"),
        FieldSet("deployment_id", "application_id", "environment_id", name="Périmètre"),
        FieldSet("status", "service_id", name="Flux"),
    )

    deployment_id = DynamicModelMultipleChoiceField(
        queryset=Deployment.objects.all(), required=False, label="Déploiement"
    )
    application_id = DynamicModelMultipleChoiceField(
        queryset=Application.objects.all(), required=False, label="Application"
    )
    environment_id = DynamicModelMultipleChoiceField(
        queryset=Environment.objects.all(), required=False, label="Environnement"
    )
    service_id = DynamicModelMultipleChoiceField(
        queryset=Service.objects.all(), required=False, label="Service NetBox"
    )
    status = forms.MultipleChoiceField(
        choices=FlowStatusChoices, required=False, label="État", widget=APISelectMultiple()
    )
