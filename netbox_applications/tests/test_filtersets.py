"""Les filtres doivent filtrer — et NetBox ignore ceux qu'il ne connaît pas.

Un paramètre inconnu ne produit pas d'erreur : la collection entière est
renvoyée avec un HTTP 200. Une faute de frappe donne donc une réponse FAUSSE,
jamais un échec. Ces tests vérifient que chaque filtre RÉDUIT réellement.
"""

from django.test import TestCase

from netbox_applications.filtersets import ApplicationFilterSet, DeploymentFilterSet
from netbox_applications.models import (
    Application,
    AuthenticationMethod,
    Deployment,
    DeploymentStatus,
    Environment,
    LifecycleStatus,
)


class ApplicationFiltersTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        keycloak = AuthenticationMethod.objects.get(slug="keycloak")
        locale = AuthenticationMethod.objects.get(slug="locale")
        en_service = LifecycleStatus.objects.get(slug="en-service")
        en_projet = LifecycleStatus.objects.get(slug="en-projet")

        cls.centralisee = Application.objects.create(
            name="centralisée",
            authentication=keycloak,
            lifecycle_status=en_service,
            business_contact="equipe@direction-rh.exemple.fr",
        )
        cls.locale = Application.objects.create(
            name="comptes propres",
            authentication=locale,
            lifecycle_status=en_projet,
            business_contact="autre@ailleurs.exemple.fr",
        )

    def _filtre(self, **params):
        return set(ApplicationFilterSet(params, queryset=Application.objects.all()).qs)

    def test_authentication_centralized_reads_the_attribute(self):
        """La question ne dépend pas du NOM de la valeur."""
        self.assertEqual(self._filtre(authentication_centralized=False), {self.locale})
        self.assertEqual(self._filtre(authentication_centralized=True), {self.centralisee})

    def test_renaming_a_value_does_not_break_the_filter(self):
        locale = AuthenticationMethod.objects.get(slug="locale")
        locale.name = "Comptes applicatifs"
        locale.save()
        self.assertEqual(self._filtre(authentication_centralized=False), {self.locale})

    def test_operational_reads_the_attribute(self):
        self.assertEqual(self._filtre(operational=True), {self.centralisee})

    def test_business_contact_matches_partially(self):
        """On cherche par service, pas par adresse exacte."""
        self.assertEqual(self._filtre(business_contact="direction-rh"), {self.centralisee})

    def test_an_unknown_value_returns_nothing(self):
        """Un filtre qui ne réduit jamais serait indiscernable d'un filtre ignoré."""
        self.assertEqual(self._filtre(business_contact="personne-ici"), set())


class DeploymentFiltersTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        app = Application.objects.create(name="filtres déploiement")
        actif = DeploymentStatus.objects.get(slug="actif")
        cls.production = Deployment.objects.create(
            application=app, environment=Environment.objects.get(slug="production"), status=actif
        )
        cls.recette = Deployment.objects.create(
            application=app, environment=Environment.objects.get(slug="recette"), status=actif
        )

    def _filtre(self, **params):
        return set(DeploymentFilterSet(params, queryset=Deployment.objects.all()).qs)

    def test_production_reads_the_attribute(self):
        self.assertEqual(self._filtre(production=True), {self.production})
        self.assertEqual(self._filtre(production=False), {self.recette})
