"""Flux et matrice.

CE QUI EST ÉPROUVÉ ICI, et pourquoi chacun compte :

  - qu'un flux ne puisse pas porter DEUX vérités sur ses ports ;
  - que les adresses soient RÉSOLUES et non stockées, pour les sept types
    d'extrémité acceptés — c'est ce qui rend la matrice actionnable ;
  - que la matrice signale CE QUI MANQUE, et pas seulement ce qu'on a saisi ;
  - que l'export CSV et l'affichage viennent du MÊME calcul, puisque c'est
    l'export qui part à l'équipe réseau.

La leçon de la version 0.4.0 s'applique : un gabarit qui se rend ne prouve rien
sur la vue qui l'appelle. Les onglets sont donc atteints par leur URL.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from netaddr import IPNetwork

from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from ipam.models import IPAddress, IPRange, Prefix, Service
from virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface

from netbox_applications import matrice
from netbox_applications.choices import FlowStatusChoices
from netbox_applications.forms import FlowForm
from netbox_applications.models import Application, Deployment, Environment, Flow, VirtualServer
from netbox_applications.models.flow import adresses_de, noms_dns_de, valider_mappings


def _ct(objet):
    return ContentType.objects.get_for_model(objet)


class SocleMixin:
    """Un déploiement, une VM qui expose un service, un serveur virtuel."""

    @classmethod
    def poser_le_socle(cls):
        cls.prefixe_clients = Prefix.objects.create(prefix="10.70.0.0/24")
        cls.app = Application.objects.create(name="facturation")
        cls.deploiement = Deployment.objects.create(
            application=cls.app, environment=Environment.objects.get(slug="production")
        )

        type_grappe = ClusterType.objects.create(name="essai", slug="essai")
        cls.grappe = Cluster.objects.create(name="grappe-essai", type=type_grappe)
        cls.vm = VirtualMachine.objects.create(name="web-prod-01", cluster=cls.grappe)
        cls.interface = VMInterface.objects.create(virtual_machine=cls.vm, name="eth0")
        cls.ip_vm = IPAddress.objects.create(address="10.70.0.20/24", dns_name="web-prod-01.exemple.invalid")
        cls.ip_vm.assigned_object = cls.interface
        cls.ip_vm.save()
        cls.vm.primary_ip4 = cls.ip_vm
        cls.vm.save()
        cls.deploiement.virtual_machines.add(cls.vm)

        cls.service = Service.objects.create(parent=cls.vm, name="https-interne", port_mappings=["tcp/8443"])
        cls.vs = VirtualServer.objects.create(
            name="vs-facturation",
            ip_address=IPAddress.objects.create(address="10.70.0.10/24"),
            port=443,
        )

    @classmethod
    def flux(cls, **champs):
        """Un flux par défaut : préfixe client vers la VM, ports du service.

        Fabrique de CLASSE et non d'instance : « setUpTestData » n'a que la
        classe sous la main, et une fabrique d'instance l'obligerait à se passer
        elle-même en argument — un détour qu'on relit mal six mois plus tard.
        """
        defauts = {
            "deployment": cls.deploiement,
            "source_type": _ct(cls.prefixe_clients),
            "source_id": cls.prefixe_clients.pk,
            "destination_type": _ct(cls.vm),
            "destination_id": cls.vm.pk,
            "service": cls.service,
        }
        return Flow(**{**defauts, **champs})


class PortsEtVeriteUniqueTest(SocleMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()

    def test_ports_come_from_the_service_when_there_is_one(self):
        """Une seule vérité : les ports du service, jamais recopiés dans le flux."""
        flux = self.flux()
        self.assertEqual(flux.mappings, ["tcp/8443"])

    def test_a_service_and_hand_written_ports_together_are_refused(self):
        flux = self.flux(port_mappings=["tcp/443"])
        with self.assertRaises(ValidationError) as leve:
            flux.full_clean()
        self.assertIn("port_mappings", leve.exception.message_dict)

    def test_neither_service_nor_ports_is_refused(self):
        """Un flux sans port n'est pas une règle, c'est une intention."""
        flux = self.flux(service=None)
        with self.assertRaises(ValidationError) as leve:
            flux.full_clean()
        self.assertIn("port_mappings", leve.exception.message_dict)

    def test_hand_written_ports_alone_are_accepted(self):
        self.flux(service=None, port_mappings=["tcp/443"]).full_clean()

    def test_the_netbox_format_is_reused_as_is(self):
        self.assertEqual(valider_mappings(["TCP/0443"]), ["tcp/443"])

    def test_an_unknown_protocol_is_refused(self):
        with self.assertRaises(ValidationError):
            valider_mappings(["icmp/0"])

    def test_a_port_out_of_bounds_is_refused(self):
        with self.assertRaises(ValidationError):
            valider_mappings(["tcp/70000"])

    def test_a_malformed_pair_is_refused(self):
        with self.assertRaises(ValidationError):
            valider_mappings(["443"])


class CoherenceTest(SocleMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()

    def test_the_same_object_on_both_ends_is_refused(self):
        flux = self.flux(
            source_type=_ct(self.vm), source_id=self.vm.pk, service=None, port_mappings=["tcp/22"]
        )
        with self.assertRaises(ValidationError) as leve:
            flux.full_clean()
        self.assertIn("destination_id", leve.exception.message_dict)

    def test_a_service_of_another_machine_is_refused(self):
        """Emprunter les ports d'une machine qui n'est pas la destination rend la matrice fausse."""
        autre = VirtualMachine.objects.create(name="autre-01", cluster=self.grappe)
        ailleurs = Service.objects.create(parent=autre, name="ailleurs", port_mappings=["tcp/9999"])
        flux = self.flux(service=ailleurs)
        with self.assertRaises(ValidationError) as leve:
            flux.full_clean()
        self.assertIn("service", leve.exception.message_dict)

    def test_a_service_of_a_vm_of_the_destination_deployment_is_accepted(self):
        """La destination peut être le DÉPLOIEMENT : le service d'une de ses VM reste cohérent."""
        autre_app = Application.objects.create(name="consommatrice")
        source = Deployment.objects.create(
            application=autre_app, environment=Environment.objects.get(slug="recette")
        )
        self.flux(
            source_type=_ct(source),
            source_id=source.pk,
            destination_type=_ct(self.deploiement),
            destination_id=self.deploiement.pk,
        ).full_clean()

    def test_the_same_flow_cannot_be_declared_twice(self):
        self.flux().save()
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.flux().save()

    def test_a_service_in_use_cannot_be_deleted(self):
        self.flux().save()
        with self.assertRaises(ProtectedError):
            self.service.delete()

    def test_it_reads_as_source_destination_and_ports(self):
        flux = self.flux()
        self.assertIn("10.70.0.0/24", str(flux))
        self.assertIn("tcp/8443", str(flux))


