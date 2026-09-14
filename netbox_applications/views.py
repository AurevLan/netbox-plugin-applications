from django.db.models import Count
from django.shortcuts import render
from django.views import View

from extras.ui.panels import CustomFieldsPanel, TagsPanel
from netbox.ui import layout
from netbox.ui.panels import RelatedObjectsPanel
from netbox.views import generic
from utilities.views import GetRelatedModelsMixin, ViewTab, register_model_view

from . import filtersets, forms, models, panels, tables

# --- Référentiels --------------------------------------------------------------
#
# Dix référentiels, cinq vues chacun : chacun feraient cinquante classes quasi
# identiques. La fabrique ci-dessous les produit à partir d'une seule
# description : une correction s'applique alors aux dix d'un coup, et il
# devient impossible d'en oublier un.

_REFERENCES = (
    # (modèle, table, filtre, formulaire)
    (
        models.LifecycleStatus,
        tables.LifecycleStatusTable,
        filtersets.LifecycleStatusFilterSet,
        forms.LifecycleStatusForm,
    ),
    (models.Criticality, tables.CriticalityTable, filtersets.CriticalityFilterSet, forms.CriticalityForm),
    (models.RTO, tables.RTOTable, filtersets.RTOFilterSet, forms.RTOForm),
    (models.RPO, tables.RPOTable, filtersets.RPOFilterSet, forms.RPOForm),
    (models.ServiceHours, tables.ServiceHoursTable, filtersets.ServiceHoursFilterSet, forms.ServiceHoursForm),
    (
        models.DataClassification,
        tables.DataClassificationTable,
        filtersets.DataClassificationFilterSet,
        forms.DataClassificationForm,
    ),
    (
        models.AuthenticationMethod,
        tables.AuthenticationMethodTable,
        filtersets.AuthenticationMethodFilterSet,
        forms.AuthenticationMethodForm,
    ),
    (models.Environment, tables.EnvironmentTable, filtersets.EnvironmentFilterSet, forms.EnvironmentForm),
    (
        models.DeploymentStatus,
        tables.DeploymentStatusTable,
        filtersets.DeploymentStatusFilterSet,
        forms.DeploymentStatusForm,
    ),
    (
        models.MaintenanceWindow,
        tables.MaintenanceWindowTable,
        filtersets.MaintenanceWindowFilterSet,
        forms.MaintenanceWindowForm,
    ),
)


def _build_reference_views(modele, table, filtre, formulaire):
    """Produit les cinq vues d'un référentiel et les expose dans ce module."""
    nom = modele.__name__
    qs = modele.objects.all()

    # La fiche se décrit par une DISPOSITION (NetBox 4.7) : sans elle, la vue
    # cherche un gabarit « netbox_applications/<modele>.html » qui n'existe pas
    # et répond 500. Le panneau « Objets liés » montre au passage combien de
    # fiches emploient la valeur — donc pourquoi sa suppression est refusée.
    disposition = layout.SimpleLayout(
        left_panels=[panels.panneau_pour(modele)(), TagsPanel()],
        right_panels=[RelatedObjectsPanel(), CustomFieldsPanel()],
    )

    def _contexte(self, request, instance):
        return {"related_models": self.get_related_models(request, instance)}

    classes = {
        f"{nom}View": type(
            f"{nom}View",
            (GetRelatedModelsMixin, generic.ObjectView),
            {
                "queryset": qs,
                "layout": disposition,
                # La disposition NE SUFFIT PAS : ObjectView résout toujours un
                # gabarit « <app>/<modele>.html ». Les modèles de l'amont en
                # embarquent un, réduit à « {% extends 'generic/object.html' %} ».
                # On pointe directement le gabarit générique plutôt que d'écrire
                # dix fichiers d'une ligne.
                "template_name": "generic/object.html",
                "get_extra_context": _contexte,
            },
        ),
        f"{nom}ListView": type(
            f"{nom}ListView",
            (generic.ObjectListView,),
            {
                "queryset": qs,
                "table": table,
                "filterset": filtre,
                # Le formulaire de filtres doit connaître SON modèle : NetBox
                # s'en sert pour les filtres enregistrés. Une classe partagée
                # laisse « model » à None et fait échouer toute la liste.
                "filterset_form": type(f"{nom}FilterForm", (forms.ReferenceFilterForm,), {"model": modele}),
            },
        ),
        f"{nom}EditView": type(
            f"{nom}EditView", (generic.ObjectEditView,), {"queryset": qs, "form": formulaire}
        ),
        # La suppression échoue si la valeur est employée : les clés étrangères
        # sont en PROTECT. C'est voulu — supprimer « Critique » ne doit pas
        # vider silencieusement le champ de toutes les applications concernées.
        f"{nom}DeleteView": type(f"{nom}DeleteView", (generic.ObjectDeleteView,), {"queryset": qs}),
        f"{nom}BulkDeleteView": type(
            f"{nom}BulkDeleteView", (generic.BulkDeleteView,), {"queryset": qs, "table": table}
        ),
    }
    globals().update(classes)


