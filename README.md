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
| **Cycle de vie du service** | l'organisation rend-elle encore ce service ? |
| Criticité métier | Critique · Majeure · Standard · Mineure |
| **RTO** | durée maximale d'interruption admise |
| **RPO** | perte de données admise — *conditionne la fréquence des sauvegardes* |
| Horaires de service | quand le service doit être **supporté** |
| Classification | Public · Interne · Confidentiel · Restreint |
| Données personnelles | RGPD |
| **Authentification** | Keycloak · OIDC · SAML · LDAP · AD · **Locale** · Aucune |
| Référents | technique et chef de projet, des `tenancy.Contact` |
| **Contact métier** | **champ libre, mais au format adresse imposé** — voir ci-dessous |

Toutes les valeurs de ces listes s'ajoutent **dans l'interface** — voir
[Les référentiels](#les-référentiels).

**Déploiement** — ce qui dépend de l'environnement :

| | |
|---|---|
| Environnement | unicité garantie : **une seule fiche par environnement** |
| **État de l'instance** | cette instance-là tourne-t-elle ? — *à ne pas confondre avec le cycle de vie du service* |
| Plage de maintenance | quand une interruption est admise **ici** |
| Diffusé à l'externe | propre à cet environnement |
| **URL d'accès** | **propre à cet environnement** — la recette n'a pas l'URL de la production |
| VM | les machines qui portent cette instance |

### Trois règles impossibles à enfreindre

Le modèle ne se contente pas de déconseiller — il **refuse** :

1. **Deux déploiements dans le même environnement.** Sans cette contrainte, deux fiches
   « production » divergeraient en silence.
2. **Exposer à l'externe une application traitant des données restreintes.** Le message indique
   les deux issues : abaisser la classification, ou retirer l'exposition. Ce n'est pas une
   interdiction de principe — c'est la combinaison qu'on ne veut pas voir apparaître par
   inadvertance.
3. **Retirer un service dont une instance de production tourne encore.** La règle vaut **dans
   les deux sens** : ni en retirant le service, ni en démarrant l'instance. Hors production,
   aucune contrainte — une recette peut survivre au retrait, le temps d'une réversibilité.

Ces trois règles sont **éprouvées à chaque poussée** par l'intégration continue, avec des cas
qui doivent être refusés *et* des cas qui doivent être acceptés : un contrôle trop large est
aussi faux qu'un contrôle absent.

### Quatre distinctions qui évitent des erreurs

- **Horaires de service ≠ plage de maintenance.** Les premiers disent quand on doit *répondre*,
  la seconde quand on peut *interrompre*. Les confondre conduit à planifier une interruption au
  pire moment.
- **RPO ≠ fréquence de sauvegarde souhaitée.** Le RPO est un **engagement** : un RPO d'une heure
  *interdit* une sauvegarde quotidienne.
- **Cycle de vie du service ≠ état d'instance.** Le premier dit si l'organisation rend encore
  le service, le second si *cette instance-là* tourne. Un service en exploitation peut avoir une
  instance de développement encore planifiée.
- **Contact métier ≠ référent technique.** Les deux référents pointent vers l'annuaire de
  contacts de NetBox ; le responsable métier n'y figure que rarement — c'est souvent un
  responsable de service ou une liste de diffusion. Le champ est donc **libre**, mais son
  **format est imposé** : une adresse de courriel, la seule chose qu'on puisse à la fois valider
  et utiliser en incident. Exiger la création préalable d'un contact ferait laisser le champ
  vide, ce qui est pire qu'une adresse saisie à la main.
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

ARG PLUGIN_VERSION=v0.5.1

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
      PLUGIN_VERSION: "v0.5.1"
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
| **La recherche ne trouve rien** | index jamais peuplé — lancer `manage.py reindex netbox_applications` |
| **La recherche ne reflète pas les modifications** | `netbox-worker` sans le plugin : il traite la tâche d'indexation sans savoir indexer ces objets, **et sans erreur** |
| Démarrage déclaré `unhealthy` | `start_period` trop court sur une machine lente |
| Le plugin **recule de version** sans erreur | une valeur de repli sur `PLUGIN_VERSION` (`${PLUGIN_VERSION:-v0.1.0}`) : la variable manquante fait construire une version ancienne, sous le nom d'image attendu. Préférer `${PLUGIN_VERSION:?}`, qui **arrête** la commande |

### Installation classique (NetBox installé directement sur un serveur)

> **Le paquet n'est pas encore publié sur PyPI.** L'installation se fait depuis ce dépôt.

```bash
# 1. Installer dans l'environnement virtuel de NetBox — pas celui du système
source /opt/netbox/venv/bin/activate
pip install "netbox-plugin-applications @ git+https://github.com/AurevLan/netbox-plugin-applications@v0.5.1"
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
echo 'netbox-plugin-applications @ git+https://github.com/AurevLan/netbox-plugin-applications@v0.5.1' \
  >> /opt/netbox/local_requirements.txt
```

> **L'étape 5 est celle qu'on oublie.** Le script `upgrade.sh` de NetBox reconstruit
> l'environnement virtuel à partir de `requirements.txt` et `local_requirements.txt`. Un plugin
> absent de ce second fichier est perdu à la mise à jour — et l'interface se met simplement à
> ne plus afficher le menu, sans erreur.

---

## Utilisation

### Interface

Menu **Applications**, en deux groupes :

- **Catalogue** — *Applications* et *Déploiements*, ce qu'on consulte tous les jours.
- **Référentiels** — les dix listes de valeurs, qu'on modifie rarement.

La fiche d'une application porte un onglet **Déploiements** dont le badge affiche leur nombre.

### Recherche globale

Les objets du plugin sont indexés : `APP-0001`, `Keycloak`, ou l'URL d'accès d'un déploiement
répondent depuis la barre de recherche de NetBox. Les résultats sont groupés sous deux
catégories, *Applications* et *Applications — référentiels*.

**L'identifiant passe devant le nom** : qui cherche `APP-0001` cherche cette fiche-là.

> ⚠️ **À la première installation de la version 0.6.0, lancer un réindexage.** Déclarer un index
> ne remplit pas la table : les objets déjà en base ne sont indexés qu'à leur prochaine
> écriture. Sans cette commande, la recherche reste muette alors que tout semble en place.
>
> ```bash
> python manage.py reindex netbox_applications
> ```
>
> Avec `netbox-docker` : `docker compose exec netbox /opt/netbox/netbox/manage.py reindex netbox_applications`

> ⚠️ **Le worker DOIT porter le plugin.** L'indexation est confiée à une tâche de fond. Un
> `netbox-worker` construit sur une image sans le plugin **n'indexe jamais rien**, sans la
> moindre erreur : la recherche cesse simplement de refléter les modifications. C'est la même
> image pour les deux services, sans exception.

### API

```
/api/plugins/applications/applications/
/api/plugins/applications/deployments/
/api/plugins/applications/authenticationmethod/     ← et les neuf autres référentiels
```

**Les champs de référentiel attendent un identifiant numérique**, comme toute relation NetBox.
On le récupère par son `slug` :

```bash
AUTH=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$NETBOX_URL/api/plugins/applications/authenticationmethod/?slug=keycloak" \
  | jq -r '.results[0].id')
```

Créer une application — **sans fournir d'identifiant**, il est attribué :

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"name\":\"Portail RH\",\"client\":2,\"authentication\":$AUTH,
       \"personal_data\":true}" \
  "$NETBOX_URL/api/plugins/applications/applications/"
```

Puis un déploiement par environnement :

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"application\":1,\"environment\":$ENV_PROD,\"status\":$ETAT_ACTIF,
       \"external_facing\":true,\"access_url\":\"https://rh.example.com\"}" \
  "$NETBOX_URL/api/plugins/applications/deployments/"
```

> **`access_url` et non `url`.** Chaque objet NetBox expose déjà un champ `url` hypermedia,
> qui pointe vers l'objet lui-même. L'adresse d'accès de l'application porte donc un nom
> distinct.

### Les référentiels

**Les dix listes de valeurs sont des objets NetBox à part entière.** Ajouter « CAS » ne demande
ni fichier à éditer, ni redémarrage, ni migration :

```
Applications → Référentiels → Authentification → « Ajouter »
```

Un nom, une couleur, une description. La valeur est immédiatement proposée dans les formulaires.

| Référentiel | Ce qu'il alimente |
|---|---|
| Cycle de vie du service | Application → Cycle de vie |
| Criticités | Application → Criticité |
| RTO / RPO | Application → engagements de continuité |
| Horaires de service | Application → Horaires |
| Classifications | Application → Classification |
| Authentification | Application → Authentification |
| Environnements | Déploiement → Environnement |
| États d'instance | Déploiement → État |
| Plages de maintenance | Déploiement → Maintenance |

**Supprimer une valeur employée est refusé.** Les clés étrangères sont en `PROTECT` : effacer
« Critique » ne doit pas vider silencieusement le champ de toutes les applications concernées.

#### Chaque référentiel porte plus qu'un libellé

C'est le point qui dépasse le confort. **Un attribut bien choisi transforme une convention
tacite en donnée interrogeable.**

| Référentiel | Attribut | Ce qu'il permet |
|---|---|---|
| Authentification | `is_centralized` | « quelles applications ont des comptes échappant à la révocation ? » — **sans supposer que la valeur s'appelle "locale"** |
| RTO / RPO | `minutes` | comparer et trier ; « RPO inférieur à 2 heures » devient une requête |
| Criticité | `incident_priority`, `requires_oncall` | relier la fiche au traitement des incidents |
| Classification | `level`, `requires_encryption` | « au moins confidentiel » devient une requête |
| Environnement | `is_production` | des règles plus strictes, sans liste de noms à maintenir |
| Cycle de vie | `is_operational` | « le service est-il rendu ? », quel que soit le libellé |

Renommer « Locale » en « Comptes applicatifs » ne casse aucune requête : les filtres portent sur
l'attribut, jamais sur le nom.

#### La couleur porte un sens

| Règle | Application |
|---|---|
| La **chaleur** indique l'exigence ou le risque | rouge sombre = contrainte la plus forte (RTO de 15 minutes, donnée restreinte) ; vert = exigence faible |
| Le **gris** est réservé à l'absence d'engagement | « au mieux », « à définir », « retiré » |
| **Froid = centralisé**, chaud = ne l'est pas | la couleur redit ce que dit `is_centralized` |

Les listes affichent ces badges, pas seulement les fiches : c'est sur plusieurs dizaines de
lignes qu'une palette paie.

> **Avant la version 0.4.0**, ces listes étaient des `ChoiceSet` étendus par `FIELD_CHOICES`
> dans la configuration de NetBox, suivis d'un redémarrage. **Cette procédure n'a plus aucun
> effet.** La migration vers les référentiels reprend les valeurs *employées par une fiche* ;
> celles déclarées dans `FIELD_CHOICES` sans être utilisées doivent être recréées dans
> l'interface.

### Filtrer dans l'interface

La liste des applications propose un panneau de filtres **regroupé par section** :

| Section | Filtres |
|---|---|
| Cycle de vie | cycle de vie du service, **service rendu**, criticité |
| Continuité | RTO, RPO, horaires de service |
| **Sécurité** | classification, données personnelles, authentification, **authentification centralisée** |
| Rattachements | client, référent technique, référent chef de projet |
| Déploiements | **environnement** — traverse la relation |

Le filtre **Environnement** répond à « quelles applications sont en production ? » : il porte
sur les déploiements, pas sur l'application elle-même.

### Filtres utiles

> ⚠️ **Un filtre inconnu est ignoré, pas refusé.** NetBox renvoie alors **toute** la collection,
> avec un `HTTP 200`. Un nom de paramètre erroné ne produit donc pas une erreur mais une réponse
> fausse, ce qui est bien pire. Les noms ci-dessous sont ceux du plugin, vérifiés.

Les filtres portant sur un **attribut** du référentiel sont les plus solides : ils survivent au
renommage d'une valeur.

| Question | Filtre |
|---|---|
| Quelles applications ont des comptes hors révocation centralisée ? | `?authentication_centralized=false` |
| Lesquelles rendent réellement le service ? | `?operational=true` |
| Quels déploiements sont en production ? | `/deployments/?production=true` |

Les filtres par valeur attendent un **identifiant**, pas un slug :

| Question | Filtre |
|---|---|
| Quelles applications utilisent telle authentification ? | `?authentication_id=<id>` |
| Lesquelles ont un déploiement dans cet environnement ? | `?environment_id=<id>` |
| Lesquelles traitent des données personnelles ? | `?personal_data=true` |
| Lesquelles relèvent de tel service métier ? | `?business_contact=direction-rh` — recherche **partielle**, par domaine ou par service |
| Quels déploiements sont exposés à l'externe ? | `/deployments/?external_facing=true` |

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

**L'intégration continue va plus loin que le lint**, parce que le lint n'a jamais rien vu des
défauts réels de ce plugin. À chaque poussée, dans un NetBox réel avec sa base :

| Contrôle | Ce qu'il attrape |
|---|---|
| Les migrations s'appliquent | un modèle et une migration qui divergent |
| Toutes les couleurs sont hexadécimales | une migration de données n'appelle pas `full_clean()` : elle écrit sans valider |
| **Les trois règles sont éprouvées** | cinq cas, dont **deux qui doivent être acceptés** — un garde-fou trop large est aussi faux qu'un garde-fou absent |
| **Les 48 pages sont parcourues** | une vue en erreur 500, ou du texte de gabarit fuitant dans le HTML |

> Le dernier point n'est pas du zèle. Rendre un gabarit isolément ne prouve rien : une version a
> livré dix pages en erreur 500 alors que ses gabarits se rendaient parfaitement. **Un contrôle
> doit emprunter le chemin de l'utilisateur.**

**Il n'y a pas encore de tests unitaires** — c'est le manque le plus net du projet.

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
