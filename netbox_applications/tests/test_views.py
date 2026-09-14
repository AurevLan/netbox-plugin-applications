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