class ResolutionDesAdressesTest(SocleMixin, TestCase):
    """Les sept types d'extrémité doivent se résoudre en adresses.

    C'est ce qui sépare une matrice lisible d'une matrice actionnable : une
    règle de pare-feu ne se pose pas avec « la VM web-prod-01 ».
    """

    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()

    def test_a_prefix_resolves_to_itself(self):
        self.assertEqual(adresses_de(self.prefixe_clients), ["10.70.0.0/24"])

    def test_a_range_resolves_to_its_bounds(self):
        # Des objets réseau, et non des chaînes : « IPRange.save » calcule sa
        # taille depuis « .ip », qu'une chaîne ne porte pas.
        plage = IPRange.objects.create(
            start_address=IPNetwork("10.70.0.50/24"), end_address=IPNetwork("10.70.0.60/24")
        )
        self.assertEqual(adresses_de(plage), ["10.70.0.50-10.70.0.60"])

    def test_a_range_still_held_as_text_resolves_too(self):
        """Le piège déjà payé sur le serveur virtuel : une adresse en mémoire est une chaîne."""
        en_memoire = IPRange(start_address="10.70.0.70/24", end_address="10.70.0.80/24")
        self.assertEqual(adresses_de(en_memoire), ["10.70.0.70-10.70.0.80"])

    def test_an_address_resolves_to_itself(self):
        self.assertEqual(adresses_de(self.ip_vm), ["10.70.0.20/24"])

    def test_a_vm_resolves_to_its_primary_address(self):
        self.assertEqual(adresses_de(self.vm), ["10.70.0.20/24"])

    def test_a_vm_without_primary_address_falls_back_to_its_interfaces(self):
        """Une VM provisionnée mais pas configurée est exactement ce cas."""
        nue = VirtualMachine.objects.create(name="sans-primaire", cluster=self.grappe)
        interface = VMInterface.objects.create(virtual_machine=nue, name="eth0")
        ip = IPAddress.objects.create(address="10.70.0.30/24")
        ip.assigned_object = interface
        ip.save()
        self.assertEqual(adresses_de(nue), ["10.70.0.30/24"])

    def test_a_device_resolves_like_a_vm(self):
        site = Site.objects.create(name="site-essai", slug="site-essai")
        fabricant = Manufacturer.objects.create(name="fab", slug="fab")
        gabarit = DeviceType.objects.create(manufacturer=fabricant, model="m", slug="m")
        role = DeviceRole.objects.create(name="role", slug="role")
        equipement = Device.objects.create(name="pare-feu-01", site=site, device_type=gabarit, role=role)
        self.assertEqual(adresses_de(equipement), [])

    def test_a_virtual_server_resolves_to_its_listening_address(self):
        self.assertEqual(adresses_de(self.vs), ["10.70.0.10/24"])

    def test_a_deployment_resolves_to_the_addresses_of_its_machines(self):
        """Un flux inter-applicatif se déclare une fois, et suit le parc."""
        self.assertEqual(adresses_de(self.deploiement), ["10.70.0.20/24"])

    def test_nothing_resolves_to_nothing(self):
        self.assertEqual(adresses_de(None), [])

    def test_dns_comes_from_netbox_and_is_never_invented(self):
        self.assertEqual(noms_dns_de(self.ip_vm), ["web-prod-01.exemple.invalid"])
        self.assertEqual(noms_dns_de(self.vm), ["web-prod-01.exemple.invalid"])
        self.assertEqual(noms_dns_de(self.vs), [])


