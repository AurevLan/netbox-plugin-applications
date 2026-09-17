"""Serveur virtuel — le point d'entrée réseau devant une instance.

CE QUE C'EST. Sur un répartiteur de charge ou un pare-feu applicatif, un
« serveur virtuel » est l'écoute exposée aux clients : une adresse IP, un port,
et les traitements qu'on y applique — dont le WAF.

POURQUOI UN OBJET ET NON UN CHAMP TEXTE SUR LE DÉPLOIEMENT. Le même serveur
virtuel sert souvent plusieurs déploiements, et c'est son ADRESSE qui compte en
incident : « qui répond sur cette IP ? » est la question qu'on pose quand une
alerte tombe. Un nom saisi à la main dans chaque fiche ne répond à rien et
diverge à la première faute de frappe.

LE PRÉFIXE N'EST PAS STOCKÉ. NetBox sait déjà quel préfixe contient une adresse :
le dupliquer ici créerait une seconde vérité, fausse dès le premier
redécoupage. Il est calculé à l'affichage.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel


class VirtualServer(NetBoxModel):
    """Une écoute sur un répartiteur ou un pare-feu applicatif."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")

    # PROTECT : supprimer l'adresse d'un serveur virtuel en service laisserait
    # une écoute sans point d'entrée, et personne ne s'en apercevrait.
    ip_address = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.PROTECT,
        related_name="virtual_servers",
        verbose_name="Adresse IP",
        help_text="L'adresse sur laquelle le service répond aux clients.",
    )
    port = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name="Port",
        help_text="Port d'écoute, par exemple 443.",
    )

    description = models.CharField(max_length=200, blank=True, verbose_name="Description")
    comments = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        ordering = ("name",)
        verbose_name = "serveur virtuel"
        verbose_name_plural = "serveurs virtuels"

    @property
    def _adresse_seule(self):
        """L'adresse sans son masque.

        Deux formes possibles, et elles ne se comportent pas pareil : objet
        réseau une fois relu de la base, simple chaîne « 10.0.0.1/24 » tant que
        l'instance vient d'être construite.
        """
        brute = self.ip_address.address
        return str(getattr(brute, "ip", None) or str(brute).split("/")[0])

    def __str__(self):
        # « address » est un objet réseau une fois relu de la base, mais une
        # simple chaîne tant que l'instance vient d'être construite en mémoire.
        # Un __str__ qui lève casse les journaux, l'administration et les
        # messages d'erreur — c'est-à-dire précisément ce qu'on lit quand
        # quelque chose va mal.
        adresse = self._adresse_seule
        if self.port:
            return f"{self.name} ({adresse}:{self.port})"
        return f"{self.name} ({adresse})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_applications:virtualserver", args=[self.pk])

    @property
    def prefix(self):
        """Le préfixe qui contient l'adresse — calculé, jamais stocké.

        Renvoie le plus spécifique : plusieurs préfixes peuvent contenir une
        même adresse, et c'est le plus étroit qui décrit son segment réel.
        """
        from ipam.models import Prefix

        # Le tri se fait en Python, pas en base : « order_by » sur
        # « net_mask_length » est accepté sans erreur et NE TRIE PAS — un /24
        # ressortait devant un /29. Les préfixes contenant une même adresse se
        # comptent sur les doigts d'une main ; les trier ici ne coûte rien et
        # donne le bon résultat.
        # L'ADRESSE SEULE, sans son masque. Interroger avec « 10.90.0.10/24 »
        # revient à demander quels préfixes contiennent le RÉSEAU /24 — ce
        # qu'aucun /29 ne peut faire, alors qu'il contient bien l'adresse.
        candidats = Prefix.objects.filter(prefix__net_contains_or_equals=self._adresse_seule)
        return max(candidats, key=lambda p: p.prefix.prefixlen, default=None)
