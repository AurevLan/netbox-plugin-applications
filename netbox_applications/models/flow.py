"""Flux — qui a le droit d'atteindre quoi, pour un déploiement donné.

CE QUI MANQUAIT. NetBox décrit déjà très bien le côté DESTINATION d'un flux :
l'objet `Service` natif porte un nom, un protocole et des ports, rattachés à une
VM ou à un équipement. Il ne dit rien de la SOURCE — et sans source, on n'a pas
une matrice de flux, on a une liste de ports ouverts.

Ce modèle apporte l'autre moitié, et rien de plus : il n'invente ni adresse, ni
service, ni zone. Les deux extrémités d'un flux sont de VRAIS OBJETS NETBOX,
désignés par référence générique — un préfixe, une plage, une adresse, une VM,
un équipement, un serveur virtuel, ou le déploiement d'une autre application.

POURQUOI PAS UN CHAMP TEXTE POUR LA SOURCE. Un texte libre se dédouble à la
première faute de frappe : « LAN admin », « lan-admin » et « Postes admin »
deviennent trois sources là où il n'y en a qu'une, et la matrice cesse d'être
exploitable. Pire, un texte ne se résout pas en adresses : il faut alors qu'un
humain traduise chaque ligne avant de toucher au pare-feu. Un préfixe NetBox se
résout tout seul, et change de valeur partout à la fois quand le réseau est
redécoupé.

LE RATTACHEMENT AU DÉPLOIEMENT EST LA CLÉ. Un flux appartient à un déploiement,
donc à un couple application et environnement : c'est ce qui permet d'obtenir la
matrice d'une application en recette sans la mélanger avec celle de sa
production, alors que ce sont les mêmes services sur des adresses différentes.
"""

import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from ipam.choices import ServiceProtocolChoices
from netbox.models import NetBoxModel

from ..choices import FlowStatusChoices

# Les modèles qu'une extrémité de flux peut désigner.
#
# Volontairement limité, et chacun pour une raison :
#   prefix / iprange   un segment, une plage — la forme d'une « zone »
#   ipaddress          un hôte précis, et il porte son nom DNS
#   virtualmachine     une machine du parc, sans avoir à nommer son adresse
#   device             un équipement physique (sauvegarde, supervision…)
#   virtualserver      le point d'entrée devant une instance
#   deployment         UNE AUTRE APPLICATION — le flux inter-applicatif, qui ne
#                      se déduit d'aucune donnée existante et qu'il faut déclarer
EXTREMITES = (
    ("ipam", "prefix"),
    ("ipam", "iprange"),
    ("ipam", "ipaddress"),
    ("virtualization", "virtualmachine"),
    ("dcim", "device"),
    ("netbox_applications", "virtualserver"),
    ("netbox_applications", "deployment"),
)

EXTREMITES_Q = models.Q()
for _app, _modele in EXTREMITES:
    EXTREMITES_Q |= models.Q(app_label=_app, model=_modele)

_PROTOCOLES = [choix[0] for choix in ServiceProtocolChoices.CHOICES]
_MOTIF_MAPPING = re.compile(rf"^({'|'.join(_PROTOCOLES)})/(\d{{1,5}})$")


def valider_mappings(mappings):
    """Contrôle des paires « protocole/port », au format de NetBox.

    Le format est celui de `Service.port_mappings` depuis NetBox 4.7 —
    `['tcp/443', 'udp/53']`. Le reprendre à l'identique n'est pas de la
    coquetterie : un flux dont les ports s'écrivent autrement que ceux de
    l'objet `Service` qu'il prolonge obligerait à convertir d'un format à
    l'autre, et c'est dans ces conversions que les erreurs se logent.
    """
    propres = []
    for mapping in mappings:
        trouve = _MOTIF_MAPPING.match((mapping or "").strip().lower())
        if not trouve:
            raise ValidationError(
                f"« {mapping} » n'est pas une paire protocole/port valide. "
                f"Attendu : {', '.join(_PROTOCOLES)} suivi de « / » et d'un port, par exemple « tcp/443 »."
            )
        port = int(trouve.group(2))
        if not 1 <= port <= 65535:
            raise ValidationError(f"Le port {port} de « {mapping} » est hors des bornes 1-65535.")
        propres.append(f"{trouve.group(1)}/{port}")
    return propres


def mappings_du_service(service):
    """Les paires protocole/port d'un objet `Service`, quelle que soit la version.

    NetBox 4.7 les stocke dans `port_mappings` (`['tcp/443']`). Les versions
    antérieures portaient `protocol` et `ports` séparément. Le plugin annonce
    4.5 comme plancher : lire l'un OU l'autre selon ce qui existe évite de
    dépendre d'un renommage interne, et de casser la compatibilité annoncée à la
    première montée de version de l'hôte.
    """
    mappings = getattr(service, "port_mappings", None)
    if mappings:
        return list(mappings)
    protocole = getattr(service, "protocol", "") or ""
    ports = getattr(service, "ports", None) or []
    return [f"{protocole}/{port}" for port in ports]


