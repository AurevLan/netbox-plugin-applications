# netbox-plugin-applications

**Catalogue applicatif CMDB pour NetBox** — applications, déploiements multi-environnements,
champs ITIL.

NetBox sait décrire l'infrastructure. Il ne sait pas dire **à quoi elle sert**. Ce plugin comble
cet écart : il ajoute un catalogue d'applications et relie chacune aux machines qui la portent.

---

## Ce que le plugin apporte

### Deux objets, et c'est le point essentiel

Une application vit dans **plusieurs environnements à la fois**, et ce qui les distingue n'est
pas accessoire.

```
Application « Portail RH »  APP-0001              ← le service
   ├── Déploiement  Production      ses VM · sa maintenance · son exposition
   ├── Déploiement  Recette
   └── Déploiement  Développement
```

**La règle de partage** : ce qui décrit le **service** reste sur l'application ; ce qui décrit
une **instance** va sur le déploiement.

Porter les VM ou la plage de maintenance sur l'application supposerait que production et recette
partagent les mêmes. L'erreur ne se voit pas à la saisie — elle se découvre le jour où l'on
interrompt la production en croyant toucher la recette.

### Champs de la fiche

**Application** — ce qui est vrai quel que soit l'environnement :

| | |
|---|---|
| Identifiant | `APP-0001`, **attribué automatiquement**, non modifiable |
| Client | un `tenancy.Tenant`, à son sens natif |
| Cycle de vie | En projet · En service · En retrait · Retiré |
| Criticité métier | Critique · Majeure · Standard · Mineure |
| **RTO** | durée maximale d'interruption admise |
| **RPO** | perte de données admise — *conditionne la fréquence des sauvegardes* |
| Horaires de service | quand le service doit être **supporté** |
| Classification | Public · Interne · Confidentiel · Restreint |
| Données personnelles | RGPD |
| **Authentification** | Keycloak · OIDC · SAML · LDAP · AD · **Locale** · Aucune |
| Référents | technique et chef de projet, des `tenancy.Contact` |

**Déploiement** — ce qui dépend de l'environnement :

| | |
|---|---|
| Environnement, statut | unicité garantie : **une seule fiche par environnement** |
| Plage de maintenance | quand une interruption est admise **ici** |
| Diffusé à l'externe | propre à cet environnement |
| URL d'accès, VM | |

### Deux règles impossibles à enfreindre

Le modèle ne se contente pas de déconseiller — il **refuse** :

1. **Deux déploiements dans le même environnement.** Sans cette contrainte, deux fiches
   « production » divergeraient en silence.
2. **Exposer à l'externe une application traitant des données restreintes.** Le message indique
   les deux issues : abaisser la classification, ou retirer l'exposition. Ce n'est pas une
   interdiction de principe — c'est la combinaison qu'on ne veut pas voir apparaître par
   inadvertance.

### Trois distinctions qui évitent des erreurs

- **Horaires de service ≠ plage de maintenance.** Les premiers disent quand on doit *répondre*,
  la seconde quand on peut *interrompre*. Les confondre conduit à planifier une interruption au
  pire moment.
- **RPO ≠ fréquence de sauvegarde souhaitée.** Le RPO est un **engagement** : un RPO d'une heure
  *interdit* une sauvegarde quotidienne.
- **Authentification « Locale » n'est pas un détail.** Elle signale des comptes **échappant à la
  révocation centralisée**. Le jour où quelqu'un quitte l'organisation, c'est cette liste qu'on
  ouvre.

---

## Installation

### Version requise

| | |
|---|---|
| NetBox | ≥ 4.7.0 |
| Python | ≥ 3.12 |

`min_version` est déclaré dans le plugin : une version de NetBox incompatible fait **échouer le
démarrage explicitement**, plutôt que de produire un comportement imprévisible.

### Avec netbox-docker

Étendre l'image publiée, sans la reconstruire :

