# Journal des versions

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Versionnage : [SemVer](https://semver.org/lang/fr/).

## [0.4.0] — 2026-09-13

### Changé — modification structurante

- **Les dix listes de valeurs deviennent des objets NetBox à part entière**, gérables dans
  l'interface : leur propre page, un bouton « Ajouter », une suppression refusée si la valeur
  est employée.
  Ajouter « CAS » ou une fenêtre de maintenance propre à un client ne demande plus de modifier
  la configuration du serveur ni de le redémarrer.
- **Chaque référentiel porte des attributs, pas seulement un libellé.** Une convention tacite
  devient une donnée interrogeable :

  | Référentiel | Attribut | Ce qu'il permet |
  |---|---|---|
  | Authentification | `is_centralized` | « quelles applications ont des comptes échappant à la révocation ? » — sans supposer que la valeur s'appelle « locale » |
  | RTO, RPO | `minutes` | comparer et trier : « RPO inférieur à 2 heures » devient une requête |
  | Criticité | `incident_priority`, `requires_oncall` | relier la fiche au traitement des incidents |
  | Classification | `level`, `requires_encryption` | « au moins confidentiel » devient une requête |
  | Environnement | `is_production` | des règles plus strictes, sans liste de noms à maintenir |
  | Statut de service | `is_operational` | « réellement en service », quel que soit le libellé |
  | Maintenance, horaires | heures de début et de fin | exploitables par un script |

- Les filtres interrogent désormais ces attributs : `?authentication_centralized=false`,
  `?operational=true`, `?production=true`.

### Migration

Trois étapes, **aucune donnée perdue** : création des référentiels, transfert des valeurs,
puis nettoyage. Les valeurs existantes sont reprises avec leurs libellés et leurs couleurs.
Une valeur inconnue du plugin — ajoutée par `FIELD_CHOICES` — donne lieu à un référentiel créé
à la volée plutôt qu'à une perte silencieuse.

Vérifié sur une copie d'une base réelle avant publication.

### Retiré

- `FIELD_CHOICES` n'est plus nécessaire pour ce plugin : les valeurs vivent en base.
  Le fichier `choices.py` disparaît.

## [0.3.0] — 2026-09-13

### Ajouté

- **Les listes déroulantes sont extensibles par configuration.** Chaque `ChoiceSet` déclare
  désormais une clé, ce qui permet d'ajouter ou de remplacer des choix via `FIELD_CHOICES`
  **sans modifier le code du plugin ni attendre une version**. Un redémarrage suffit.
- Filtres supplémentaires sur les applications : RTO, RPO, horaires de service, client,
  référents, et **environnement de déploiement** — ce dernier traverse la relation et répond à
  « quelles applications sont en production ? ».

### Corrigé

- **Les filtres étaient présents mais introuvables.** Sans `fieldsets`, NetBox les affichait à
  la suite, sans titre ni regroupement, mêlés à `filter_id` et `q`. Des filtres qu'on ne trouve
  pas reviennent à ne pas en avoir. Ils sont désormais groupés par section — dont une section
  **Sécurité** qui porte l'authentification.

## [0.2.1] — 2026-09-13

### Corrigé

- **Le panneau « Déploiements » affichait du texte parasite et des objets Python.**
  Deux causes, invisibles à l'analyse statique :
  - un commentaire `{# … #}` écrit sur **plusieurs lignes** — la syntaxe de Django est
    **monoligne**, si bien que seule la première était consommée et le reste s'affichait ;
  - `linkify:"get_environment_display"` — le filtre fait un `getattr`, qui sur une **méthode**
    retourne l'objet méthode : d'où les `functools.partial` affichés dans la colonne
    Environnement.

### Ajouté

- **L'intégration continue rend désormais réellement les gabarits** et échoue s'ils contiennent
  du texte parasite (`{#`, `{{`, `functools.partial`…). C'est le contrôle qui aurait attrapé le
  bug ci-dessus : aucun lint ne le voyait.

## [0.2.0] — 2026-09-13

### Corrigé

- **L'URL d'accès d'un déploiement n'était visible nulle part.** Elle existait bien par
  environnement, mais n'apparaissait ni dans le panneau « Déploiements » de la fiche
  application, ni dans les colonnes par défaut de la liste. Il fallait ouvrir chaque
  déploiement pour la voir — ce qui donnait l'impression qu'il n'y avait **qu'une seule URL**,
  celle de la production.
  Elle figure désormais aux deux endroits.

### Modifié

- **`Deployment.url` renommé en `Deployment.access_url`.** L'ancien nom entrait en collision
  avec le champ `url` hypermedia que NetBox expose sur chaque objet, ce qui imposait un
  contournement dans le sérialiseur. Le renommage supprime la cause plutôt que de la contourner.
  Migration `RenameField` : **les données existantes sont préservées**.
- Le panneau « Déploiements » de la fiche application affiche désormais environnement, statut,
  URL, plage de maintenance, exposition externe et nombre de VM — au lieu de quatre colonnes
  sans en-têtes.

### Documentation

- Procédure d'installation `netbox-docker` réécrite : trois fichiers à créer, une commande,
  une vérification, et un tableau de résolution des incidents. La version précédente montrait
  un `COPY` depuis un répertoire local, ce qui n'a aucun sens pour qui installe le plugin.
- Installation classique complétée : déclaration dans `configuration.py`, redémarrage du worker,
  et surtout l'ajout à `local_requirements.txt` — sans lui, `upgrade.sh` de NetBox recrée
  l'environnement virtuel et le plugin disparaît **sans message d'erreur**.
- Correction : `pip install netbox-plugin-applications` était indiqué alors que le paquet n'est
  pas publié sur PyPI. La commande aurait échoué.

## [0.1.0] — 2026-09-13

### Ajouté

- Modèle **Application** : identité, client, cycle de vie, criticité, RTO, RPO, horaires de
  service, classification des données, RGPD, système d'authentification, référents technique
  et chef de projet, documentation.
- Modèle **Deployment** : une instance par environnement, avec sa plage de maintenance, son
  exposition externe, son URL d'accès et ses VM.
- **Identifiant applicatif** `APP-0000` attribué automatiquement à la création.
- Menu **Applications** de premier niveau, onglet **Déploiements** sur la fiche d'application.
- API REST complète pour les deux modèles, avec filtres.
- Filtre des applications **par environnement de déploiement**, traversant la relation.

### Garanties

- **Unicité `(application, environnement)`** : deux déploiements ne peuvent pas coexister dans
  le même environnement.
- **Refus d'exposer à l'externe** une application traitant des données en diffusion restreinte.
- Suppressions choisies : `PROTECT` sur le client, `SET_NULL` sur les référents,
  `CASCADE` sur les déploiements.
