# netbox-plugin-applications

[![Contrôles](https://github.com/AurevLan/netbox-plugin-applications/actions/workflows/ci.yml/badge.svg)](https://github.com/AurevLan/netbox-plugin-applications/actions/workflows/ci.yml)
[![CodeQL](https://github.com/AurevLan/netbox-plugin-applications/actions/workflows/codeql.yml/badge.svg)](https://github.com/AurevLan/netbox-plugin-applications/actions/workflows/codeql.yml)
[![Scorecard OpenSSF](https://api.scorecard.dev/projects/github.com/AurevLan/netbox-plugin-applications/badge)](https://scorecard.dev/viewer/?uri=github.com/AurevLan/netbox-plugin-applications)
[![Couverture](https://img.shields.io/badge/couverture-98.3%25-brightgreen)](#ce-que-la-cha%C3%AEne-de-contr%C3%B4le-v%C3%A9rifie)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![NetBox](https://img.shields.io/badge/NetBox-%E2%89%A5%204.7.0-blue)](https://netbox.dev)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-green)](LICENSE)

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
| **WAF activé** | un pare-feu applicatif filtre-t-il cette instance ? |
| **Serveur virtuel WAF** | le point d'entrée par lequel le filtrage s'applique — facultatif |
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
- **Le WAF se déclare par déploiement, pas par application.** La production est souvent protégée
  quand la recette ne l'est pas, et c'est exactement cet écart qu'on veut pouvoir constater. Le
  filtre `?expose_sans_waf=true` répond à « qu'est-ce qui est exposé à l'externe sans filtrage ? »
  — une question qui croise deux champs, donc qu'aucun filtre simple ne pose.
- **Contact métier ≠ référent technique.** Les deux référents pointent vers l'annuaire de
  contacts de NetBox ; le responsable métier n'y figure que rarement — c'est souvent un
  responsable de service ou une liste de diffusion. Le champ est donc **libre**, mais son
  **format est imposé** : une adresse de courriel, la seule chose qu'on puisse à la fois valider
  et utiliser en incident. Exiger la création préalable d'un contact ferait laisser le champ
  vide, ce qui est pire qu'une adresse saisie à la main.
- **Authentification « Locale » n'est pas un détail.** Elle signale des comptes **échappant à la
  révocation centralisée**. Le jour où quelqu'un quitte l'organisation, c'est cette liste qu'on
  ouvre.

## Ce que la chaîne de contrôle vérifie

Les badges ci-dessus sont **vivants** : ils reflètent la dernière exécution, pas une déclaration
d'intention. Ce tableau dit ce qui se cache derrière.

| Contrôle | Portée mesurée | Ce qu'il attrape |
|---|---|---|
| **Tests** | **91 tests**, couverture **98,3 %** | les règles du modèle et l'atteignabilité des pages |
| **Parcours des pages** | **48 pages** — liste, création, fiche et édition des 12 modèles | une vue en erreur 500, du texte de gabarit fuitant dans le HTML |
| **Règles métier** | **3 règles**, éprouvées dans les deux sens | un garde-fou muet, ou trop large |
| **Recherche globale** | **12 index**, 5 recherches | des objets invisibles depuis la barre de recherche |
| **Migrations** | appliquées sur une base réelle | un modèle et une migration qui divergent |
| **ruff** | **9 familles de règles** (`E W F I UP B S DJ RUF`) | style, imports, pièges, motifs dangereux |
| **bandit** + **CodeQL** | tout le paquet | motifs dangereux, vulnérabilités d'analyse statique |
| **pip-audit** | dépendances, **aussi chaque lundi** | une vulnérabilité publiée sans qu'on touche au code |
| **detect-secrets** | arbre git complet | un secret commité, ou une détection nouvelle non relue |
| **Scorecard OpenSSF** | pratiques du dépôt | note attribuée par un tiers, selon des critères publics |

### Choix de durcissement

| | Pourquoi |
|---|---|
| **Aucune dépendance d'exécution** | le plugin n'utilise que ce que NetBox fournit : aucune surface d'attaque ajoutée, aucun conflit de version possible avec l'hôte |
| **Actions épinglées par empreinte** | une étiquette `v5` peut être redéplacée vers un commit quelconque, qui s'exécuterait avec nos droits ; une empreinte ne change pas de contenu |
| `permissions: contents: read` | moindre privilège sur tous les workflows |
| **Qualifié sur 3.12, 3.13 et 3.14** | NetBox 4.7 s'exécute sur 3.14 : ne qualifier que sur 3.12 validerait une version que personne n'exécute |
| **Dependabot** | des outils de sécurité épinglés vieillissent, et leurs bases de vulnérabilités avec eux |
| **pre-commit** | ce qui est refusé en intégration continue l'est avant le commit |

### La note Scorecard, et ce qu'elle reproche

**5,6 / 10** au dernier relevé. Le badge est vivant : il change quand le dépôt change. Les points
retirés, et ce qu'on en fait :

| Critère | Note | Décision |
|---|---|---|
| **Branch-Protection** | 0 | à activer — un réglage du dépôt, pas du code |
| **Code-Review** | 0 | projet à un seul mainteneur : aucune revue par un tiers n'est possible aujourd'hui |
| **Packaging** | — | pas de publication PyPI ; l'installation se fait depuis un tag de ce dépôt |
| **Signed-Releases** | — | les artefacts ne sont pas signés |
| **Fuzzing** | 0 | sans objet : le plugin ne traite aucune entrée non fiable, ni format binaire |
| **Security-Policy** | 4 → | politique enrichie : délais d'engagement, versions suivies |
| **Pinned-Dependencies** | 4 → | actions épinglées par empreinte depuis la 0.8.0 ; la note suit au prochain relevé |
| Token-Permissions, SAST, Vulnerabilities, License, Dangerous-Workflow, Dependency-Update-Tool | 9-10 | |

**Un critère à 0 n'est pas toujours un défaut à corriger.** « Code-Review » mesure la revue par
un tiers : sur un projet à un mainteneur, l'exiger reviendrait à se relire soi-même dans une
interface différente. C'est dit ici plutôt que maquillé.

### Ce qui n'est pas couvert

Dit ici plutôt que découvert à l'usage :

- **Pas de publication PyPI** — l'installation se fait depuis ce dépôt, à un tag figé.
- **Pas de SBOM ni de provenance signée** — le paquet se construit, se vérifie avec `twine`, mais
  n'est pas attesté.
- **Pas de vérification de types** — NetBox ne publie pas de stubs ; un `mypy` sans eux
  produirait surtout du bruit.
- **La couverture porte sur le code du plugin**, migrations et tests exclus.

> **Ce que 98 % ne veulent PAS dire.** La couverture mesure des lignes exécutées, pas des
> comportements éprouvés. Une bonne part de ce chiffre vient du simple chargement du plugin :
> ces modules construisent leurs vues, tables et sérialiseurs par des fabriques exécutées à
> l'import. Le nombre serait élevé même sans un seul test.
>
> **Ce qui vaut, ce sont les tests de règles** — ceux qui tentent une opération interdite et
> vérifient qu'elle est refusée, puis une opération légitime et vérifient qu'elle passe. Le seuil
> de 95 % sert à repérer une baisse, pas à prouver une qualité.

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
| `Could not resolve host` / `Temporary failure in name resolution` à la construction | réseau fermé — voir [Sans accès à un dépôt distant](#sans-accès-à-un-dépôt-distant-pendant-la-construction) |
| `error: Multiple files match pattern` sur le `COPY` de la roue | deux roues dans le répertoire : n'en garder qu'une |
| **La recherche ne reflète pas les modifications** | `netbox-worker` sans le plugin : il traite la tâche d'indexation sans savoir indexer ces objets, **et sans erreur** |
| Démarrage déclaré `unhealthy` | `start_period` trop court sur une machine lente |
| Le plugin **recule de version** sans erreur | une valeur de repli sur `PLUGIN_VERSION` (`${PLUGIN_VERSION:-v0.1.0}`) : la variable manquante fait construire une version ancienne, sous le nom d'image attendu. Préférer `${PLUGIN_VERSION:?}`, qui **arrête** la commande |

### Sans accès à un dépôt distant pendant la construction

Sur un réseau fermé, la construction précédente échoue deux fois : `apt-get` ne joint pas les
dépôts Debian, et `uv pip` ne joint pas GitHub. La parade tient en une phrase : **on apporte le
paquet déjà construit**.

C'est possible sans contorsion parce que **le plugin ne déclare aucune dépendance d'exécution**.
Une roue (`.whl`) s'installe donc entièrement hors ligne — rien à résoudre, rien à télécharger.

#### 1. Produire la roue, là où le réseau existe

```bash
git clone https://github.com/AurevLan/netbox-plugin-applications
cd netbox-plugin-applications
git checkout v0.11.0

python -m pip install build
python -m build --wheel
```

Résultat : `dist/netbox_plugin_applications-0.11.0-py3-none-any.whl`, **91 Kio**. C'est ce
fichier qu'on transporte — clé USB, dépôt interne, partage de fichiers.

> **Ni Python ni réseau sur la machine de construction ?** L'intégration continue conserve la
> roue en artefact à chaque poussée — onglet *Actions* → une exécution de *Contrôles* → artefact
> **`paquet`**, disponible 90 jours. On la télécharge depuis un poste connecté et on la
> transporte.

#### 2. La placer à côté du Dockerfile

```
mon-netbox-docker/
├── Dockerfile-plugins
└── netbox_plugin_applications-0.11.0-py3-none-any.whl
```

#### 3. Un Dockerfile qui ne sort pas

```dockerfile
ARG NETBOX_IMAGE_TAG=v4.7-5.1.1
FROM netboxcommunity/netbox:${NETBOX_IMAGE_TAG}

USER root

# Ni git, ni dépôt distant : la roue est déjà là.
# « uv pip » et non « pip » : l'image officielle installe avec uv, et son
# environnement virtuel n'embarque PAS pip.
COPY netbox_plugin_applications-*.whl /tmp/
RUN uv pip install --no-cache /tmp/netbox_plugin_applications-*.whl \
 && rm -f /tmp/netbox_plugin_applications-*.whl

USER 999
```

Trois différences avec la version connectée, et chacune compte :

| | Version connectée | Version hors ligne |
|---|---|---|
| `apt-get install git` | nécessaire | **supprimé** — plus rien à cloner |
| Source du paquet | `git+https://…@tag` | un fichier local |
| Version installée | portée par le tag | **portée par le nom du fichier** |

#### 4. Construire, en s'interdisant le réseau

```bash
docker build --network none -t netbox-with-plugins:latest .
```

`--network none` n'est pas une précaution de style : c'est ce qui **prouve** que la construction
ne dépend d'aucun accès. Sans ce drapeau, une construction qui réussit sur un poste connecté
peut échouer sur le réseau cible, et on ne le découvre qu'à ce moment-là.

#### 5. Vérifier avant de déployer

```bash
docker run --rm --network none netbox-with-plugins:latest \
  python -c "from importlib.metadata import version; print(version('netbox-plugin-applications'))"
```

✅ **Éprouvé le 2026-09-23** sur l'image `netboxcommunity/netbox:v4.7-5.1.1` :

| Contrôle | Résultat |
|---|---|
| Construction avec `--network none` | ✅ réussie |
| Version installée | ✅ `0.11.0` |
| Gabarits HTML embarqués | ✅ présents |
| Migrations embarquées | ✅ 10 |
| `manage.py check` avec le plugin activé | ✅ *System check identified no issues* |

#### Ce qui reste à faire à chaque montée de version

**Reconstruire la roue et la recopier.** C'est le coût de cette méthode : la version n'est plus
tirée d'un tag, elle est portée par un fichier qu'un humain déplace. Gardez le numéro de version
dans le nom du fichier — c'est la seule trace de ce qui a réellement été installé.

> **Le piège à connaître** : si l'ancienne roue reste à côté de la nouvelle, le motif
> `netbox_plugin_applications-*.whl` en désigne deux et la construction échoue — ou pire,
> installe la mauvaise. Un seul fichier dans le répertoire, toujours.

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

### Déclarer une application

**Applications → Démarrer** ouvre directement l'assistant. Le même bouton
**« Déclarer une application »** figure sur la liste des applications. Dans les deux cas, une
fenêtre s'ouvre au premier plan pour un **remplissage guidé en quatre temps** :

| Étape | Ce qu'on demande, et pourquoi |
|---|---|
| **1. L'application** | nom, client, contact métier — ce qui identifie le service |
| **2. Les engagements** | criticité, RTO, RPO, horaires, avec leur sens en une phrase |
| **3. Sécurité et données** | classification, RGPD, authentification |
| **4. Le premier déploiement** | **l'étape qui compte** : une application qui ne tourne nulle part ne se surveille pas |

L'application et son premier déploiement sont créés **dans une seule transaction**. Un refus du
modèle à la dernière étape — l'exposition externe d'une donnée restreinte, par exemple —
n'écrit **rien** : sans cela, le refus laisserait exactement l'application orpheline que
l'assistant existe pour éviter.

Le formulaire complet reste accessible par le bouton **Add**, pour qui sait déjà ce qu'il fait.

### Par où commencer

Le menu **Applications** s'ouvre sur **Démarrer** — un parcours guidé qui explique le modèle en
une minute, puis **regarde l'état réel de votre catalogue** :

- combien d'applications, de déploiements, de valeurs de référentiel ;
- **quelles applications n'ont encore aucun déploiement** ;
- **quels déploiements ne sont rattachés à aucune machine** ;
- **quelles machines ne servent aucun déploiement** — le même oubli, vu de l'autre bout.

C'est ce dernier point qui le rend utile bien après la première prise en main : la page est une
liste de ce qui est resté à moitié fait. Elle rappelle aussi ce que veulent dire RTO, RPO,
horaires de service et authentification « locale » — les quatre mots qui arrêtent tout le monde.

### Interface

Menu **Applications**, en deux groupes :

- **Catalogue** — *Démarrer*, *Applications* et *Déploiements*, ce qu'on consulte tous les jours.
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
| **Qu'est-ce qui est exposé sans pare-feu applicatif ?** | `/deployments/?expose_sans_waf=true` |
| Quels déploiements passent par ce serveur virtuel ? | `/deployments/?waf_virtual_server_id=<id>` |

---

## Développement

### Mise en place

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

### Contrôles

```bash
# Les tests — dans un environnement NetBox, ils ont besoin de sa base
python manage.py test netbox_applications

# Avec la mesure de couverture, comme en intégration continue
coverage run --source=netbox_applications --omit='*/migrations/*,*/tests/*' \
  manage.py test netbox_applications
coverage report --precision=1 --fail-under=95

# Qualité et sécurité, sans base de données
ruff check .             # style, imports, pièges courants, motifs dangereux
ruff format --check .    # formatage
bandit -c pyproject.toml -r netbox_applications
pip-audit --skip-editable   # vulnérabilités des dépendances
detect-secrets scan --baseline .secrets.baseline
```

> **`--keepdb` change tout sur une petite machine.** Créer la base de test de NetBox exécute
> toutes ses migrations : plusieurs dizaines de minutes sur 1 vCPU, jusqu'à l'épuisement
> mémoire. Une fois la base créée, la suite s'exécute en une quarantaine de secondes :
>
> ```bash
> python manage.py test netbox_applications --keepdb
> ```

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
