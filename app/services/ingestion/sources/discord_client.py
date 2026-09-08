import httpx

from app.config import settings


class ConfigurationDiscordManquante(Exception):
    """
    Levée quand le token du bot Discord n'est pas configuré.
    """


def _verifier_configuration() -> None:
    if not settings.discord_bot_token:
        raise ConfigurationDiscordManquante(
            "DISCORD_BOT_TOKEN n'est pas configuré. "
            "Le token du bot Discord doit être fourni avant "
            "de pouvoir lire les messages d'un salon."
        )


async def lire_messages_discord(
    channel_id: str,
    limite: int = 100,
) -> list[dict]:
    """
    Récupère les derniers messages d'un salon Discord via
    l'API REST officielle, en utilisant un bot déjà invité
    sur le serveur.
    """
    _verifier_configuration()

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

    headers = {
        "Authorization": f"Bot {settings.discord_bot_token}",
    }

    async with httpx.AsyncClient() as client:
        reponse = await client.get(
            url, headers=headers, params={"limit": limite}
        )
        reponse.raise_for_status()
        return reponse.json()