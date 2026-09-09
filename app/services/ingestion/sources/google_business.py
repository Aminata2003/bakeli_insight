from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class GoogleBusinessConnecteur(ConnecteurIngestion):
    """
    Connecteur Google Business Profile (avis étoilés des campus).
    """

    plateforme_code = "google_business"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for avis in self.donnees:
            texte = (
                avis.get("comment")
                or ""
            )

            reviewer = avis.get("reviewer", {})

            resultat.append(
                DonneeIngestion(
                    plateforme_code=self.plateforme_code,
                    source_id=str(avis.get("reviewId", "")),
                    texte=str(texte),
                    auteur_prenom=reviewer.get("displayName"),
                    auteur_nom=None,
                    metadata=avis,
                )
            )

        return resultat