from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DonneeIngestion:
    """
    Format commun produit par tous les connecteurs de sources.

    Exemple :
        Google Forms -> DonneeIngestion
        WhatsApp -> DonneeIngestion
        LinkedIn -> DonneeIngestion
    """

    plateforme_code: str
    source_id: str
    texte: str

    date_source: datetime | None = None

    auteur_nom: str | None = None
    auteur_prenom: str | None = None

    url_source: str | None = None

    metadata: dict[str, Any] | None = None


class ConnecteurIngestion(ABC):
    """
    Contrat commun que chaque source doit respecter.
    """

    plateforme_code: str

    @abstractmethod
    async def recuperer(self) -> list[DonneeIngestion]:
        """
        Récupère les nouvelles données depuis la source.
        """
        raise NotImplementedError

    def nom(self) -> str:
        return self.plateforme_code