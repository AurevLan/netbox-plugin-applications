"""Modèles du catalogue applicatif.

reference.py    les référentiels — listes de valeurs gérées dans l'interface
application.py  la fiche applicative et ses déploiements
"""

from .application import Application, Deployment
from .reference import (
    RPO,
    RTO,
    AuthenticationMethod,
    Criticality,
    DataClassification,
    DeploymentStatus,
    Environment,
    LifecycleStatus,
    MaintenanceWindow,
    ServiceHours,
)

__all__ = (
    "RPO",
    "RTO",
    "Application",
    "AuthenticationMethod",
    "Criticality",
    "DataClassification",
    "Deployment",
    "DeploymentStatus",
    "Environment",
    "LifecycleStatus",
    "MaintenanceWindow",
    "ServiceHours",
)

# Les référentiels, dans l'ordre où ils sont présentés dans le menu.
# Cette liste évite de répéter dix fois la même énumération dans les vues,
# les URL et la navigation.
REFERENCES = (
    LifecycleStatus,
    Criticality,
    RTO,
    RPO,
    ServiceHours,
    DataClassification,
    AuthenticationMethod,
    Environment,
    DeploymentStatus,
    MaintenanceWindow,
)
