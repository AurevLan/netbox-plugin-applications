from netbox.api.routers import NetBoxRouter

from . import views

app_name = "netbox_applications-api"

router = NetBoxRouter()
router.register("applications", views.ApplicationViewSet)
router.register("deployments", views.DeploymentViewSet)

urlpatterns = router.urls
