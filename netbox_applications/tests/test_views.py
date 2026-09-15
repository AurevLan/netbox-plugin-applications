"""Atteignabilité : toute page du plugin doit s'afficher.

POURQUOI CE TEST EXISTE. La version 0.4.0 a livré VINGT pages en erreur 500
alors que ses gabarits se rendaient parfaitement : le défaut était dans les
vues et le routage, qu'aucun rendu isolé de gabarit n'emprunte.

Un contrôle doit suivre le chemin de l'utilisateur, pas un raccourci qui lui
ressemble.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from netbox_applications.models import REFERENCES, Application, Deployment, Environment

# Texte qui ne doit JAMAIS apparaître dans une page rendue. Un commentaire
# Django « {# … #} » n'est un commentaire que sur UNE ligne : au-delà, il
# s'affiche tel quel. Aucun lint ne le voit.
PARASITES = ("functools.partial", "{#", "#}", "{{", "{%")


class ToutesLesPagesTest(TestCase):
    """Liste, création, fiche et édition, pour les douze modèles."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("essai", "essai@exemple.invalid", "x")
        for modele in REFERENCES:
            modele.objects.get_or_create(slug="essai", defaults={"name": "essai"})
        cls.app = Application.objects.create(name="essai-pages")
        Deployment.objects.create(application=cls.app, environment=Environment.objects.first())

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def _pages(self):
        for modele in (*REFERENCES, Application, Deployment):
            nom = modele._meta.model_name
            objet = modele.objects.first()
            yield reverse(f"plugins:netbox_applications:{nom}_list")
            yield reverse(f"plugins:netbox_applications:{nom}_add")
            yield objet.get_absolute_url()
            yield objet.get_absolute_url() + "edit/"

    def test_every_page_answers(self):
        for url in self._pages():
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (200, 302))

    def test_no_template_text_leaks_into_the_page(self):
        for url in self._pages():
            reponse = self.client.get(url)
            if reponse.status_code != 200:
                continue
            html = reponse.content.decode()
            for motif in PARASITES:
                with self.subTest(url=url, motif=motif):
                    self.assertNotIn(motif, html)

    def test_the_count_of_pages_is_the_expected_one(self):
        """Douze modèles, quatre pages chacun. Un modèle oublié se verrait ici."""
        self.assertEqual(len(list(self._pages())), (len(REFERENCES) + 2) * 4)


class PanneauxTest(TestCase):
    """Les attributs d'un référentiel doivent être VISIBLES sur sa fiche.

    Un champ ajouté au modèle mais absent de l'affichage est une donnée qui
    n'atteint jamais son destinataire.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("panneau", "p@exemple.invalid", "x")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_specific_attributes_are_displayed(self):
        from netbox_applications.models import RTO, AuthenticationMethod, MaintenanceWindow

        attendus = {
            AuthenticationMethod: ("Centralisée", "Rang", "Slug"),
            RTO: ("Durée (minutes)",),
            MaintenanceWindow: ("Début", "Fin", "Interruption admise"),
        }
        for modele, libelles in attendus.items():
            html = self.client.get(modele.objects.first().get_absolute_url()).content.decode()
            for libelle in libelles:
                with self.subTest(modele=modele.__name__, libelle=libelle):
                    self.assertIn(libelle, html)


class FiltresAtteignablesTest(TestCase):
    """Un filtre absent des « fieldsets » existe mais reste introuvable.

    Ce défaut a été livré DEUX fois : en 0.1.0 pour les filtres du catalogue,
    puis en 0.4.0 pour les filtres par attribut. D'où ce test.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("filtre", "f@exemple.invalid", "x")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_attribute_filters_appear_in_the_panel(self):
        attendus = {
            "/plugins/applications/applications/": ("Service rendu", "Authentification centralisée"),
            "/plugins/applications/deployments/": ("En production",),
        }
        for url, libelles in attendus.items():
            html = self.client.get(url).content.decode()
            for libelle in libelles:
                with self.subTest(url=url, libelle=libelle):
                    self.assertIn(libelle, html)


class ParcoursGuideTest(TestCase):
    """Le parcours guidé doit dire VRAI sur l'état de la base.

    Une page d'accueil qui affiche « tout est fait » alors qu'il reste du
    travail est pire qu'une absence de page : elle fait croire que c'est fini.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("parcours", "p@exemple.invalid", "x")
        cls.url = reverse("plugins:netbox_applications:demarrer")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_the_page_answers(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_no_template_text_leaks(self):
        html = self.client.get(self.url).content.decode()
        for motif in PARASITES:
            with self.subTest(motif=motif):
                self.assertNotIn(motif, html)

    def test_it_explains_the_split_between_the_two_objects(self):
        html = self.client.get(self.url).content.decode()
        for attendu in ("le service", "une instance", "RTO", "RPO"):
            with self.subTest(attendu=attendu):
                self.assertIn(attendu, html)

    def test_it_names_an_application_left_without_deployment(self):
        orpheline = Application.objects.create(name="restée en chemin")
        html = self.client.get(self.url).content.decode()
        self.assertIn("restée en chemin", html)
        self.assertIn(orpheline.get_absolute_url(), html)

    def test_a_complete_application_is_not_flagged(self):
        """Signaler une application complète serait un faux positif permanent."""
        complete = Application.objects.create(name="complète")
        for environnement in Environment.objects.all():
            Deployment.objects.create(application=complete, environment=environnement)
        html = self.client.get(self.url).content.decode()
        debut = html.index("Sans aucun déploiement") if "Sans aucun déploiement" in html else None
        if debut is not None:
            self.assertNotIn("complète", html[debut : debut + 600])

    def test_it_names_a_machine_attached_to_nothing(self):
        """Le manque doit se voir des deux côtés (ADR-0018)."""
        from virtualization.models import Cluster, ClusterType, VirtualMachine

        type_grappe = ClusterType.objects.create(name="orpheline", slug="orpheline")
        grappe = Cluster.objects.create(name="grappe orpheline", type=type_grappe)
        machine = VirtualMachine.objects.create(name="vm-sans-emploi", cluster=grappe)
        html = self.client.get(self.url).content.decode()
        self.assertIn("vm-sans-emploi", html)
        self.assertIn(machine.get_absolute_url(), html)

    def test_an_attached_machine_is_not_flagged(self):
        from virtualization.models import Cluster, ClusterType, VirtualMachine

        type_grappe = ClusterType.objects.create(name="employée", slug="employee")
        grappe = Cluster.objects.create(name="grappe employée", type=type_grappe)
        machine = VirtualMachine.objects.create(name="vm-au-travail", cluster=grappe)
        deploiement = Deployment.objects.create(
            application=Application.objects.create(name="avec machine"),
            environment=Environment.objects.first(),
        )
        deploiement.virtual_machines.add(machine)
        html = self.client.get(self.url).content.decode()
        self.assertNotIn("vm-au-travail", html)

    def test_the_counts_match_the_database(self):
        Application.objects.create(name="comptée")
        html = self.client.get(self.url).content.decode()
        self.assertIn(f">{Application.objects.count()}</div>", html)
