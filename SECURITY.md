# Politique de sécurité

## Versions suivies

| Version | Suivie |
|---|---|
| 0.1.x | ✅ |

## Signaler une vulnérabilité

**N'ouvrez pas d'issue publique.** Une issue rend la faille visible avant qu'un correctif
n'existe, ce qui expose tous les déploiements.

Utilisez l'onglet **Security → Report a vulnerability** du dépôt GitHub, qui ouvre un canal
privé avec les mainteneurs.

Merci d'indiquer : la version du plugin et de NetBox, les étapes de reproduction, et l'impact
que vous estimez.

Vous recevrez un accusé de réception sous 72 heures.

## Surface d'attaque du plugin

Ce que le plugin **fait** — et donc ce qu'il convient d'examiner :

| Élément | Risque examiné |
|---|---|
| Modèles Django | injection SQL via l'ORM (aucune requête brute n'est écrite) |
| Sérialiseurs API | exposition de champs non prévus |
| Gabarits HTML | injection de contenu — Django échappe par défaut, aucun `safe` n'est utilisé |
| Permissions | chaque vue exige la permission NetBox correspondante |

Ce que le plugin **ne fait pas**, et qui réduit d'autant la surface :

- aucune dépendance tierce déclarée ;
- aucun appel réseau sortant ;
- aucune exécution de commande système ;
- aucune écriture de fichier ;
- aucune désérialisation de données non fiables.

## Contrôles automatisés

À chaque commit et à chaque poussée :

| Outil | Ce qu'il cherche |
|---|---|
| `ruff` (règles `S`) | motifs dangereux dans le code |
| `bandit` | vulnérabilités Python courantes |
| `pip-audit` | vulnérabilités connues des dépendances |
| `detect-secrets` | secrets commités par inadvertance |

## Limite connue

Le plugin déclare `min_version = "4.7.0"`. Une version **antérieure** de NetBox est refusée au
démarrage. Une version **postérieure** n'est pas bloquée : elle peut casser le plugin sans
avertissement. Vérifiez la compatibilité avant toute montée de version majeure de NetBox.