def _sans_masque(valeur):
    """L'adresse seule, qu'elle vienne de la base ou d'une instance en mémoire.

    Le même piège que pour le serveur virtuel, et il s'est reproduit ici :
    « address » est un objet réseau une fois relu de la base, mais une simple
    chaîne tant que l'instance vient d'être construite. Lire « .ip » sans
    précaution lève sur la seconde forme — et c'est celle que produit un test,
    donc celle qui échoue en dernier, longtemps après l'écriture du code.
    """
    return str(getattr(valeur, "ip", None) or str(valeur).split("/")[0])


def adresses_de(objet):
    """Les adresses que désigne un objet NetBox, telles qu'un pare-feu les attend.

    C'EST CE QUI REND LA MATRICE ACTIONNABLE. Une ligne qui dit « la VM
    web-prod-01 » est lisible par un humain ; une règle de pare-feu a besoin de
    son adresse. La résolution se fait ici, à la lecture, et jamais en base :
    recopier l'adresse dans le flux la figerait au jour de la saisie.
    """
    if objet is None:
        return []

    # Préfixe, plage, adresse : l'objet EST l'adresse.
    if hasattr(objet, "prefix") and not hasattr(objet, "ip_address"):
        return [str(objet.prefix)]
    if hasattr(objet, "start_address") and hasattr(objet, "end_address"):
        return [f"{_sans_masque(objet.start_address)}-{_sans_masque(objet.end_address)}"]
    if hasattr(objet, "address"):
        return [str(objet.address)]

    # Serveur virtuel du plugin : son adresse d'écoute.
    if hasattr(objet, "ip_address"):
        return [str(objet.ip_address.address)]

    # Déploiement : l'union des adresses de ses VM. Un flux inter-applicatif se
    # déclare donc une fois, et suit l'application quand son parc change.
    if hasattr(objet, "virtual_machines"):
        adresses = []
        for vm in objet.virtual_machines.all():
            adresses.extend(adresses_de(vm))
        return adresses

    # VM ou équipement : l'adresse primaire si elle existe, sinon TOUTES celles
    # portées par ses interfaces. L'adresse primaire seule serait un piège : une
    # machine multi-réseaux répond aussi sur les autres.
    primaire = getattr(objet, "primary_ip", None)
    if primaire is not None:
        return [str(primaire.address)]
    # Pas d'adresse primaire : on descend aux interfaces. Une VM provisionnée
    # mais pas encore configurée est exactement dans ce cas, et c'est souvent
    # celle pour laquelle on demande un flux.
    interfaces = getattr(objet, "interfaces", None)
    if interfaces is not None:
        adresses = []
        for interface in interfaces.all():
            adresses.extend(str(ip.address) for ip in interface.ip_addresses.all())
        return adresses
    portees = getattr(objet, "ip_addresses", None)
    if portees is not None:
        return [str(ip.address) for ip in portees.all()]
    return []


def noms_dns_de(objet):
    """Les noms DNS connus de NetBox pour cet objet.

    NetBox ne gère pas d'enregistrements DNS dans son cœur : ce qu'il porte est
    le champ `dns_name` d'une adresse. On lit donc ce champ, et rien d'autre —
    inventer un nom à partir du nom de la machine produirait une colonne
    plausible et fausse.
    """
    if objet is None:
        return []
    if hasattr(objet, "dns_name"):
        return [objet.dns_name] if objet.dns_name else []
    primaire = getattr(objet, "primary_ip", None)
    if primaire is not None and primaire.dns_name:
        return [primaire.dns_name]
    if hasattr(objet, "ip_address"):
        return [objet.ip_address.dns_name] if objet.ip_address.dns_name else []
    return []