for _modele, _table, _filtre, _form in _REFERENCES:
    _build_reference_views(_modele, _table, _filtre, _form)


# --- Parcours guidé -------------------------------------------------------------


class DemarrerView(View):
    """Parcours guidé de création d'une fiche applicative.

    POURQUOI UNE PAGE ET PAS UNE DOCUMENTATION. Le point de blocage d'un
    nouveau venu n'est pas la syntaxe d'un formulaire : c'est de comprendre
    POURQUOI il y a deux objets, et de savoir CE QU'IL LUI RESTE À FAIRE.

    Cette page répond aux deux. Elle explique le partage application /
    déploiement, puis regarde l'état RÉEL de la base : combien d'applications,
    lesquelles n'ont encore aucun déploiement, lesquelles n'ont aucune VM
    rattachée. Elle reste donc utile après la première prise en main — c'est
    une liste de ce qui est resté à moitié fait.
    """

    def get(self, request):
        applications = models.Application.objects.annotate(
            nb_deploiements=Count("deployments", distinct=True)
        )
        # Ce qui est resté en chemin : le vrai apport de la page.
        sans_deploiement = applications.filter(nb_deploiements=0)
        sans_vm = models.Deployment.objects.annotate(nb_vm=Count("virtual_machines", distinct=True)).filter(
            nb_vm=0
        )

        etapes = [
            {
                "numero": 1,
                "titre": "Vérifier les référentiels",
                "faite": models.Environment.objects.exists(),
                "reste": None,
            },
            {
                "numero": 2,
                "titre": "Créer l'application",
                "faite": applications.exists(),
                "reste": None,
            },
            {
                "numero": 3,
                "titre": "Ajouter un déploiement par environnement",
                "faite": applications.exists() and not sans_deploiement.exists(),
                "reste": sans_deploiement,
            },
            {
                "numero": 4,
                "titre": "Rattacher les machines",
                "faite": models.Deployment.objects.exists() and not sans_vm.exists(),
                "reste": sans_vm,
            },
        ]

        return render(
            request,
            "netbox_applications/demarrer.html",
            {
                "etapes": etapes,
                "nb_applications": applications.count(),
                "nb_deploiements": models.Deployment.objects.count(),
                "nb_referentiels": sum(modele.objects.count() for modele in models.REFERENCES),
                "sans_deploiement": sans_deploiement,
                "sans_vm": sans_vm,
            },
        )


# --- Application ---------------------------------------------------------------


class ApplicationView(generic.ObjectView):
    queryset = models.Application.objects.all()


@register_model_view(models.Application, "deployments")
class ApplicationDeploymentsView(generic.ObjectChildrenView):
    """Onglet « Déploiements » sur la fiche d'une application."""

    queryset = models.Application.objects.all()
    child_model = models.Deployment
    table = tables.DeploymentsOnApplicationTable
    filterset = filtersets.DeploymentFilterSet
    template_name = "netbox_applications/application_deployments.html"
    tab = ViewTab(
        label="Déploiements",
        badge=lambda obj: obj.deployments.count(),
        permission="netbox_applications.view_deployment",
    )

    def get_children(self, request, parent):
        return models.Deployment.objects.filter(application=parent)


class ApplicationListView(generic.ObjectListView):
    # Compteur annoté en base : une requête au lieu d'une par ligne.
    queryset = models.Application.objects.annotate(deployment_count=Count("deployments"))
    table = tables.ApplicationTable
    filterset = filtersets.ApplicationFilterSet
    filterset_form = forms.ApplicationFilterForm


class ApplicationEditView(generic.ObjectEditView):
    queryset = models.Application.objects.all()
    form = forms.ApplicationForm


class ApplicationDeleteView(generic.ObjectDeleteView):
    queryset = models.Application.objects.all()


class ApplicationBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Application.objects.annotate(deployment_count=Count("deployments"))
    table = tables.ApplicationTable


# --- Déploiement ---------------------------------------------------------------


class DeploymentView(generic.ObjectView):
    queryset = models.Deployment.objects.all()


class DeploymentListView(generic.ObjectListView):
    queryset = models.Deployment.objects.annotate(vm_count=Count("virtual_machines"))
    table = tables.DeploymentTable
    filterset = filtersets.DeploymentFilterSet
    filterset_form = forms.DeploymentFilterForm


class DeploymentEditView(generic.ObjectEditView):
    queryset = models.Deployment.objects.all()
    form = forms.DeploymentForm


class DeploymentDeleteView(generic.ObjectDeleteView):
    queryset = models.Deployment.objects.all()


class DeploymentBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Deployment.objects.annotate(vm_count=Count("virtual_machines"))
    table = tables.DeploymentTable
