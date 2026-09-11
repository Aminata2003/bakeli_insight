from datetime import datetime

from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class DiscordConnecteur(ConnecteurIngestion):
    """
    Connecteur Discord.

    Alimenté via l'API REST Discord (récupération périodique
    des messages d'un ou plusieurs salons communautaires).
    """

    plateforme_code = "discord"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for message in self.donnees:
            texte = message.get("content", "")

            # On ignore les messages vides (souvent des messages
            # système, images seules, ou embeds sans texte).
            if not texte:
                continue

            auteur = message.get("author", {})

            resultat.append(
                DonneeIngestion(
                    plateforme_code=self.plateforme_code,
                    source_id=str(message.get("id", "")),
                    texte=str(texte),
                    date_source=_parser_timestamp(
                        message.get("timestamp")
                    ),
                    auteur_prenom=auteur.get("username"),
                    auteur_nom=None,
                    metadata=message,
                )
            )

        return resultat


def _parser_timestamp(valeur: str | None) -> datetime | None:
    """
    Convertit le timestamp ISO 8601 renvoyé par l'API Discord
    (ex: "2026-09-10T09:54:12.123000+00:00") en datetime.

    Sans cette date, l'avis retombe sur une date par défaut très
    ancienne côté frontend, et disparaît silencieusement de tous
    les filtres de période (Aujourd'hui/Semaine/Mois/Année).
    """
    if not valeur:
        return None

    try:
        return datetime.fromisoformat(valeur)
    except ValueError:
        return None