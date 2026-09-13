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
| **URL d'accès** | **propre à cet environnement** — la recette n'a pas l'URL de la production |
| VM | les machines qui portent cette instance |

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

L'image officielle de NetBox ne contient pas les plugins : il faut en **dériver une** qui les
installe. C'est la façon prévue par `netbox-docker`, pas un contournement.

Trois fichiers à créer dans votre copie de `netbox-docker`, puis une commande.

#### 1. `Dockerfile-plugins`

```dockerfile
# Dérive l'image officielle en y ajoutant le plugin.
# L'image amont n'est pas reconstruite : ses correctifs restent acquis.
ARG NETBOX_IMAGE_TAG=v4.7-5.1.1
FROM netboxcommunity/netbox:${NETBOX_IMAGE_TAG}

ARG PLUGIN_VERSION=v0.1.0

USER root

# git n'est nécessaire QUE pour l'installation depuis un dépôt, et il est
# retiré aussitôt : le laisser agrandirait l'image et sa surface d'attaque.
#
# « uv pip » et non « pip » : l'image officielle installe ses dépendances avec
# uv, et un environnement virtuel créé par uv n'embarque PAS pip.
# « /opt/netbox/venv/bin/pip » échouerait avec un code 127.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && uv pip install --no-cache \
      "netbox-plugin-applications @ git+https://github.com/AurevLan/netbox-plugin-applications@${PLUGIN_VERSION}" \
 && apt-get purge -y --auto-remove git \
 && rm -rf /var/lib/apt/lists/*

USER 999
```

#### 2. `configuration/extra.py`

```python
PLUGINS = ["netbox_applications"]
```

> Ce fichier existe déjà dans `netbox-docker` — ajoutez-y la ligne plutôt que de l'écraser.

#### 3. `docker-compose.override.yml`

```yaml
# L'ancre est partagée entre netbox et netbox-worker : les deux DOIVENT
# utiliser la même image. Un worker sans le plugin ne saurait pas traiter les
# objets qu'il définit, et l'erreur ne se voit qu'à l'exécution d'une tâche.
x-netbox-plugins: &netbox-plugins
  build:
    context: .
    dockerfile: Dockerfile-plugins
    args:
      NETBOX_IMAGE_TAG: "v4.7-5.1.1"
      PLUGIN_VERSION: "v0.1.0"
  image: netbox-with-plugins:latest

services:
  netbox:
    <<: *netbox-plugins
    ports:
      - "8000:8080"
    healthcheck:
      # Le premier démarrage après ajout d'un plugin est plus long : migrations
      # et collecte des fichiers statiques. Sur une machine modeste, la valeur
      # amont (90 s) ne suffit pas.
      start_period: 300s

  netbox-worker:
    <<: *netbox-plugins
```

#### 4. Construire et démarrer

```bash
docker compose build netbox
docker compose up -d
```

**Les migrations sont appliquées automatiquement** au démarrage par le point d'entrée de
`netbox-docker` : aucune commande à lancer.

#### 5. Vérifier

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/plugins/installed-plugins/
```

Doit retourner `Applications` et sa version. Le menu **Applications** apparaît alors dans
l'interface.

#### Si quelque chose ne va pas

| Symptôme | Cause |
|---|---|
| `exit code: 127` à la construction | `pip` utilisé au lieu de `uv pip` — l'image officielle n'a pas pip dans son venv |
| Le menu n'apparaît pas | `PLUGINS` absent de `configuration/extra.py`, ou fichier non monté |
| `relation "netbox_applications_..." does not exist` | l'image a été construite sans le plugin, ou le conteneur tourne sur une image antérieure — reconstruire puis `up -d` |
| Les tâches en arrière-plan échouent | `netbox-worker` n'utilise pas la même image que `netbox` |
| Démarrage déclaré `unhealthy` | `start_period` trop court sur une machine lente |

### Installation classique (NetBox installé directement sur un serveur)

> **Le paquet n'est pas encore publié sur PyPI.** L'installation se fait depuis ce dépôt.

```bash
# 1. Installer dans l'environnement virtuel de NetBox — pas celui du système
source /opt/netbox/venv/bin/activate
pip install "netbox-plugin-applications @ git+https://github.com/AurevLan/netbox-plugin-applications@v0.1.0"
```

```python
# 2. Déclarer le plugin dans /opt/netbox/netbox/netbox/configuration.py
PLUGINS = ["netbox_applications"]
```

```bash
# 3. Appliquer les migrations et collecter les fichiers statiques
python /opt/netbox/netbox/manage.py migrate
python /opt/netbox/netbox/manage.py collectstatic --no-input

# 4. Redémarrer NetBox ET son worker
sudo systemctl restart netbox netbox-rq
```

```bash
# 5. Survivre aux mises à jour de NetBox
#    upgrade.sh recrée l'environnement virtuel : sans cette ligne, le plugin
#    disparaîtrait silencieusement à la prochaine montée de version.
echo 'netbox-plugin-applications @ git+https://github.com/AurevLan/netbox-plugin-applications@v0.1.0' \
  >> /opt/netbox/local_requirements.txt
```

> **L'étape 5 est celle qu'on oublie.** Le script `upgrade.sh` de NetBox reconstruit
> l'environnement virtuel à partir de `requirements.txt` et `local_requirements.txt`. Un plugin
> absent de ce second fichier est perdu à la mise à jour — et l'interface se met simplement à
> ne plus afficher le menu, sans erreur.

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

> **`access_url` et non `url`.** Chaque objet NetBox expose déjà un champ `url` hypermedia,
> qui pointe vers l'objet lui-même. L'adresse d'accès de l'application porte donc un nom
> distinct.

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
