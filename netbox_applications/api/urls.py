from netbox.api.routers import NetBoxRouter

from .. import models
from . import views

app_name = "netbox_applications-api"

router = NetBoxRouter()
router.register("applications", views.ApplicationViewSet)
router.register("deployments", views.DeploymentViewSet)
router.register("virtual-servers", views.VirtualServerViewSet)

# Référentiels — le chemin suit le nom du modèle en minuscules, comme les URL
# de l'interface, pour qu'une même convention serve partout.
for _modele in models.REFERENCES:
    router.register(
        _modele.__name__.lower(),
        getattr(views, f"{_modele.__name__}ViewSet"),
    )

urlpatterns = router.urls
