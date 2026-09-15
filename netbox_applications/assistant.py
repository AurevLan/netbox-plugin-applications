"""Assistant de déclaration d'une application — un remplissage guidé, en modale.

POURQUOI UN ASSISTANT PLUTÔT QUE LE FORMULAIRE ORDINAIRE. Le formulaire complet
montre une vingtaine de champs d'un coup, sans dire lesquels comptent ni
pourquoi. Qui découvre la fiche applicative ne sait pas ce qu'est un RPO, ni
qu'il devra créer un déploiement ensuite — et repart avec une application
orpheline. C'est l'oubli le plus fréquent, et la page « Démarrer » ne fait que
le constater après coup.

L'assistant découpe la saisie en quatre temps, explique chaque groupe en une
phrase, et se termine par le PREMIER DÉPLOIEMENT : on ne peut pas en sortir
avec une application qui ne tourne nulle part.

L'ÉTAT VIT DANS LA SESSION, pas dans des champs cachés : un aller-retour
malheureux ne perd pas la saisie, et rien d'incomplet n'atteint la base. Rien
n'est écrit avant la dernière étape, et tout l'est dans une seule transaction.
"""

from django import forms
from django.db import transaction

from tenancy.models import Contact, Tenant
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

CLE_SESSION = "netbox_applications_assistant"


class _EtapeForm(forms.Form):
    """Base commune : des listes ordinaires, pas de sélecteur dynamique.

    Les champs dynamiques de NetBox ont besoin d'une initialisation JavaScript
    que le contenu échangé par HTMX dans une modale ne reçoit pas toujours. Les
    référentiels comptent quatre à sept valeurs : une liste déroulante simple
    est ici plus sûre, et tout aussi lisible.
    """

    titre = ""
    explication = ""


class EtapeIdentite(_EtapeForm):
    titre = "L'application"
    explication = (
        "Ce qui identifie le service, indépendamment de l'endroit où il tourne. Seul le nom est obligatoire."
    )

    name = forms.CharField(label="Nom de l'application", max_length=100)
    client = forms.ModelChoiceField(
        queryset=Tenant.objects.all(), required=False, label="Client", empty_label="— aucun —"
    )
    description = forms.CharField(label="Description", max_length=200, required=False)
    business_contact = forms.EmailField(
        required=False,
        label="Contact métier",
        help_text="Adresse du responsable métier, ou de sa liste de diffusion.",
    )

    def clean_name(self):
        nom = self.cleaned_data["name"]
        if Application.objects.filter(name__iexact=nom).exists():
            raise forms.ValidationError("Une application porte déjà ce nom.")
        return nom


class EtapeEngagements(_EtapeForm):
    titre = "Les engagements"
    explication = (
        "Ce qu'on promet au métier. Ces valeurs décident du traitement en incident "
        "et de la fréquence des sauvegardes : laissez vide plutôt que d'inventer."
    )

    lifecycle_status = forms.ModelChoiceField(
        queryset=LifecycleStatus.objects.all(),
        required=False,
        label="Cycle de vie du service",
        empty_label="— non renseigné —",
    )
    criticality = forms.ModelChoiceField(
        queryset=Criticality.objects.all(),
        required=False,
        label="Criticité métier",
        empty_label="— non renseignée —",
        help_text="Ce que l'arrêt du service coûte à l'organisation.",
    )
    rto = forms.ModelChoiceField(
        queryset=RTO.objects.all(),
        required=False,
        label="RTO — durée d'interruption admise",
        empty_label="— non renseigné —",
        help_text="Combien de temps le service peut rester interrompu.",
    )
    rpo = forms.ModelChoiceField(
        queryset=RPO.objects.all(),
        required=False,
        label="RPO — perte de données admise",
        empty_label="— non renseigné —",
        help_text="Un RPO d'une heure INTERDIT une sauvegarde quotidienne.",
    )
    service_hours = forms.ModelChoiceField(
        queryset=ServiceHours.objects.all(),
        required=False,
        label="Horaires de service",
        empty_label="— non renseignés —",
        help_text="Quand il faut répondre — à ne pas confondre avec la plage de maintenance.",
    )


