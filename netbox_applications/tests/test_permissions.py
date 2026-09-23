"""Les vues écrites à la main doivent refuser ce que NetBox refuse.

POURQUOI CES TESTS EXISTENT. Un audit du 2026-09-23 a montré qu'un compte
dépourvu de TOUTE permission pouvait créer une application et son déploiement
par l'assistant — alors que l'API et la liste lui répondaient 403. Les vues
génériques de NetBox portent une garde ; « django.views.View » n'en porte
aucune, et l'assistant en héritait donc rien.

ATTENTION AUX PERMISSIONS DJANGO. NetBox n'utilise PAS « user.user_permissions » :
il évalue ses propres objets « ObjectPermission ». Un test qui accorde une
permission Django accorde en réalité zéro droit — et conclut à tort que la vue
est trop stricte.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from users.models import ObjectPermission

from core.models import ObjectType

from netbox_applications.models import Application, Environment


class GardeDesVuesEcritesAMainTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Aucun mot de passe : « force_login » s'en passe, et un mot de passe
        # en dur dans un test est une alerte de sécurité qu'on finit par ignorer.
        cls.user = get_user_model().objects.create_user("sans-droits")
        cls.demarrer = reverse("plugins:netbox_applications:demarrer")
        cls.assistant = reverse("plugins:netbox_applications:assistant")

    def setUp(self):
        self.client = Client(raise_request_exception=False)
        self.client.force_login(self.user)

    def _accorder(self, *actions):
        """Accorde des droits À LA MANIÈRE DE NETBOX, seule qui compte ici."""
        ObjectPermission.objects.filter(name="essai").delete()
        permission = ObjectPermission.objects.create(name="essai", actions=list(actions), enabled=True)
        permission.object_types.set(ObjectType.objects.filter(app_label="netbox_applications"))
        permission.users.add(self.user)

    def _parcours_complet(self, nom):
        self.client.post(f"{self.assistant}0/", {"name": nom})
        self.client.post(f"{self.assistant}1/", {})
        self.client.post(f"{self.assistant}2/", {})
        return self.client.post(
            f"{self.assistant}3/",
            {"environment": Environment.objects.get(slug="production").pk},
        )

    # --- Sans aucun droit -----------------------------------------------------

    def test_the_start_page_is_refused_without_view_permission(self):
        """Elle nomme les applications du catalogue : c'est une lecture."""
        self.assertEqual(self.client.get(self.demarrer).status_code, 403)

    def test_the_wizard_is_refused_without_add_permission(self):
        self.assertEqual(self.client.get(self.assistant).status_code, 403)

    def test_nothing_is_written_without_permission(self):
        """Le défaut trouvé à l'audit : l'assistant écrivait sans aucun droit."""
        avant = Application.objects.count()
        reponse = self._parcours_complet("tentative sans droits")
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(Application.objects.count(), avant)
        self.assertFalse(Application.objects.filter(name="tentative sans droits").exists())

    # --- Avec les droits qu'il faut ------------------------------------------

    def test_reading_is_allowed_with_view_permission(self):
        self._accorder("view")
        self.assertEqual(self.client.get(self.demarrer).status_code, 200)

    def test_the_wizard_works_with_add_permission(self):
        self._accorder("view", "add")
        reponse = self._parcours_complet("créée avec droits")
        self.assertEqual(reponse.status_code, 204)
        self.assertTrue(Application.objects.filter(name="créée avec droits").exists())

    # --- Le cas intermédiaire, celui qui décide ------------------------------

    def test_read_only_may_look_but_not_declare(self):
        """Lire le catalogue ne donne pas le droit d'y ajouter."""
        self._accorder("view")
        self.assertEqual(self.client.get(self.demarrer).status_code, 200)
        self.assertEqual(self.client.get(self.assistant).status_code, 403)

    def test_a_read_only_account_cannot_write_either(self):
        self._accorder("view")
        avant = Application.objects.count()
        self.assertEqual(self._parcours_complet("par un lecteur").status_code, 403)
        self.assertEqual(Application.objects.count(), avant)


class ToutesLesRoutesOntUneGardeTest(TestCase):
    """Aucune route du plugin ne doit répondre sans vérifier de permission.

    Ce test attrape la PROCHAINE vue écrite à la main, pas seulement les deux
    qui ont été corrigées.
    """

    def test_every_plugin_view_enforces_a_permission(self):
        from django.urls import get_resolver

        def parcourir(motifs, prefixe=""):
            for motif in motifs:
                if hasattr(motif, "url_patterns"):
                    yield from parcourir(motif.url_patterns, prefixe + str(motif.pattern))
                else:
                    yield prefixe + str(motif.pattern), motif.callback

        sans_garde = []
        for chemin, vue in parcourir(get_resolver().url_patterns):
            if "netbox_applications" not in getattr(vue, "__module__", ""):
                continue
            classe = getattr(vue, "view_class", None)
            if classe is None:
                continue
            if not hasattr(classe, "get_required_permission"):
                sans_garde.append(f"{chemin} → {classe.__name__}")

        self.assertEqual(sans_garde, [], "Vues sans garde de permission")
