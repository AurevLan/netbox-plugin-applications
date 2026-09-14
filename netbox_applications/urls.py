from django.urls import include, path

from utilities.urls import get_model_urls

from . import models, views


def _reference_urls(modele):
    """Les six routes d'un référentiel, dérivées de son nom.

    Le segment d'URL et le nom de route suivent la convention de NetBox :
    le nom du modèle en minuscules.
    """
    n = modele.__name__.lower()
    return [
        path(f"{n}/", getattr(views, f"{modele.__name__}ListView").as_view(), name=f"{n}_list"),
        path(f"{n}/add/", getattr(views, f"{modele.__name__}EditView").as_view(), name=f"{n}_add"),
        path(
            f"{n}/delete/",
            getattr(views, f"{modele.__name__}BulkDeleteView").as_view(),
            name=f"{n}_bulk_delete",
        ),
        path(f"{n}/<int:pk>/", getattr(views, f"{modele.__name__}View").as_view(), name=n),
        path(
            f"{n}/<int:pk>/edit/",
            getattr(views, f"{modele.__name__}EditView").as_view(),
            name=f"{n}_edit",
        ),
        path(
            f"{n}/<int:pk>/delete/",
            getattr(views, f"{modele.__name__}DeleteView").as_view(),
            name=f"{n}_delete",
        ),
        path(f"{n}/<int:pk>/", include(get_model_urls("netbox_applications", n))),
    ]


urlpatterns = [
    # Parcours guidé — première entrée du menu, première page qu'on ouvre.
    path("demarrer/", views.DemarrerView.as_view(), name="demarrer"),
    # Applications
    path("applications/", views.ApplicationListView.as_view(), name="application_list"),
    path("applications/add/", views.ApplicationEditView.as_view(), name="application_add"),
    path(
        "applications/delete/",
        views.ApplicationBulkDeleteView.as_view(),
        name="application_bulk_delete",
    ),
    path("applications/<int:pk>/", views.ApplicationView.as_view(), name="application"),
    path("applications/<int:pk>/edit/", views.ApplicationEditView.as_view(), name="application_edit"),
    path(
        "applications/<int:pk>/delete/",
        views.ApplicationDeleteView.as_view(),
        name="application_delete",
    ),
    path("applications/<int:pk>/", include(get_model_urls("netbox_applications", "application"))),
    # Déploiements
    path("deployments/", views.DeploymentListView.as_view(), name="deployment_list"),
    path("deployments/add/", views.DeploymentEditView.as_view(), name="deployment_add"),
    path(
        "deployments/delete/",
        views.DeploymentBulkDeleteView.as_view(),
        name="deployment_bulk_delete",
    ),
    path("deployments/<int:pk>/", views.DeploymentView.as_view(), name="deployment"),
    path("deployments/<int:pk>/edit/", views.DeploymentEditView.as_view(), name="deployment_edit"),
    path(
        "deployments/<int:pk>/delete/",
        views.DeploymentDeleteView.as_view(),
        name="deployment_delete",
    ),
    path("deployments/<int:pk>/", include(get_model_urls("netbox_applications", "deployment"))),
]

# Référentiels
for _modele in models.REFERENCES:
    urlpatterns += _reference_urls(_modele)