class EtapeSecurite(_EtapeForm):
    titre = "Sécurité et données"
    explication = (
        "Ce qui décide de l'exposition admise. Une application traitant des données "
        "restreintes ne pourra pas être diffusée à l'externe : le modèle le refusera."
    )

    data_classification = forms.ModelChoiceField(
        queryset=DataClassification.objects.all(),
        required=False,
        label="Classification des données",
        empty_label="— non renseignée —",
    )
    personal_data = forms.BooleanField(required=False, label="Traite des données personnelles (RGPD)")
    authentication = forms.ModelChoiceField(
        queryset=AuthenticationMethod.objects.all(),
        required=False,
        label="Authentification",
        empty_label="— non renseignée —",
        help_text="Une méthode non centralisée signale des comptes échappant à la révocation.",
    )
    technical_contact = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        label="Référent technique",
        empty_label="— aucun —",
    )


class EtapeDeploiement(_EtapeForm):
    titre = "Le premier déploiement"
    explication = (
        "Une application qui ne tourne nulle part ne se surveille pas et ne se retrouve "
        "pas en incident. Déclarez au moins l'environnement où elle existe aujourd'hui ; "
        "les autres s'ajouteront ensuite."
    )

    environment = forms.ModelChoiceField(
        queryset=Environment.objects.all(), label="Environnement", empty_label=None
    )
    status = forms.ModelChoiceField(
        queryset=DeploymentStatus.objects.all(),
        required=False,
        label="État de l'instance",
        empty_label="— non renseigné —",
    )
    maintenance_window = forms.ModelChoiceField(
        queryset=MaintenanceWindow.objects.all(),
        required=False,
        label="Plage de maintenance",
        empty_label="— non renseignée —",
        help_text="Quand une interruption est admise SUR CET ENVIRONNEMENT.",
    )
    external_facing = forms.BooleanField(required=False, label="Diffusé à l'externe")
    access_url = forms.URLField(required=False, label="URL d'accès")
    virtual_machines = forms.ModelMultipleChoiceField(
        queryset=VirtualMachine.objects.all(),
        required=False,
        label="Machines",
        help_text="Ce rattachement répond, en incident, à « cette machine sert à quoi ? ».",
    )


ETAPES = [EtapeIdentite, EtapeEngagements, EtapeSecurite, EtapeDeploiement]


def _valeurs_brutes(form):
    """Réduit les objets à leurs identifiants : une session se sérialise."""
    brutes = {}
    for nom, valeur in form.cleaned_data.items():
        if hasattr(valeur, "pk"):
            brutes[nom] = valeur.pk
        elif hasattr(valeur, "__iter__") and not isinstance(valeur, str):
            brutes[nom] = [objet.pk for objet in valeur]
        else:
            brutes[nom] = valeur
    return brutes


@transaction.atomic
def creer(donnees):
    """Écrit l'application ET son déploiement, ou rien.

    La transaction n'est pas une précaution de principe : sans elle, un refus
    sur le déploiement — exposition externe d'une donnée restreinte, par
    exemple — laisserait exactement l'application orpheline que l'assistant
    existe pour éviter.
    """
    application = Application(
        name=donnees["name"],
        description=donnees.get("description") or "",
        business_contact=donnees.get("business_contact") or "",
        client_id=donnees.get("client"),
        lifecycle_status_id=donnees.get("lifecycle_status"),
        criticality_id=donnees.get("criticality"),
        rto_id=donnees.get("rto"),
        rpo_id=donnees.get("rpo"),
        service_hours_id=donnees.get("service_hours"),
        data_classification_id=donnees.get("data_classification"),
        personal_data=donnees.get("personal_data") or False,
        authentication_id=donnees.get("authentication"),
        technical_contact_id=donnees.get("technical_contact"),
    )
    application.full_clean(exclude=["application_id"])
    application.save()

    deploiement = Deployment(
        application=application,
        environment_id=donnees["environment"],
        status_id=donnees.get("status"),
        maintenance_window_id=donnees.get("maintenance_window"),
        external_facing=donnees.get("external_facing") or False,
        access_url=donnees.get("access_url") or "",
    )
    deploiement.full_clean()
    deploiement.save()
    if donnees.get("virtual_machines"):
        deploiement.virtual_machines.set(donnees["virtual_machines"])

    return application
