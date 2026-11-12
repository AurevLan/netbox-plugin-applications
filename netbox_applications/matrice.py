"""La matrice de flux d'un déploiement, et d'une application.

TROIS ORIGINES, ET ELLES NE SE VALENT PAS. Une matrice utile ne montre pas
seulement ce qu'on a saisi : elle montre aussi ce que le modèle implique déjà,
et surtout CE QUI MANQUE. Chaque ligne porte donc son origine :

  « déclaré »     un objet `Flow` — quelqu'un l'a écrit, daté, justifié.
  « déduit »      personne ne l'a saisi, mais le modèle ne laisse pas le choix :
                  une instance diffusée à l'externe derrière un WAF implique un
                  flux vers son serveur virtuel, et ce serveur virtuel implique
                  un flux vers les machines qu'il sert.
  « à déclarer »  un objet `Service` existe sur une VM du déploiement, et AUCUN
                  flux ne dit depuis où on l'atteint. C'est un port ouvert sans
                  source connue — la ligne la plus intéressante de la matrice.

LA TROISIÈME EST LA RAISON D'ÊTRE DE CE FICHIER. Une matrice qui ne liste que
les flux déclarés est toujours complète par construction : elle décrit ce qu'on
sait déjà. Celle-ci peut dire « il vous manque ceci », et c'est la seule forme
qui serve à quelque chose lors d'une revue.

RIEN N'EST STOCKÉ. Les lignes déduites sont recalculées à chaque affichage. Les
figer en base créerait des lignes à maintenir d'accord avec les objets dont
elles sont tirées — c'est-à-dire une seconde vérité, fausse dès le premier
changement de WAF.
"""

import csv
import io
from dataclasses import dataclass

from .choices import FlowStatusChoices
from .models.flow import adresses_de, mappings_du_service, noms_dns_de

DECLARE = "déclaré"
DEDUIT = "déduit"
A_DECLARER = "à déclarer"

# Pour les lignes déduites qui viennent de l'extérieur : il n'existe aucun objet
# NetBox représentant « Internet », et en inventer un serait un objet que
# personne ne gère. La ligne est marquée « déduit », donc on sait qu'elle n'a
# pas d'objet derrière elle.
INTERNET = "Internet"


@dataclass(frozen=True)
class Ligne:
    """Une ligne de matrice, prête à être lue, exportée ou envoyée à un pare-feu."""

    origine: str
    source: str
    destination: str
    mappings: tuple = ()
    adresses_source: tuple = ()
    adresses_destination: tuple = ()
    dns: tuple = ()
    etat: str = ""
    couleur: str = ""
    justification: str = ""
    reference: str = ""
    flux: object = None
    deploiement: object = None
    alerte: str = ""

    @property
    def ports(self):
        return ", ".join(self.mappings)

    @property
    def est_declare(self):
        return self.origine == DECLARE

    @property
    def manque(self):
        return self.origine == A_DECLARER


def _ligne_declaree(flux):
    return Ligne(
        origine=DECLARE,
        source=flux.libelle_source,
        destination=flux.libelle_destination,
        mappings=tuple(flux.mappings),
        adresses_source=tuple(flux.adresses_source),
        adresses_destination=tuple(flux.adresses_destination),
        dns=tuple(flux.dns_destination),
        etat=flux.get_status_display(),
        couleur=flux.get_status_color() or "",
        justification=flux.justification,
        reference=flux.firewall_reference,
        flux=flux,
        deploiement=flux.deployment,
    )


def _ligne_deduite(source, destination, mappings, deploiement, raison, alerte=""):
    return Ligne(
        origine=DEDUIT,
        source=str(source),
        destination=str(destination),
        mappings=tuple(mappings),
        adresses_source=tuple(adresses_de(source) if not isinstance(source, str) else ["0.0.0.0/0"]),
        adresses_destination=tuple(adresses_de(destination)),
        dns=tuple(noms_dns_de(destination)),
        etat="Impliqué par le modèle",
        couleur="cyan",
        justification=raison,
        deploiement=deploiement,
        alerte=alerte,
    )


def _services_du_deploiement(deploiement):
    """Les objets `Service` portés par les VM de ce déploiement."""
    couples = []
    for vm in deploiement.virtual_machines.all():
        for service in vm.services.all():
            couples.append((vm, service))
    return couples


