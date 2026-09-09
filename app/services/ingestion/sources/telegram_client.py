import httpx

from app.config import settings


class ConfigurationTelegramManquante(Exception):
    """
    Levée quand le token du bot Telegram n'est pas configuré.
    """


def _verifier_configuration() -> None:
    if not settings.telegram_bot_token:
        raise ConfigurationTelegramManquante(
            "TELEGRAM_BOT_TOKEN n'est pas configuré. "
            "Le token du bot Telegram doit être fourni avant "
            "de pouvoir lire les messages d'un salon/groupe."
        )


async def lire_messages_telegram(offset: int | None = None) -> list[dict]:
    """
    Récupère les derniers messages reçus par le bot Telegram
    (méthode getUpdates, en mode polling).

    Le bot doit avoir été ajouté au groupe/canal communautaire
    Bakeli, avec la désactivation du mode "confidentialité"
    (privacy mode) pour pouvoir lire tous les messages du groupe
    et pas seulement les commandes qui lui sont adressées.
    """
    _verifier_configuration()

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"

    params = {"timeout": 0}
    if offset is not None:
        params["offset"] = offset

    async with httpx.AsyncClient() as client:
        reponse = await client.get(url, params=params)
        reponse.raise_for_status()
        data = reponse.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Erreur API Telegram : {data.get('description')}"
        )

    return data.get("result", [])