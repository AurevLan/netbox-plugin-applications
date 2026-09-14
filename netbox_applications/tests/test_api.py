"""L'API doit accepter d'ÉCRIRE ce qu'elle sait lire.

Rattacher une machine à un déploiement répondait HTTP 500 : le champ était
déclaré comme sérialiseur imbriqué, lisible mais pas inscriptible. Personne ne
l'a vu parce que l'interface graphique, elle, passe par un formulaire Django —
et qu'aucun test n'écrivait par l'API.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from virtualization.models import Cluster, ClusterType, VirtualMachine

from netbox_applications.models import (
    Application,
    AuthenticationMethod,
    Deployment,
    Environment,
)


class EcritureApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("api", "api@exemple.invalid", "x")
        cls.app = Application.objects.create(name="pilotée par l'API")
        cls.deployment = Deployment.objects.create(
            application=cls.app, environment=Environment.objects.get(slug="production")
        )
        type_grappe = ClusterType.objects.create(name="essai", slug="essai")
        grappe = Cluster.objects.create(name="grappe d'essai", type=type_grappe)
        cls.vm = VirtualMachine.objects.create(name="vm-essai", cluster=grappe)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def _patch(self, chemin, corps):
        return self.client.patch(chemin, data=json.dumps(corps), content_type="application/json")

    def test_a_machine_can_be_attached_to_a_deployment(self):
        reponse = self._patch(
            f"/api/plugins/applications/deployments/{self.deployment.pk}/",
            {"virtual_machines": [self.vm.pk]},
        )
        self.assertEqual(reponse.status_code, 200, reponse.content[:300])
        self.assertEqual(list(self.deployment.virtual_machines.all()), [self.vm])

    def test_the_attachment_reads_back_as_a_full_object(self):
        """En écriture un identifiant, en lecture l'objet : c'est l'usage NetBox."""
        self._patch(
            f"/api/plugins/applications/deployments/{self.deployment.pk}/",
            {"virtual_machines": [self.vm.pk]},
        )
        donnees = json.loads(
            self.client.get(f"/api/plugins/applications/deployments/{self.deployment.pk}/").content
        )
        self.assertEqual([m["name"] for m in donnees["virtual_machines"]], ["vm-essai"])

    def test_the_relation_reads_from_the_machine_too(self):
        self._patch(
            f"/api/plugins/applications/deployments/{self.deployment.pk}/",
            {"virtual_machines": [self.vm.pk]},
        )
        self.assertEqual(list(self.vm.deployments.all()), [self.deployment])

    def test_a_deployment_can_be_created_with_its_machines(self):
        reponse = self.client.post(
            "/api/plugins/applications/deployments/",
            data=json.dumps(
                {
                    "application": self.app.pk,
                    "environment": Environment.objects.get(slug="recette").pk,
                    "virtual_machines": [self.vm.pk],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 201, reponse.content[:300])
        self.assertEqual(json.loads(reponse.content)["virtual_machines"][0]["name"], "vm-essai")

    def test_an_application_can_be_created_with_its_references(self):
        keycloak = AuthenticationMethod.objects.get(slug="keycloak")
        reponse = self.client.post(
            "/api/plugins/applications/applications/",
            data=json.dumps({"name": "créée par l'API", "authentication": keycloak.pk}),
            content_type="application/json",
        )
        self.assertEqual(reponse.status_code, 201, reponse.content[:300])
        self.assertRegex(json.loads(reponse.content)["application_id"], r"^APP-\d{4,}$")

    def test_an_invalid_business_contact_is_refused(self):
        """Le format imposé doit l'être aussi par l'API, pas seulement en interface."""
        reponse = self._patch(
            f"/api/plugins/applications/applications/{self.app.pk}/",
            {"business_contact": "pas une adresse"},
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("business_contact", json.loads(reponse.content))
