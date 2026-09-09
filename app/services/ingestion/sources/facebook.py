from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class FacebookConnecteur(ConnecteurIngestion):
    """
    Connecteur Facebook (commentaires sur les publications
    officielles Bakeli, via l'API Graph Meta).
    """

    plateforme_code = "facebook"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for commentaire in self.donnees:
            texte = commentaire.get("message", "")

            if not texte:
                continue

            auteur = commentaire.get("from", {})

            resultat.append(
                DonneeIngestion(
                    plateforme_code=self.plateforme_code,
                    source_id=str(commentaire.get("id", "")),
                    texte=str(texte),
                    auteur_prenom=auteur.get("name"),
                    auteur_nom=None,
                    metadata=commentaire,
                )
            )

        return resultat