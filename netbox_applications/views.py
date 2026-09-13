from django.db.models import Count

from netbox.views import generic
from utilities.views import ViewTab, register_model_view

from . import filtersets, forms, models, tables

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
    classes = {
        f"{nom}View": type(f"{nom}View", (generic.ObjectView,), {"queryset": qs}),
        f"{nom}ListView": type(
            f"{nom}ListView",
            (generic.ObjectListView,),
            {
                "queryset": qs,
                "table": table,
                "filterset": filtre,
                "filterset_form": forms.ReferenceFilterForm,
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
