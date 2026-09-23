"""Catalogue applicatif CMDB pour NetBox : applications et déploiements."""

from netbox.plugins import PluginConfig


class ApplicationsConfig(PluginConfig):
    name = "netbox_applications"
    verbose_name = "Applications"
    description = (
        "Fiche applicative au sens CMDB : client, criticité, engagements de continuité, "
        "déploiements par environnement, machines et pare-feu applicatif."
    )
    version = "0.12.0"
    author = "Aurelien"
    base_url = "applications"
    # Contrainte de version : si une montée de NetBox casse l'API plugin, le
    # démarrage échoue EXPLICITEMENT plutôt que de produire un comportement
    # imprévisible. Le coût d'un plugin est ainsi rendu visible, pas caché.
    min_version = "4.7.0"


config = ApplicationsConfig
