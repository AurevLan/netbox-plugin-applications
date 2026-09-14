"""Règles que le modèle doit rendre impossibles à enfreindre."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

# ProtectedError vit dans « django.db.models », pas dans « django.db ».
from django.db.models import ProtectedError
from django.test import TestCase

from netbox_applications.models import (
    Application,
    AuthenticationMethod,
    Criticality,
    DataClassification,
    Deployment,
    DeploymentStatus,
    Environment,
    LifecycleStatus,
)


class ApplicationIdentifierTest(TestCase):
    """L'identifiant lisible est attribué seul, et n'est jamais redemandé."""

    def test_identifier_is_assigned_on_creation(self):
        app = Application.objects.create(name="sans identifiant")
        self.assertRegex(app.application_id, r"^APP-\d{4,}$")

    def test_identifier_is_stable_across_saves(self):
        app = Application.objects.create(name="stable")
        premier = app.application_id
        app.description = "modifiée"
        app.save()
        app.refresh_from_db()
        self.assertEqual(app.application_id, premier)

    def test_identifiers_are_distinct(self):
        premiers = {Application.objects.create(name=f"app-{i}").application_id for i in range(5)}
        self.assertEqual(len(premiers), 5)


class DeploymentUniquenessTest(TestCase):
    """Une application n'a qu'UNE fiche par environnement.

    Sans cette contrainte, deux fiches « production » divergeraient en silence.
    """

    @classmethod
    def setUpTestData(cls):
        cls.app = Application.objects.create(name="unicite")
        cls.production = Environment.objects.get(slug="production")
        cls.recette = Environment.objects.get(slug="recette")

    def test_second_deployment_in_same_environment_is_refused(self):
        Deployment.objects.create(application=self.app, environment=self.production)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Deployment.objects.create(application=self.app, environment=self.production)

    def test_another_environment_is_accepted(self):
        Deployment.objects.create(application=self.app, environment=self.production)
        Deployment.objects.create(application=self.app, environment=self.recette)
        self.assertEqual(self.app.deployments.count(), 2)


class ExternalExposureTest(TestCase):
    """Exposer à l'externe une donnée restreinte est refusé.

    Ce garde-fou a été MUET pendant deux versions : il comparait la
    classification à la chaîne « restreint », devenue un objet. D'où ce test.
    """

    @classmethod
    def setUpTestData(cls):
        cls.app = Application.objects.create(name="exposition")
        cls.deployment = Deployment.objects.create(
            application=cls.app, environment=Environment.objects.get(slug="recette")
        )

    def _classer(self, slug):
        Application.objects.filter(pk=self.app.pk).update(
            data_classification=DataClassification.objects.get(slug=slug)
        )
        self.deployment.refresh_from_db()
        self.deployment.external_facing = True

    def test_restricted_data_cannot_be_exposed(self):
        self._classer("restreint")
        with self.assertRaises(ValidationError) as leve:
            self.deployment.full_clean()
        self.assertIn("external_facing", leve.exception.message_dict)

    def test_internal_data_may_be_exposed(self):
        self._classer("interne")
        self.deployment.full_clean()

    def test_rule_reads_the_level_not_the_name(self):
        """Renommer « Restreint » ne doit pas désarmer la règle."""
        restreint = DataClassification.objects.get(slug="restreint")
        restreint.name = "Diffusion nominative"
        restreint.save()
        self._classer("restreint")
        with self.assertRaises(ValidationError):
            self.deployment.full_clean()


class LifecycleCoherenceTest(TestCase):
    """Cohérence entre cycle de vie du SERVICE et état d'une INSTANCE.

    La règle vaut dans les deux sens : sans la réciproque, il suffirait de
    passer par l'autre bout pour créer la contradiction.
    """

    @classmethod
    def setUpTestData(cls):
        cls.retire = LifecycleStatus.objects.get(slug="retire")
        cls.en_service = LifecycleStatus.objects.get(slug="en-service")
        cls.actif = DeploymentStatus.objects.get(slug="actif")
        cls.planifie = DeploymentStatus.objects.get(slug="planifie")
        cls.production = Environment.objects.get(slug="production")
        cls.recette = Environment.objects.get(slug="recette")

    def setUp(self):
        self.app = Application.objects.create(name="coherence", lifecycle_status=self.en_service)
        self.prod = Deployment.objects.create(
            application=self.app, environment=self.production, status=self.actif
        )

    def test_service_cannot_be_retired_while_production_runs(self):
        self.app.lifecycle_status = self.retire
        with self.assertRaises(ValidationError) as leve:
            self.app.full_clean()
        self.assertIn("lifecycle_status", leve.exception.message_dict)

    def test_production_cannot_run_for_a_retired_service(self):
        Application.objects.filter(pk=self.app.pk).update(lifecycle_status=self.retire)
        self.prod.refresh_from_db()
        with self.assertRaises(ValidationError) as leve:
            self.prod.full_clean()
        self.assertIn("status", leve.exception.message_dict)

    def test_message_names_the_environment_at_fault(self):
        self.app.lifecycle_status = self.retire
        with self.assertRaises(ValidationError) as leve:
            self.app.full_clean()
        self.assertIn(str(self.production), leve.exception.message_dict["lifecycle_status"][0])

    def test_outside_production_nothing_is_constrained(self):
        """Une recette peut survivre au retrait, le temps d'une réversibilité."""
        Application.objects.filter(pk=self.app.pk).update(lifecycle_status=self.retire)
        recette = Deployment.objects.create(application=self.app, environment=self.recette, status=self.actif)
        recette.full_clean()

    def test_a_planned_instance_does_not_block_anything(self):
        """Un service rendu peut avoir une instance encore planifiée."""
        self.prod.status = self.planifie
        self.prod.save()
        Application.objects.filter(pk=self.app.pk).update(lifecycle_status=self.retire)
        self.prod.refresh_from_db()
        self.prod.full_clean()