class MatriceTest(SocleMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()

    def test_a_declared_flow_appears(self):
        self.flux(justification="Les clients consultent leurs factures.").save()
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        declarees = [ligne for ligne in lignes if ligne.est_declare]
        self.assertEqual(len(declarees), 1)
        self.assertEqual(declarees[0].adresses_source, ("10.70.0.0/24",))
        self.assertEqual(declarees[0].adresses_destination, ("10.70.0.20/24",))

    def test_an_exposed_service_without_any_source_is_reported_as_missing(self):
        """La ligne la plus intéressante de la matrice : un port ouvert sans origine connue."""
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        manquantes = [ligne for ligne in lignes if ligne.manque]
        self.assertEqual(len(manquantes), 1)
        self.assertIn("tcp/8443", manquantes[0].ports)

    def test_a_declared_flow_removes_the_missing_line(self):
        self.flux().save()
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        self.assertEqual([ligne for ligne in lignes if ligne.manque], [])

    def test_external_exposure_behind_a_waf_implies_a_flow_from_the_outside(self):
        self.deploiement.external_facing = True
        self.deploiement.waf_enabled = True
        self.deploiement.waf_virtual_server = self.vs
        self.deploiement.save()
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        depuis_internet = [ligne for ligne in lignes if ligne.source == matrice.INTERNET]
        self.assertEqual(len(depuis_internet), 1)
        self.assertEqual(depuis_internet[0].origine, matrice.DEDUIT)
        self.assertEqual(depuis_internet[0].ports, "tcp/443")

    def test_the_virtual_server_implies_a_flow_towards_what_it_serves(self):
        self.deploiement.waf_enabled = True
        self.deploiement.waf_virtual_server = self.vs
        self.deploiement.save()
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        deduites = [ligne for ligne in lignes if ligne.origine == matrice.DEDUIT]
        self.assertTrue(any("tcp/8443" in ligne.ports for ligne in deduites))

    def test_external_exposure_without_an_entry_point_is_reported(self):
        self.deploiement.external_facing = True
        self.deploiement.save()
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        self.assertTrue(any(ligne.manque and ligne.source == matrice.INTERNET for ligne in lignes))

    def test_nothing_declared_and_nothing_exposed_gives_an_empty_matrix(self):
        vide = Deployment.objects.create(
            application=self.app, environment=Environment.objects.get(slug="recette")
        )
        self.assertEqual(matrice.matrice_du_deploiement(vide), [])

    def test_an_application_matrix_covers_every_environment(self):
        recette = Deployment.objects.create(
            application=self.app, environment=Environment.objects.get(slug="recette")
        )
        recette.virtual_machines.add(self.vm)
        lignes = matrice.matrice_de_l_application(self.app)
        deploiements = {ligne.deploiement for ligne in lignes}
        self.assertEqual(deploiements, {self.deploiement, recette})

    def test_the_summary_counts_by_origin(self):
        self.flux(status=FlowStatusChoices.OUVERT).save()
        resume = matrice.compte_par_origine(matrice.matrice_du_deploiement(self.deploiement))
        self.assertEqual(resume["declare"], 1)
        self.assertEqual(resume["en_vigueur"], 1)
        self.assertEqual(resume["a_declarer"], 0)

    def test_only_open_flows_count_as_in_force(self):
        """Une matrice qui confond demandé et ouvert ne décrit ni l'un ni l'autre."""
        self.flux(status=FlowStatusChoices.DEMANDE).save()
        resume = matrice.compte_par_origine(matrice.matrice_du_deploiement(self.deploiement))
        self.assertEqual(resume["en_vigueur"], 0)

    def test_the_csv_carries_a_header_and_one_line_per_row(self):
        self.flux().save()
        lignes = matrice.matrice_du_deploiement(self.deploiement)
        csv = matrice.en_csv(lignes)
        self.assertEqual(csv.splitlines()[0].split(";")[0], "application")
        self.assertEqual(len(csv.strip().splitlines()), len(lignes) + 1)

    def test_the_csv_separates_addresses_with_spaces_not_commas(self):
        """Un CSV dont les cellules contiennent des virgules s'ouvre de travers."""
        self.deploiement.external_facing = True
        self.deploiement.save()
        csv = matrice.en_csv(matrice.matrice_du_deploiement(self.deploiement))
        for ligne in csv.splitlines()[1:]:
            self.assertEqual(len(ligne.split(";")), len(matrice.COLONNES))


class PagesDesFluxTest(SocleMixin, TestCase):
    """Toute page doit s'afficher — la leçon des vingt erreurs 500 de la 0.4.0."""

    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()
        cls.user = get_user_model().objects.create_superuser("flux", "flux@exemple.invalid", "x")
        cls.objet = cls.flux()
        cls.objet.save()

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def _pages(self):
        yield reverse("plugins:netbox_applications:flow_list")
        yield reverse("plugins:netbox_applications:flow_add")
        yield self.objet.get_absolute_url()
        yield self.objet.get_absolute_url() + "edit/"
        yield self.deploiement.get_absolute_url() + "matrice/"
        yield self.app.get_absolute_url() + "matrice/"

    def test_every_page_answers(self):
        for url in self._pages():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_no_template_text_leaks_into_the_page(self):
        for url in self._pages():
            contenu = self.client.get(url).content.decode()
            for parasite in ("{#", "#}", "{%", "functools.partial"):
                with self.subTest(url=url, parasite=parasite):
                    self.assertNotIn(parasite, contenu)

    def test_the_matrix_tab_shows_the_declared_flow(self):
        contenu = self.client.get(self.deploiement.get_absolute_url() + "matrice/").content.decode()
        self.assertIn("10.70.0.0/24", contenu)
        self.assertIn("tcp/8443", contenu)

    def test_the_csv_export_comes_from_the_same_view(self):
        reponse = self.client.get(self.deploiement.get_absolute_url() + "matrice/?export=csv")
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("text/csv", reponse["Content-Type"])
        self.assertIn("attachment", reponse["Content-Disposition"])
        self.assertIn("10.70.0.0/24", reponse.content.decode())

    def test_the_application_export_covers_every_environment(self):
        reponse = self.client.get(self.app.get_absolute_url() + "matrice/?export=csv")
        self.assertIn("Production", reponse.content.decode())


class ApiDesFluxTest(SocleMixin, TestCase):
    """L'API doit rendre les adresses RÉSOLUES.

    Un consommateur qui alimente un pare-feu a besoin des adresses, pas d'un
    identifiant de type de contenu. Les calculer côté serveur évite que chaque
    consommateur réimplémente la résolution, et se trompe différemment.
    """

    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()
        cls.objet = cls.flux()
        cls.objet.save()
        cls.user = get_user_model().objects.create_superuser("api", "api@exemple.invalid", "x")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_the_list_answers(self):
        url = reverse("plugins-api:netbox_applications-api:flow-list")
        reponse = self.client.get(url, HTTP_ACCEPT="application/json")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json()["count"], 1)

    def test_the_detail_carries_resolved_addresses_and_ports(self):
        url = reverse("plugins-api:netbox_applications-api:flow-detail", args=[self.objet.pk])
        charge = self.client.get(url, HTTP_ACCEPT="application/json").json()
        self.assertEqual(charge["adresses_source"], ["10.70.0.0/24"])
        self.assertEqual(charge["adresses_destination"], ["10.70.0.20/24"])
        self.assertEqual(charge["mappings"], ["tcp/8443"])
        self.assertEqual(charge["source"], "10.70.0.0/24")


