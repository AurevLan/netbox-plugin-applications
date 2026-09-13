from django.db.models import Count

from netbox.views import generic
from utilities.views import ViewTab, register_model_view

from . import filtersets, forms, models, tables

# --- Application -------------------------------------------------------------


class ApplicationView(generic.ObjectView):
    queryset = models.Application.objects.all()


@register_model_view(models.Application, "deployments")
class ApplicationDeploymentsView(generic.ObjectChildrenView):
    """Onglet « Déploiements » sur la fiche d'une application.

    Un onglet plutôt qu'un simple tableau dans la page : le nombre de
    déploiements se lit alors sans ouvrir la fiche.
    """

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


# --- Déploiement -------------------------------------------------------------


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
