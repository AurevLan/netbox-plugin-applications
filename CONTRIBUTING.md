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
