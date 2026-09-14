"""Indexation pour la recherche globale de NetBox.

POURQUOI C'EST INDISPENSABLE À UNE CMDB. La barre de recherche est la première
porte d'entrée : on tape « APP-0001 » ou « Keycloak », pas un chemin de menu.
Sans index, les objets du plugin sont INVISIBLES — la recherche ne renvoie rien
et n'indique pas pourquoi.

NetBox charge automatiquement la liste « indexes » de ce module (attribut
« search_indexes » d'un PluginConfig, dont le chemin par défaut est
« search.indexes »). Le décorateur @register_search n'est donc PAS employé ici :
l'enregistrement est fait par le chargeur du plugin.

LE POIDS SE LIT À L'ENVERS : plus il est FAIBLE, plus le champ est jugé
pertinent. L'identifiant applicatif passe donc devant le nom — qui cherche
« APP-0001 » cherche cette fiche-là, et rien d'autre.

⚠️ Déclarer un index ne remplit pas la table. Les objets déjà en base ne sont
indexés qu'à leur prochaine écriture, ou par « manage.py reindex
netbox_applications ». Sans cela, la recherche reste muette et tout semble
pourtant en place.
"""

from netbox.search import SearchIndex

from . import models

CATALOGUE = "Applications"
REFERENTIELS = "Applications — référentiels"


class ApplicationIndex(SearchIndex):
    model = models.Application
    category = CATALOGUE
    fields = (
        # Devant le nom : un identifiant recherché est recherché exactement.
        ("application_id", 90),
        ("name", 100),
        # Retrouver toutes les applications d'un service par son adresse est
        # une question courante en gestion de parc applicatif.
        ("business_contact", 250),
        ("documentation_url", 300),
        ("description", 500),
        ("comments", 5000),
    )
    display_attrs = ("client", "lifecycle_status", "criticality", "business_contact")


class DeploymentIndex(SearchIndex):
    model = models.Deployment
    category = CATALOGUE
    # Un déploiement n'a pas de nom propre : c'est son URL d'accès qu'on cherche
    # en pratique, quand on tombe sur une adresse sans savoir ce qu'elle sert.
    fields = (
        ("access_url", 200),
        ("description", 500),
        ("comments", 5000),
    )
    display_attrs = ("application", "environment", "status", "access_url")


def _index_referentiel(modele):
    """Produit l'index d'un référentiel.

    Les dix partagent la même forme. Une fabrique évite dix classes recopiées
    et garantit qu'aucun référentiel n'est oublié — le contrôle en fin de
    module s'en assure.
    """
    return type(
        f"{modele.__name__}Index",
        (SearchIndex,),
        {
            "model": modele,
            "category": REFERENTIELS,
            "fields": (
                ("name", 100),
                ("slug", 110),
                ("description", 500),
                ("comments", 5000),
            ),
            "display_attrs": ("description",),
        },
    )


indexes = [
    ApplicationIndex,
    DeploymentIndex,
    *[_index_referentiel(modele) for modele in models.REFERENCES],
]

# Un « assert » disparaîtrait avec « python -O ». On lève explicitement.
_attendu = len(models.REFERENCES) + 2
if len(indexes) != _attendu:
    raise RuntimeError(f"{len(indexes)} index déclarés pour {_attendu} modèles indexables.")