class Flow(NetBoxModel):
    """Un flux autorisé, d'une source vers une destination, pour un déploiement."""

    deployment = models.ForeignKey(
        to="netbox_applications.Deployment",
        on_delete=models.CASCADE,
        related_name="flows",
        verbose_name="Déploiement",
        help_text="L'instance concernée — donc l'application ET son environnement.",
    )

    # --- Source -------------------------------------------------------------
    source_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=EXTREMITES_Q,
        related_name="+",
        verbose_name="Type de source",
    )
    source_id = models.PositiveBigIntegerField(verbose_name="Source")
    source = GenericForeignKey(ct_field="source_type", fk_field="source_id")

    # --- Destination --------------------------------------------------------
    destination_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=EXTREMITES_Q,
        related_name="+",
        verbose_name="Type de destination",
    )
    destination_id = models.PositiveBigIntegerField(verbose_name="Destination")
    destination = GenericForeignKey(ct_field="destination_type", fk_field="destination_id")

    # --- Ce qui passe -------------------------------------------------------
    # PROTECT : supprimer un service NetBox référencé par un flux ouvert
    # laisserait une règle de pare-feu sans justification.
    service = models.ForeignKey(
        to="ipam.Service",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="application_flows",
        verbose_name="Service NetBox",
        help_text="Quand il est renseigné, protocole et ports viennent de lui — ils ne sont pas recopiés.",
    )
    port_mappings = ArrayField(
        base_field=models.CharField(max_length=63),
        blank=True,
        default=list,
        verbose_name="Protocole/port",
        help_text="Par exemple « tcp/443 ». À ne remplir que si aucun service NetBox ne décrit déjà ce flux.",
    )

    status = models.CharField(
        max_length=20,
        choices=FlowStatusChoices,
        default=FlowStatusChoices.DEMANDE,
        verbose_name="État",
    )
    justification = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Justification",
        help_text="Pourquoi ce flux existe. C'est la seule colonne qu'on relit lors d'une revue.",
    )
    firewall_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence sur le pare-feu",
        help_text="Nom ou numéro de la règle une fois posée, pour relier la matrice à l'équipement.",
    )

    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
    comments = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        ordering = ("deployment", "source_type", "source_id", "destination_type", "destination_id")
        verbose_name = "flux"
        verbose_name_plural = "flux"
        indexes = (
            models.Index(fields=("source_type", "source_id")),
            models.Index(fields=("destination_type", "destination_id")),
        )
        constraints = (
            # Le même flux déclaré deux fois produirait deux lignes identiques
            # dans la matrice, et une question sans réponse à la revue
            # suivante : laquelle est la bonne ?
            models.UniqueConstraint(
                fields=(
                    "deployment",
                    "source_type",
                    "source_id",
                    "destination_type",
                    "destination_id",
                    "service",
                ),
                name="netbox_applications_flux_unique_avec_service",
                condition=models.Q(service__isnull=False),
                violation_error_message="Ce flux est déjà déclaré pour ce déploiement et ce service.",
            ),
        )

    def __str__(self):
        ports = self.ports_lisibles or "ports non précisés"
        return f"{self.libelle_source} vers {self.libelle_destination} ({ports})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_applications:flow", args=[self.pk])

    def get_status_color(self):
        """Couleur du badge d'état — convention NetBox, lue par les gabarits."""
        return FlowStatusChoices.colors.get(self.status)

    # --- Lecture ------------------------------------------------------------

    @property
    def libelle_source(self):
        return str(self.source) if self.source else "(source supprimée)"

    @property
    def libelle_destination(self):
        return str(self.destination) if self.destination else "(destination supprimée)"

    @property
    def mappings(self):
        """Les paires protocole/port du flux — du service s'il y en a un.

        Une seule vérité : quand un objet `Service` décrit déjà le flux, c'est
        lui qui fait foi. Recopier ses ports ici créerait deux valeurs à tenir
        d'accord, et l'une des deux finirait fausse.
        """
        if self.service_id:
            return mappings_du_service(self.service)
        return list(self.port_mappings or [])

    @property
    def ports_lisibles(self):
        return ", ".join(self.mappings)

    @property
    def adresses_source(self):
        return adresses_de(self.source)

    @property
    def adresses_destination(self):
        return adresses_de(self.destination)

    @property
    def dns_destination(self):
        return noms_dns_de(self.destination)

    @property
    def en_vigueur(self):
        """Ce flux décrit-il le réseau tel qu'il est, ou une intention ?"""
        return self.status in FlowStatusChoices.EN_VIGUEUR

    # --- Contrôles ----------------------------------------------------------

    def clean(self):
        super().clean()
        erreurs = {}

        if self.service_id and self.port_mappings:
            erreurs["port_mappings"] = (
                "Un service NetBox est déjà indiqué : ses ports font foi. "
                "Deux sources pour la même information finissent par se contredire."
            )
        elif not self.service_id and not self.port_mappings:
            erreurs["port_mappings"] = (
                "Indiquer un service NetBox, ou au moins une paire protocole/port. "
                "Un flux sans port n'est pas une règle, c'est une intention."
            )

        if self.port_mappings:
            try:
                self.port_mappings = valider_mappings(self.port_mappings)
            except ValidationError as erreur:
                erreurs["port_mappings"] = erreur.messages

        meme_extremite = (
            self.source_type_id
            and self.source_type_id == self.destination_type_id
            and self.source_id == self.destination_id
        )
        if meme_extremite:
            erreurs["destination_id"] = "La source et la destination sont le même objet."

        # Le service doit décrire la DESTINATION, pas un tiers. Sans ce
        # contrôle, un flux pourrait emprunter les ports d'une machine qui n'est
        # pas celle qu'il ouvre — et la matrice serait fausse sans qu'on puisse
        # le voir en la relisant.
        if self.service_id and self.destination_type_id and self.destination is not None:
            parent = getattr(self.service, "parent", None) or getattr(self.service, "virtual_machine", None)
            vms_du_deploiement = (
                set(self.destination.virtual_machines.values_list("pk", flat=True))
                if hasattr(self.destination, "virtual_machines")
                else set()
            )
            rattache = parent is not None and (
                parent == self.destination or (getattr(parent, "pk", None) in vms_du_deploiement)
            )
            if not rattache:
                erreurs["service"] = (
                    f"Le service « {self.service} » est rattaché à « {parent or 'rien'} », "
                    f"qui n'est pas la destination « {self.libelle_destination} »."
                )

        if erreurs:
            raise ValidationError(erreurs)
