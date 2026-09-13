# Journal des versions

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).
Versionnage : [SemVer](https://semver.org/lang/fr/).

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
