"""Menu « Applications ».

Deux groupes distincts, et c'est délibéré : le catalogue est ce qu'on consulte
tous les jours, les référentiels ce qu'on modifie rarement. Les mélanger
noierait les deux entrées utiles sous dix entrées de configuration.
"""

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

from . import models


def _item(nom_modele, libelle, titre_ajout):
    """Une entrée de menu et son bouton « Ajouter »."""
    n = nom_modele.lower()
    return PluginMenuItem(
        link=f"plugins:netbox_applications:{n}_list",
        link_text=libelle,
        permissions=[f"netbox_applications.view_{n}"],
        buttons=(
            PluginMenuButton(
                link=f"plugins:netbox_applications:{n}_add",
                title=titre_ajout,
                icon_class="mdi mdi-plus-thick",
                permissions=[f"netbox_applications.add_{n}"],
            ),
        ),
    )


catalogue = (
    # En tête : c'est la page qui explique le reste, et celle qui dit ce qui
    # est resté à moitié fait.
    PluginMenuItem(
        link="plugins:netbox_applications:demarrer",
        link_text="Démarrer",
        permissions=["netbox_applications.view_application"],
    ),
    _item("Application", "Applications", "Ajouter une application"),
    _item("Deployment", "Déploiements", "Ajouter un déploiement"),
)

# Les libellés sont explicites : « RTO » seul ne dirait rien à qui ouvre le
# menu sans connaître l'acronyme.
referentiels = (
    _item("LifecycleStatus", "Cycle de vie du service", "Ajouter une étape"),
    _item("Criticality", "Criticités", "Ajouter une criticité"),
    _item("RTO", "RTO — reprise", "Ajouter un RTO"),
    _item("RPO", "RPO — perte de données", "Ajouter un RPO"),
    _item("ServiceHours", "Horaires de service", "Ajouter des horaires"),
    _item("DataClassification", "Classifications", "Ajouter une classification"),
    _item("AuthenticationMethod", "Authentification", "Ajouter une méthode"),
    _item("Environment", "Environnements", "Ajouter un environnement"),
    _item("DeploymentStatus", "États d'instance", "Ajouter un état"),
    _item("MaintenanceWindow", "Plages de maintenance", "Ajouter une plage"),
)

# Un « assert » disparaîtrait avec « python -O » : le contrôle ne garantirait
# alors plus rien. On lève explicitement.
if len(referentiels) != len(models.REFERENCES):
    raise RuntimeError(
        f"Le menu déclare {len(referentiels)} référentiels pour "
        f"{len(models.REFERENCES)} modèles : une entrée manque, ou l'inverse."
    )

menu = PluginMenu(
    label="Applications",
    groups=(
        ("Catalogue", catalogue),
        ("Référentiels", referentiels),
    ),
    icon_class="mdi mdi-apps",
)
