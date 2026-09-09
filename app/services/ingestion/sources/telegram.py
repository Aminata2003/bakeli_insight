from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class TelegramConnecteur(ConnecteurIngestion):
    """
    Connecteur Telegram.

    Alimenté via la méthode getUpdates de l'API Bot Telegram
    (récupération périodique des messages du/des groupe(s)
    communautaires Bakeli).
    """

    plateforme_code = "telegram"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for update in self.donnees:
            message = update.get("message") or update.get("channel_post")

            if not message:
                continue

            texte = message.get("text", "")

            if not texte:
                continue

            auteur = message.get("from", {})

            resultat.append(
                DonneeIngestion(
                    plateforme_code=self.plateforme_code,
                    source_id=str(message.get("message_id", "")),
                    texte=str(texte),
                    auteur_prenom=auteur.get("first_name"),
                    auteur_nom=auteur.get("last_name"),
                    metadata=update,
                )
            )

        return resultat