class FormulaireDesFluxTest(SocleMixin, TestCase):
    """Le formulaire, là où l'utilisateur se heurte aux erreurs.

    Les extrémités sont saisies par TYPE, un champ par type d'objet. Le prix de
    ce choix est qu'il faut garantir qu'un seul se remplisse : sans ce contrôle,
    une saisie dans deux champs produirait un flux dont l'extrémité dépendrait
    de l'ordre de lecture du formulaire.
    """

    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()

    def _donnees(self, **champs):
        defauts = {
            "deployment": self.deploiement.pk,
            "status": FlowStatusChoices.DEMANDE,
            "source_prefix": self.prefixe_clients.pk,
            "destination_virtual_machine": self.vm.pk,
            "service": self.service.pk,
        }
        return {**defauts, **champs}

    def test_a_valid_form_sets_both_generic_references(self):
        formulaire = FlowForm(data=self._donnees())
        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        flux = formulaire.save()
        self.assertEqual(flux.source, self.prefixe_clients)
        self.assertEqual(flux.destination, self.vm)

    def test_no_source_at_all_is_refused(self):
        formulaire = FlowForm(data=self._donnees(source_prefix=""))
        self.assertFalse(formulaire.is_valid())
        self.assertIn("source_prefix", formulaire.errors)

    def test_two_sources_are_refused(self):
        formulaire = FlowForm(data=self._donnees(source_ip_address=self.ip_vm.pk))
        self.assertFalse(formulaire.is_valid())
        self.assertIn("source_prefix", formulaire.errors)

    def test_ports_are_read_from_a_comma_separated_list(self):
        formulaire = FlowForm(data=self._donnees(service="", port_mappings="tcp/443, tcp/8443"))
        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        self.assertEqual(formulaire.save().port_mappings, ["tcp/443", "tcp/8443"])

    def test_a_malformed_port_is_reported_by_the_form(self):
        formulaire = FlowForm(data=self._donnees(service="", port_mappings="443"))
        self.assertFalse(formulaire.is_valid())
        self.assertIn("port_mappings", formulaire.errors)

    def test_editing_repopulates_the_right_field_among_the_seven(self):
        """Sans cela, un simple enregistrement effacerait l'extrémité existante."""
        flux = self.flux()
        flux.save()
        formulaire = FlowForm(instance=flux)
        self.assertEqual(formulaire.initial["source_prefix"], self.prefixe_clients.pk)
        self.assertEqual(formulaire.initial["destination_virtual_machine"], self.vm.pk)

    def test_editing_shows_hand_written_ports_back(self):
        flux = self.flux(service=None, port_mappings=["tcp/22"])
        flux.save()
        self.assertEqual(FlowForm(instance=flux).initial["port_mappings"], "tcp/22")


