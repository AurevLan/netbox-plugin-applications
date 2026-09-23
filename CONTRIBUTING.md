# Contribuer

## Avant d'écrire du code

Ouvrez une issue décrivant le besoin. Un champ ajouté est un champ que quelqu'un devra
remplir : mieux vaut discuter de son utilité avant de l'implémenter.

## Mise en place

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

## Règles

1. **Un champ doit répondre à une question d'exploitation**, pas seulement documenter.
   L'authentification est dans le modèle parce que « Locale » signale des comptes échappant à
   la révocation centralisée — pas pour faire joli dans une fiche.
2. **Ce qui décrit le service va sur `Application`** ; ce qui décrit une instance va sur
   `Deployment`. Un attribut placé du mauvais côté produit une erreur qui ne se voit qu'en
   incident.
3. **Les libellés sont en français**, les identifiants techniques en anglais.
4. **Toute modification du modèle exige une migration.** Générer la migration **avant** de
   reconstruire l'image : l'ordre inverse échoue silencieusement.
5. Les contrôles (`ruff`, `bandit`, `pip-audit`, `detect-secrets`) doivent passer.

## Validation

```bash
ruff check . && ruff format --check .
bandit -c pyproject.toml -r netbox_applications
pip-audit
```

## Messages de commit

En français, à l'impératif, expliquant **pourquoi** plutôt que *quoi* — le diff dit déjà quoi.

## Publier une version

Tout part du **tag**. La pose d'un tag `vX.Y.Z` déclenche la construction, la release GitHub et,
si elle est activée, la publication PyPI.

```bash
# 1. La version, aux DEUX endroits qui la déclarent
#    (un contrôle refuse la publication si le tag ne leur correspond pas)
vim pyproject.toml netbox_applications/__init__.py

# 2. Le CHANGELOG décrit la version AVANT qu'elle existe :
#    les notes de release en sont extraites telles quelles.
vim CHANGELOG.md        # ## [X.Y.Z] — AAAA-MM-JJ

# 3. Vérifier que l'intégration continue est VERTE avant de taguer
#    (convention du projet amont, § 5 quinquies — et elle a déjà été enfreinte)

# 4. Publier
git tag -a vX.Y.Z -m "X.Y.Z — en une ligne"
git push origin main --follow-tags
```

La release porte **la roue en pièce jointe**. C'est elle qu'on télécharge pour installer le
plugin sur un réseau fermé, sans compte et sans date d'expiration.

### Activer la publication PyPI

Elle est câblée mais **sautée** tant qu'on ne l'a pas activée — un job rouge en permanence finit
par ne plus être lu.

1. Sur **PyPI**, créer un *pending publisher* : *Your projects → Publishing* →
   propriétaire `AurevLan`, dépôt `netbox-plugin-applications`, workflow `publication.yml`,
   environnement `pypi`.
2. Sur **GitHub**, *Settings → Environments* → créer l'environnement `pypi`.
3. Une variable `PUBLIER_SUR_PYPI` = `oui`, **au choix** :
   - *Settings → Secrets and variables → Actions → onglet **Variables*** → *New repository
     variable* — portée dépôt ;
   - ou sur l'environnement `pypi` lui-même — *Settings → Environments → pypi → Variables*.

   > **Une *Variable*, pas un *Secret*.** Les deux onglets sont voisins ; un secret n'est jamais
   > lisible d'une condition. Et la comparaison est stricte : `Oui`, `OUI` ou un espace en trop
   > ne correspondent pas.

**Aucun jeton à créer, à stocker ni à faire tourner** : PyPI reconnaît le dépôt, le workflow et
l'environnement, et délivre un jeton éphémère à chaque publication.