```dockerfile
ARG NETBOX_IMAGE_TAG
FROM netboxcommunity/netbox:${NETBOX_IMAGE_TAG}

USER root
COPY netbox-plugin-applications/ /opt/netbox-plugins/applications/
# L'image amont installe ses dépendances avec « uv », et un venv créé par uv
# n'embarque PAS pip : « venv/bin/pip » échouerait en 127.
RUN uv pip install --no-cache /opt/netbox-plugins/applications/
USER 999
```

Puis déclarer le plugin dans `/etc/netbox/config/extra.py` :

```python
PLUGINS = ["netbox_applications"]
```

> **Le service `netbox-worker` doit utiliser la même image.** Un worker sans le plugin ne saurait
> pas traiter les objets qu'il définit.

### Installation classique

```bash
source /opt/netbox/venv/bin/activate
pip install netbox-plugin-applications
python /opt/netbox/netbox/manage.py migrate
python /opt/netbox/netbox/manage.py collectstatic --no-input
```

---

## Utilisation

### Interface

Menu **Applications**, avec deux entrées. La fiche d'une application porte un onglet
**Déploiements** dont le badge affiche leur nombre.

### API

```
/api/plugins/applications/applications/
/api/plugins/applications/deployments/
```

Créer une application — **sans fournir d'identifiant**, il est attribué :

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Portail RH","client":2,"lifecycle_status":"en-service",
       "criticality":"critique","rto":"4h","rpo":"1h",
       "data_classification":"confidentiel","personal_data":true,
       "authentication":"keycloak"}' \
  "$NETBOX_URL/api/plugins/applications/applications/"
```

Puis un déploiement par environnement :

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"application":1,"environment":"production","status":"actif",
       "maintenance_window":"aucune-24-7","external_facing":true,
       "access_url":"https://rh.example.com"}' \
  "$NETBOX_URL/api/plugins/applications/deployments/"
```

> **`access_url` et non `url`.** Le modèle a un champ `url` (l'adresse d'accès) et NetBox attend
> un champ `url` hypermedia. L'adresse d'accès est donc exposée sous `access_url`.

### Filtres utiles

| Question | Filtre |
|---|---|
| Quelles applications sont en production ? | `?environment=production` — traverse la relation |
| Lesquelles ont une authentification locale ? | `?authentication=locale` |
| Lesquelles traitent des données personnelles ? | `?personal_data=true` |
| Quels déploiements sont exposés ? | `/deployments/?external_facing=true` |

---

## Développement

### Mise en place

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

### Contrôles

```bash
ruff check .            # style, imports, pièges courants, motifs dangereux
ruff format --check .   # formatage
bandit -c pyproject.toml -r netbox_applications
pip-audit                # vulnérabilités des dépendances
detect-secrets scan      # secrets accidentellement commités
```

Tous sont exécutés à chaque commit par `pre-commit`, et à chaque poussée par l'intégration
continue.

### Modifier le modèle

Django exige une migration à chaque changement de modèle, et **NetBox interdit
`makemigrations` hors mode développeur** :

```bash
# DEVELOPER = True dans une copie TEMPORAIRE de la configuration
python manage.py makemigrations netbox_applications
```

> ⚠️ **Générer la migration, PUIS reconstruire l'image.** L'ordre inverse échoue
> **silencieusement** : aucune erreur au démarrage, seulement une table absente.

---

## Sécurité

Voir [SECURITY.md](SECURITY.md) pour signaler une vulnérabilité.

Le plugin **ne déclare aucune dépendance** : il s'exécute dans NetBox et n'utilise que ce que
NetBox fournit. C'est délibéré — une dépendance ajoutée ici exposerait à un conflit de version
avec l'hôte, que rien ne résoudrait proprement.

## Origine

Ce plugin est né d'un besoin concret : un lab d'automatisation d'infrastructure où NetBox sert
de source de vérité pour provisionner des machines, sans qu'aucun objet ne permette de dire
**à quoi elles servent**.

Les choix de conception sont donc guidés par l'exploitation, pas par l'exhaustivité. Les
dépendances entre applications, par exemple, ont été volontairement écartées : c'est le champ
le plus utile en incident, mais le plus difficile à tenir à jour — et une carte de dépendances
fausse est plus dangereuse qu'une absence de carte.

## Licence

MIT — voir [LICENSE](LICENSE).
