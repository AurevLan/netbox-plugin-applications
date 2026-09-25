"""Catalogue applicatif CMDB pour NetBox : applications et déploiements."""

from netbox.plugins import PluginConfig


class ApplicationsConfig(PluginConfig):
    name = "netbox_applications"
    verbose_name = "Applications"
    description = (
        "Fiche applicative au sens CMDB : client, criticité, engagements de continuité, "
        "déploiements par environnement, machines et pare-feu applicatif."
    )
    version = "0.13.0"
    author = "Aurelien"
    base_url = "applications"
    # Plancher ÉPROUVÉ, pas supposé : la suite complète a été exécutée sur
    # NetBox 4.5.10 et 4.7.0 (voir la matrice d'intégration continue).
    #
    # ⚠️ NetBox N'ARRÊTE PAS le démarrage si cette contrainte n'est pas
    # satisfaite : il émet un avertissement et charge le reste. Le menu
    # n'apparaît pas, et rien dans l'interface ne dit pourquoi.
    min_version = "4.5.0"


config = ApplicationsConfig