class BusinessContactTest(TestCase):
    """Champ libre, mais au format d'une adresse."""

    @classmethod
    def setUpTestData(cls):
        cls.app = Application.objects.create(name="contact")

    def test_an_address_is_accepted(self):
        for valeur in ("rh@exemple.fr", "liste-rh@exemple.fr", ""):
            with self.subTest(valeur=valeur):
                self.app.business_contact = valeur
                self.app.full_clean()

    def test_anything_else_is_refused(self):
        for valeur in ("Jean Dupont", "rh@exemple", "rh exemple.fr"):
            with self.subTest(valeur=valeur):
                self.app.business_contact = valeur
                with self.assertRaises(ValidationError) as leve:
                    self.app.full_clean()
                self.assertIn("business_contact", leve.exception.message_dict)


class ReferenceProtectionTest(TestCase):
    """Supprimer une valeur employée viderait des fiches en silence."""

    def test_a_used_value_cannot_be_deleted(self):
        keycloak = AuthenticationMethod.objects.get(slug="keycloak")
        Application.objects.create(name="protégée", authentication=keycloak)
        # PROTECT, et non SET_NULL : la suppression doit échouer, pas vider
        # silencieusement le champ des fiches concernées.
        with transaction.atomic(), self.assertRaises(ProtectedError):
            keycloak.delete()
        self.assertTrue(AuthenticationMethod.objects.filter(slug="keycloak").exists())

    def test_an_unused_value_can_be_deleted(self):
        jetable = AuthenticationMethod.objects.create(name="jetable", slug="jetable")
        jetable.delete()
        self.assertFalse(AuthenticationMethod.objects.filter(slug="jetable").exists())


class ReferenceSeedTest(TestCase):
    """Ce que la migration a semé, et qui doit le rester."""

    def test_colours_are_hexadecimal(self):
        """Une migration de données n'appelle pas full_clean() : elle écrit sans valider."""
        from netbox_applications.models import REFERENCES

        invalides = [
            f"{modele.__name__}/{objet.slug}={objet.color!r}"
            for modele in REFERENCES
            for objet in modele.objects.all()
            if not (len(objet.color or "") == 6 and set(objet.color.lower()) <= set("0123456789abcdef"))
        ]
        self.assertEqual(invalides, [])

    def test_attributes_carry_meaning(self):
        self.assertFalse(AuthenticationMethod.objects.get(slug="locale").is_centralized)
        self.assertTrue(AuthenticationMethod.objects.get(slug="keycloak").is_centralized)
        self.assertTrue(LifecycleStatus.objects.get(slug="en-service").is_operational)
        self.assertFalse(LifecycleStatus.objects.get(slug="retire").is_operational)
        self.assertTrue(Environment.objects.get(slug="production").is_production)

    def test_recovery_objectives_are_comparable(self):
        """Le libellé ne se trie pas ; les minutes, si."""
        from netbox_applications.models import RTO

        self.assertEqual(RTO.objects.get(slug="4h").minutes, 240)
        self.assertLess(RTO.objects.get(slug="1h").minutes, RTO.objects.get(slug="24h").minutes)

    def test_references_are_ordered_by_weight(self):
        rangs = list(Criticality.objects.values_list("weight", flat=True))
        self.assertEqual(rangs, sorted(rangs))