def matrice_du_deploiement(deploiement):
    """Les lignes de matrice d'un déploiement : déclarées, déduites, manquantes."""
    lignes = []

    declares = list(deploiement.flows.select_related("source_type", "destination_type", "service"))
    for flux in declares:
        lignes.append(_ligne_declaree(flux))

    # Les services déjà couverts par un flux déclaré, pour ne pas les redemander.
    services_couverts = {flux.service_id for flux in declares if flux.service_id}

    vs = deploiement.waf_virtual_server
    services = _services_du_deploiement(deploiement)

    # 1. L'extérieur vers le point d'entrée. Déduit de « diffusé à l'externe ».
    if deploiement.external_facing and vs is not None:
        port = f"tcp/{vs.port}" if vs.port else ""
        lignes.append(
            _ligne_deduite(
                INTERNET,
                vs,
                [port] if port else [],
                deploiement,
                "Instance diffusée à l'externe, derrière ce serveur virtuel.",
                alerte="" if vs.port else "Le serveur virtuel n'a pas de port déclaré.",
            )
        )
    elif deploiement.external_facing and vs is None:
        lignes.append(
            Ligne(
                origine=A_DECLARER,
                source=INTERNET,
                destination="(aucun point d'entrée déclaré)",
                etat="Incomplet",
                couleur="red",
                justification="L'instance est diffusée à l'externe sans serveur virtuel déclaré.",
                deploiement=deploiement,
                alerte="Diffusion externe sans point d'entrée : la matrice ne peut pas être complète.",
            )
        )

    # 2. Le point d'entrée vers les machines qu'il sert.
    if vs is not None:
        for vm, service in services:
            lignes.append(
                _ligne_deduite(
                    vs,
                    service,
                    mappings_du_service(service),
                    deploiement,
                    f"Le serveur virtuel sert « {vm} », qui expose ce service.",
                )
            )

    # 3. Ce qui manque : un service exposé dont personne ne dit l'origine.
    for vm, service in services:
        if service.pk in services_couverts:
            continue
        # Déjà rendu visible par la ligne déduite 2 : on ne redemande une
        # déclaration que si aucun serveur virtuel ne l'explique.
        if vs is not None:
            continue
        lignes.append(
            Ligne(
                origine=A_DECLARER,
                source="(source non déclarée)",
                destination=str(service),
                mappings=tuple(mappings_du_service(service)),
                adresses_destination=tuple(adresses_de(vm)),
                dns=tuple(noms_dns_de(vm)),
                etat="À compléter",
                couleur="red",
                justification=f"« {vm} » expose ce service, et aucun flux ne dit depuis où on l'atteint.",
                deploiement=deploiement,
                alerte="Port exposé sans source déclarée.",
            )
        )

    return lignes


def matrice_de_l_application(application):
    """Toutes les lignes d'une application, environnement par environnement.

    L'ordre suit celui des déploiements — donc celui des environnements tel que
    le référentiel le classe. Une matrice qui mélangerait recette et production
    ne serait pas une matrice d'application, mais un tas.
    """
    lignes = []
    deploiements = application.deployments.select_related("environment", "waf_virtual_server")
    for deploiement in deploiements:
        lignes.extend(matrice_du_deploiement(deploiement))
    return lignes


COLONNES = (
    "application",
    "environnement",
    "origine",
    "source",
    "adresses_source",
    "destination",
    "adresses_destination",
    "dns",
    "ports",
    "etat",
    "justification",
    "reference_pare_feu",
)


def en_csv(lignes):
    """La matrice au format CSV, telle qu'on l'envoie à une équipe réseau.

    Les adresses sont jointes par un espace et non par une virgule : un CSV dont
    les cellules contiennent des virgules s'ouvre de travers dans la moitié des
    tableurs, et une matrice de flux illisible ne protège rien.
    """
    tampon = io.StringIO()
    graveur = csv.writer(tampon, delimiter=";")
    graveur.writerow(COLONNES)
    for ligne in lignes:
        deploiement = ligne.deploiement
        graveur.writerow(
            (
                str(deploiement.application) if deploiement else "",
                str(deploiement.environment) if deploiement else "",
                ligne.origine,
                ligne.source,
                " ".join(ligne.adresses_source),
                ligne.destination,
                " ".join(ligne.adresses_destination),
                " ".join(ligne.dns),
                ligne.ports,
                ligne.etat,
                ligne.justification,
                ligne.reference,
            )
        )
    return tampon.getvalue()


# Clés SANS ACCENT ni espace : un gabarit Django résout « resume.declare », pas
# « resume.à déclarer ». Les libellés accentués restent sur les lignes, où ils
# sont affichés et jamais utilisés comme clés.
_CLES = {DECLARE: "declare", DEDUIT: "deduit", A_DECLARER: "a_declarer"}


def compte_par_origine(lignes):
    """De quoi afficher un résumé honnête en tête de matrice."""
    resume = {"declare": 0, "deduit": 0, "a_declarer": 0}
    for ligne in lignes:
        cle = _CLES.get(ligne.origine)
        if cle:
            resume[cle] += 1
    resume["en_vigueur"] = sum(
        1 for ligne in lignes if ligne.flux is not None and ligne.flux.status in FlowStatusChoices.EN_VIGUEUR
    )
    resume["total"] = len(lignes)
    return resume
