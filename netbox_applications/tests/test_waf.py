"""Pare-feu applicatif et serveur virtuel.

Ce qui est éprouvé : qu'une fiche ne puisse pas se contredire, que le préfixe
soit CALCULÉ et non stocké, et que la question qui motive tout ce champ —
« qu'est-ce qui est exposé sans filtrage ? » — trouve sa réponse.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from ipam.models import IPAddress, Prefix

from netbox_applications.filtersets import DeploymentFilterSet
from netbox_applications.models import (
    Application,
    Deployment,
    Environment,
    VirtualServer,
)


class VirtualServerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prefixe = Prefix.objects.create(prefix="10.90.0.0/24")
        cls.ip = IPAddress.objects.create(address="10.90.0.10/24")
        cls.vs = VirtualServer.objects.create(name="vs-essai", ip_address=cls.ip, port=443)

    def test_it_reads_as_name_address_and_port(self):
        self.assertEqual(str(self.vs), "vs-essai (10.90.0.10:443)")

    def test_it_reads_without_a_port(self):
        sans_port = VirtualServer.objects.create(
            name="vs-sans-port", ip_address=IPAddress.objects.create(address="10.90.0.11/24")
        )
        self.assertEqual(str(sans_port), "vs-sans-port (10.90.0.11)")

    def test_str_survives_an_address_still_held_as_text(self):
        """Un __str__ qui lève casse les journaux et les messages d'erreur.

        « address » n'est un objet réseau qu'une fois relu de la base ; en
        mémoire, juste après construction, c'est une chaîne.
        """
        en_memoire = VirtualServer(name="vs-memoire", ip_address=IPAddress(address="10.90.0.12/24"))
        self.assertIn("vs-memoire", str(en_memoire))

    def test_the_prefix_is_computed_not_stored(self):
        self.assertEqual(self.vs.prefix, self.prefixe)
        self.assertNotIn("prefix", [f.name for f in VirtualServer._meta.get_fields() if f.concrete])

    def test_the_most_specific_prefix_wins(self):
        """Plusieurs préfixes peuvent contenir une adresse ; le plus étroit décrit son segment."""
        etroit = Prefix.objects.create(prefix="10.90.0.8/29")
        self.assertEqual(self.vs.prefix, etroit)

    def test_an_address_in_use_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.ip.delete()


class WafSurLeDeploiementTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vs = VirtualServer.objects.create(
            name="vs-waf", ip_address=IPAddress.objects.create(address="10.91.0.10/24")
        )
        cls.app = Application.objects.create(name="protégée")

    def _deploiement(self, slug="production", **champs):
        return Deployment(application=self.app, environment=Environment.objects.get(slug=slug), **champs)

    def test_a_virtual_server_without_waf_is_refused(self):
        """Nommer le moyen d'un filtrage qui n'a pas lieu est une fiche qui se contredit."""
        deploiement = self._deploiement(waf_enabled=False, waf_virtual_server=self.vs)
        with self.assertRaises(ValidationError) as leve:
            deploiement.full_clean()
        self.assertIn("waf_enabled", leve.exception.message_dict)

    def test_a_virtual_server_with_waf_is_accepted(self):
        self._deploiement(waf_enabled=True, waf_virtual_server=self.vs).full_clean()

    def test_the_waf_may_be_enabled_without_a_virtual_server(self):
        """Le serveur virtuel est FACULTATIF : on peut savoir qu'on est protégé sans savoir par quoi."""
        self._deploiement(waf_enabled=True).full_clean()

    def test_the_waf_lives_on_the_deployment_not_the_application(self):
        """La production est souvent protégée quand la recette ne l'est pas."""
        champs = [f.name for f in Deployment._meta.get_fields() if f.concrete]
        self.assertIn("waf_enabled", champs)
        self.assertNotIn("waf_enabled", [f.name for f in Application._meta.get_fields() if f.concrete])

    def test_a_virtual_server_in_use_cannot_be_deleted(self):
        deploiement = self._deploiement(waf_enabled=True, waf_virtual_server=self.vs)
        deploiement.save()
        with self.assertRaises(ProtectedError):
            self.vs.delete()


class ExposeSansWafTest(TestCase):
    """La question qui justifie tout ce champ, et qu'aucun filtre simple ne pose."""

    @classmethod
    def setUpTestData(cls):
        app = Application.objects.create(name="exposition")
        vs = VirtualServer.objects.create(
            name="vs-expose", ip_address=IPAddress.objects.create(address="10.92.0.10/24")
        )
        cls.nu = Deployment.objects.create(
            application=app,
            environment=Environment.objects.get(slug="production"),
            external_facing=True,
        )
        cls.protege = Deployment.objects.create(
            application=app,
            environment=Environment.objects.get(slug="recette"),
            external_facing=True,
            waf_enabled=True,
            waf_virtual_server=vs,
        )
        cls.interne = Deployment.objects.create(
            application=app,
            environment=Environment.objects.get(slug="preproduction"),
            external_facing=False,
        )

    def _filtre(self, **params):
        return set(DeploymentFilterSet(params, queryset=Deployment.objects.all()).qs)

    def test_it_finds_what_is_exposed_without_filtering(self):
        self.assertEqual(self._filtre(expose_sans_waf=True), {self.nu})

    def test_it_finds_what_is_exposed_and_protected(self):
        self.assertEqual(self._filtre(expose_sans_waf=False), {self.protege})

    def test_an_internal_deployment_is_in_neither_answer(self):
        """Non exposé n'est pas « exposé sans WAF » : le filtre ne doit pas l'attraper."""
        self.assertNotIn(self.interne, self._filtre(expose_sans_waf=True))
        self.assertNotIn(self.interne, self._filtre(expose_sans_waf=False))


class PagesDuServeurVirtuelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("waf", "w@exemple.invalid", "x")
        cls.vs = VirtualServer.objects.create(
            name="vs-pages",
            ip_address=IPAddress.objects.create(address="10.93.0.10/24"),
            port=8443,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_every_page_answers(self):
        pages = [
            reverse("plugins:netbox_applications:virtualserver_list"),
            reverse("plugins:netbox_applications:virtualserver_add"),
            self.vs.get_absolute_url(),
            self.vs.get_absolute_url() + "edit/",
        ]
        for url in pages:
            with self.subTest(url=url):
                reponse = self.client.get(url)
                self.assertIn(reponse.status_code, (200, 302))
                if reponse.status_code == 200:
                    html = reponse.content.decode()
                    for motif in ("functools.partial", "{#", "#}", "{{", "{%"):
                        self.assertNotIn(motif, html)

    def test_the_record_shows_the_computed_prefix(self):
        Prefix.objects.create(prefix="10.93.0.0/24")
        html = self.client.get(self.vs.get_absolute_url()).content.decode()
        self.assertIn("10.93.0.0/24", html)

    def test_it_is_reachable_from_the_menu(self):
        from netbox_applications.navigation import catalogue

        liens = [item.link for item in catalogue]
        self.assertIn("plugins:netbox_applications:virtualserver_list", liens)
