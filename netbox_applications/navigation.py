"""Menu de premier niveau « Applications ».

C'est l'une des raisons d'être du plugin. Sans lui, une fiche applicative
n'aurait pu être portée que par un objet NetBox détourné — un « Tenant »
assorti de champs personnalisés — dont le menu se serait appelé « Tenancy »
et le champ client « Group », libellés qu'aucun réglage ne change.
"""

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

application_item = PluginMenuItem(
    link="plugins:netbox_applications:application_list",
    link_text="Applications",
    permissions=["netbox_applications.view_application"],
    buttons=(
        PluginMenuButton(
            link="plugins:netbox_applications:application_add",
            title="Ajouter une application",
            icon_class="mdi mdi-plus-thick",
            permissions=["netbox_applications.add_application"],
        ),
    ),
)

deployment_item = PluginMenuItem(
    link="plugins:netbox_applications:deployment_list",
    link_text="Déploiements",
    permissions=["netbox_applications.view_deployment"],
    buttons=(
        PluginMenuButton(
            link="plugins:netbox_applications:deployment_add",
            title="Ajouter un déploiement",
            icon_class="mdi mdi-plus-thick",
            permissions=["netbox_applications.add_deployment"],
        ),
    ),
)

menu = PluginMenu(
    label="Applications",
    groups=(("Catalogue applicatif", (application_item, deployment_item)),),
    icon_class="mdi mdi-apps",
)
