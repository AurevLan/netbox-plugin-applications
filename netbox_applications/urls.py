from django.urls import include, path

from utilities.urls import get_model_urls

from . import views

urlpatterns = (
    # Applications
    path("applications/", views.ApplicationListView.as_view(), name="application_list"),
    path("applications/add/", views.ApplicationEditView.as_view(), name="application_add"),
    path("applications/delete/", views.ApplicationBulkDeleteView.as_view(), name="application_bulk_delete"),
    path("applications/<int:pk>/", views.ApplicationView.as_view(), name="application"),
    path("applications/<int:pk>/edit/", views.ApplicationEditView.as_view(), name="application_edit"),
    path("applications/<int:pk>/delete/", views.ApplicationDeleteView.as_view(), name="application_delete"),
    # Onglets enregistrés (déploiements) et vues fournies par NetBox
    # (journal de modifications, entrées de journal).
    path("applications/<int:pk>/", include(get_model_urls("netbox_applications", "application"))),
    # Déploiements
    path("deployments/", views.DeploymentListView.as_view(), name="deployment_list"),
    path("deployments/add/", views.DeploymentEditView.as_view(), name="deployment_add"),
    path("deployments/delete/", views.DeploymentBulkDeleteView.as_view(), name="deployment_bulk_delete"),
    path("deployments/<int:pk>/", views.DeploymentView.as_view(), name="deployment"),
    path("deployments/<int:pk>/edit/", views.DeploymentEditView.as_view(), name="deployment_edit"),
    path("deployments/<int:pk>/delete/", views.DeploymentDeleteView.as_view(), name="deployment_delete"),
    path("deployments/<int:pk>/", include(get_model_urls("netbox_applications", "deployment"))),
)
