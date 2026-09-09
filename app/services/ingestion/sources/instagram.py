from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class InstagramConnecteur(ConnecteurIngestion):
    """
    Connecteur Instagram (commentaires sur les publications
    officielles Bakeli, via l'API Graph Meta).
    """

    plateforme_code = "instagram"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for commentaire in self.donnees:
            texte = commentaire.get("text", "")

            if not texte:
                continue

            resultat.append(
                DonneeIngestion(
                    plateforme_code=self.plateforme_code,
                    source_id=str(commentaire.get("id", "")),
                    texte=str(texte),
                    auteur_prenom=commentaire.get("username"),
                    auteur_nom=None,
                    metadata=commentaire,
                )
            )

        return resultat