class EtatsDesFluxTest(SocleMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.poser_le_socle()

    def test_an_open_flow_describes_the_network_as_it_is(self):
        self.assertTrue(self.flux(status=FlowStatusChoices.OUVERT).en_vigueur)

    def test_a_requested_flow_describes_an_intention(self):
        """« À retirer » reste visible : le supprimer effacerait le travail restant."""
        for etat in (
            FlowStatusChoices.DEMANDE,
            FlowStatusChoices.REFUSE,
            FlowStatusChoices.A_RETIRER,
            FlowStatusChoices.FERME,
        ):
            with self.subTest(etat=etat):
                self.assertFalse(self.flux(status=etat).en_vigueur)

    def test_each_state_carries_a_colour(self):
        # Les entrées portent TROIS valeurs : clé, libellé, couleur.
        for etat, *_reste in FlowStatusChoices.CHOICES:
            with self.subTest(etat=etat):
                self.assertTrue(self.flux(status=etat).get_status_color())

    def test_a_deleted_endpoint_does_not_break_the_display(self):
        """Un __str__ qui lève casse les journaux et les messages d'erreur."""
        flux = self.flux(source_type=_ct(self.prefixe_clients), source_id=999999)
        self.assertIn("source supprimée", flux.libelle_source)
        self.assertEqual(flux.adresses_source, [])
