"""Tests du plugin.

POURQUOI DES TESTS ICI ET PAS SEULEMENT EN INTÉGRATION CONTINUE.

Les contrôles du plugin vivaient dans des scripts noyés au fil du YAML de la
CI : ni versionnés comme du code, ni exécutables localement, ni mesurables.
Trois d'entre eux échouaient depuis toujours sans que personne le voie.

Ce sont désormais des tests Django ordinaires. Ils s'exécutent par :

    python manage.py test netbox_applications

CE QUI EST ÉPROUVÉ ICI, ce sont les RÈGLES — celles que le modèle doit rendre
impossibles à enfreindre — et l'ATTEIGNABILITÉ — pages qui s'affichent, filtres
qui filtrent, recherche qui trouve. Ce sont les deux familles de défauts que ce
plugin a réellement connues.

Chaque règle est éprouvée DANS LES DEUX SENS : un cas qui doit être refusé et
un cas qui doit être accepté. Un contrôle trop large est aussi faux qu'un
contrôle absent.
"""
