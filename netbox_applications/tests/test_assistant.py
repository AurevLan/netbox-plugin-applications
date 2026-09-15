"""L'assistant de déclaration : quatre étapes, une transaction.

Ce qui est éprouvé ici n'est pas l'esthétique de la modale, mais deux
promesses : on ne sort pas de l'assistant avec une application orpheline, et un
refus du modèle à la dernière étape n'écrit RIEN.
"""

import html as htmlmod

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from netbox_applications.models import (
    Application,
    AuthenticationMethod,
    Criticality,
    DataClassification,
    Deployment,
    DeploymentStatus,
    Environment,
)

PARASITES = ("functools.partial", "{#", "#}", "{{", "{%")


class AssistantTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("assistant", "a@exemple.invalid", "x")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def _texte(self, reponse):
        """Les apostrophes sont échappées par Django : comparer sur le texte."""
        return htmlmod.unescape(reponse.content.decode())

    def _etape(self, numero, donnees):
        return self.client.post(
            reverse("plugins:netbox_applications:assistant_etape", kwargs={"etape": numero}),
            donnees,
        )

    def _parcours_complet(self, nom="déclarée par l'assistant", **remplacements):
        self._etape(0, {"name": nom, **remplacements.get("identite", {})})
        self._etape(1, remplacements.get("engagements", {}))
        self._etape(2, remplacements.get("securite", {}))
        return self._etape(
            3,
            {
                "environment": Environment.objects.get(slug="production").pk,
                **remplacements.get("deploiement", {}),
            },
        )

    def test_the_first_step_opens(self):
        reponse = self.client.get(reverse("plugins:netbox_applications:assistant"))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Étape 1 sur 4", self._texte(reponse))

    def test_no_template_text_leaks(self):
        html = self.client.get(reverse("plugins:netbox_applications:assistant")).content.decode()
        for motif in PARASITES:
            with self.subTest(motif=motif):
                self.assertNotIn(motif, html)

    def test_the_four_steps_chain(self):
        for numero, donnees in enumerate(
            [{"name": "enchaînement"}, {}, {}],
        ):
            reponse = self._etape(numero, donnees)
            self.assertEqual(reponse.status_code, 200)
            self.assertIn(f"Étape {numero + 2} sur 4", self._texte(reponse))

    def test_it_creates_the_application_and_its_first_deployment(self):
        """La promesse centrale : on ne sort pas avec une application orpheline."""
        reponse = self._parcours_complet(
            engagements={"criticality": Criticality.objects.get(slug="majeure").pk},
            securite={"authentication": AuthenticationMethod.objects.get(slug="keycloak").pk},
            deploiement={"status": DeploymentStatus.objects.get(slug="actif").pk},
        )
        self.assertEqual(reponse.status_code, 204)

        application = Application.objects.get(name="déclarée par l'assistant")
        self.assertRegex(application.application_id, r"^APP-\d{4,}$")
        self.assertEqual(application.criticality.slug, "majeure")
        self.assertEqual(application.authentication.slug, "keycloak")
        self.assertEqual(application.deployments.count(), 1)
        self.assertEqual(application.deployments.first().environment.slug, "production")

    def test_it_sends_the_browser_to_the_new_record(self):
        reponse = self._parcours_complet(nom="redirigée")
        application = Application.objects.get(name="redirigée")
        self.assertEqual(reponse["HX-Redirect"], application.get_absolute_url())

    def test_a_duplicate_name_is_refused_on_the_first_step(self):
        Application.objects.create(name="déjà prise")
        reponse = self._etape(0, {"name": "déjà prise"})
        self.assertIn("porte déjà ce nom", self._texte(reponse))
        self.assertIn("Étape 1 sur 4", self._texte(reponse))

    def test_a_malformed_business_contact_is_refused(self):
        reponse = self._etape(0, {"name": "contact douteux", "business_contact": "Jean Dupont"})
        self.assertIn("Étape 1 sur 4", self._texte(reponse))
        self.assertFalse(Application.objects.filter(name="contact douteux").exists())

    def test_a_refusal_on_the_last_step_writes_nothing(self):
        """Sans transaction, ce refus laisserait l'application orpheline."""
        reponse = self._parcours_complet(
            nom="restreinte",
            securite={"data_classification": DataClassification.objects.get(slug="restreint").pk},
            deploiement={"external_facing": "on"},
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("Étape 4 sur 4", self._texte(reponse))
        self.assertFalse(Application.objects.filter(name="restreinte").exists())
        self.assertFalse(Deployment.objects.filter(application__name="restreinte").exists())

    def test_reopening_the_wizard_starts_from_a_blank_sheet(self):
        """Reprendre une saisie abandonnée sans le dire serait déroutant."""
        self._etape(0, {"name": "abandonnée"})
        reponse = self.client.get(reverse("plugins:netbox_applications:assistant"))
        self.assertNotIn("abandonnée", reponse.content.decode())

    def test_the_button_is_offered_on_the_application_list(self):
        html = self.client.get(reverse("plugins:netbox_applications:application_list")).content.decode()
        self.assertIn("Déclarer une application", html)
        self.assertIn(reverse("plugins:netbox_applications:assistant"), html)
