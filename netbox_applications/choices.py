"""Énumérations du plugin.

Les listes de valeurs que l'exploitant gère lui-même sont des RÉFÉRENTIELS
(`models/reference.py`) : il peut en ajouter, les renommer, leur donner une
couleur. Celles de ce fichier sont d'une autre nature — leur valeur porte un
COMPORTEMENT du code, et en ajouter une sans toucher au code ne produirait
rien. Elles sont donc figées ici, et non ouvertes dans l'interface.
"""

from utilities.choices import ChoiceSet


class FlowStatusChoices(ChoiceSet):
    """Où en est un flux entre sa demande et sa mise en œuvre.

    Le cycle importe autant que le flux lui-même : une matrice qui ne distingue
    pas « demandé » de « ouvert » ne dit pas si elle décrit le réseau tel qu'il
    est ou tel qu'on le souhaite — et c'est alors deux documents en un, dont
    aucun n'est fiable.

    « À retirer » existe parce qu'un flux qui n'est plus nécessaire doit rester
    visible jusqu'à sa fermeture effective. Le supprimer de la matrice avant que
    le pare-feu ne soit modifié ferait disparaître la seule trace du travail
    restant.
    """

    key = "Flow.status"

    DEMANDE = "demande"
    OUVERT = "ouvert"
    REFUSE = "refuse"
    A_RETIRER = "a-retirer"
    FERME = "ferme"

    CHOICES = [
        (DEMANDE, "Demandé", "orange"),
        (OUVERT, "Ouvert", "green"),
        (REFUSE, "Refusé", "red"),
        (A_RETIRER, "À retirer", "purple"),
        (FERME, "Fermé", "gray"),
    ]

    # Les états qui décrivent le réseau TEL QU'IL EST. Les autres décrivent une
    # intention. La matrice le signale, et un export vers un pare-feu ne doit
    # jamais confondre les deux.
    EN_VIGUEUR = (OUVERT,)
