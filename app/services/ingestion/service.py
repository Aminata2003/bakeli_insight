from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion
from app.services.ingestion.normalisation import normaliser_donnee


class ServiceIngestion:
    """
    Orchestrateur central de l'ingestion.

    Tous les connecteurs passent par ce service avant
    d'être transmis au reste du pipeline.
    """

    def __init__(self, connecteurs: list[ConnecteurIngestion] | None = None):
        self.connecteurs = connecteurs or []

    def ajouter_connecteur(self, connecteur: ConnecteurIngestion) -> None:
        self.connecteurs.append(connecteur)

    async def recuperer_toutes_les_donnees(self) -> list[DonneeIngestion]:
        donnees_normalisees = []

        for connecteur in self.connecteurs:
            donnees = await connecteur.recuperer()

            for donnee in donnees:
                donnee = normaliser_donnee(donnee)

                # On ignore les entrées complètement vides.
                if not donnee.texte and not donnee.source_id:
                    continue

                donnees_normalisees.append(donnee)

        return donnees_normalisees