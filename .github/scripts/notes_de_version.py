"""Extrait du CHANGELOG la section d'une version, pour en faire les notes de release.

POURQUOI NE PAS RÉÉCRIRE LES NOTES À LA MAIN. Elles existent déjà, relues et
versionnées, dans CHANGELOG.md. Les retaper au moment de publier produirait deux
récits de la même version, qui divergeraient dès la première correction.

L'ABSENCE DE SECTION EST UN ÉCHEC, pas un cas à contourner : publier une version
que le journal ne décrit pas revient à livrer sans dire ce qui change.
"""

import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage : notes_de_version.py <version>")

version = sys.argv[1].lstrip("v")

with open("CHANGELOG.md", encoding="utf-8") as fichier:
    texte = fichier.read()

# On s'arrête au titre de version suivant, ou à la fin du fichier.
motif = rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
trouve = re.search(motif, texte, re.S | re.M)

if not trouve:
    raise SystemExit(
        f"Aucune section « ## [{version}] » dans CHANGELOG.md.\n"
        "Le journal des versions doit décrire la version AVANT qu'elle ne soit publiée."
    )

print(trouve.group(1).strip())
