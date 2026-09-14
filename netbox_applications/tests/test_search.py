"""La recherche globale doit trouver les objets du plugin.

Sans index, « APP-0001 » et « Keycloak » renvoyaient ZÉRO résultat, sans que
rien ne l'indique. Pour une CMDB, la barre de recherche est la première porte
d'entrée.
"""

from django.test import TestCase

from netbox.search import get_indexer
from netbox.search.backends import search_backend

from netbox_applications.models import (
    REFERENCES,
    Application,
    AuthenticationMethod,
    Deployment,
    Environment,
)


class IndexationTest(TestCase):
    def test_every_model_has_an_index(self):
        for modele in (Application, Deployment, *REFERENCES):
            with self.subTest(modele=modele.__name__):
                self.assertIsNotNone(get_indexer(modele))

    def test_the_identifier_outranks_the_name(self):
        """Qui cherche « APP-0001 » cherche cette fiche-là.

        Le poids se lit à l'envers : plus il est faible, plus le champ prime.
        """
        champs = dict(get_indexer(Application).fields)
        self.assertLess(champs["application_id"], champs["name"])


class RechercheTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.app = Application.objects.create(name="portail des essais")
        cls.authent = AuthenticationMethod.objects.create(name="essai-authent", slug="essai-authent")
        cls.deploiement = Deployment.objects.create(
            application=cls.app,
            environment=Environment.objects.first(),
            access_url="https://essai-deploiement.invalid",
        )
        for modele in (Application, Deployment, AuthenticationMethod):
            search_backend.cache(modele.objects.all())

    def _trouve(self, terme):
        return {type(resultat.object) for resultat in search_backend.search(terme)}

    def test_an_application_is_found_by_its_identifier(self):
        self.assertIn(Application, self._trouve(self.app.application_id))

    def test_an_application_is_found_by_its_name(self):
        self.assertIn(Application, self._trouve("portail des essais"))

    def test_a_reference_value_is_found(self):
        self.assertIn(AuthenticationMethod, self._trouve("essai-authent"))

    def test_a_deployment_is_found_by_its_url(self):
        """Ce qu'on a en main quand on tombe sur une adresse inconnue."""
        self.assertIn(Deployment, self._trouve("essai-deploiement"))

    def test_an_absent_term_finds_nothing(self):
        self.assertEqual(self._trouve("terme-absent-du-catalogue"), set())
