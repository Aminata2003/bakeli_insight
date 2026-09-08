import httpx

from app.config import settings


class ConfigurationTypeformManquante(Exception):
    """
    Levée quand le token API Typeform n'est pas configuré.
    """


def _verifier_configuration() -> None:
    if not settings.typeform_api_token:
        raise ConfigurationTypeformManquante(
            "TYPEFORM_API_TOKEN n'est pas configuré. "
            "Le token API Typeform doit être fourni avant de "
            "pouvoir récupérer les réponses."
        )


async def lire_reponses_typeform(form_id: str) -> list[dict]:
    """
    Récupère les réponses d'un formulaire Typeform via l'API
    officielle (Responses API), de façon périodique/à la demande —
    conformément au cahier des charges.
    """
    _verifier_configuration()

    url = f"https://api.typeform.com/forms/{form_id}/responses"

    headers = {
        "Authorization": f"Bearer {settings.typeform_api_token}",
    }

    async with httpx.AsyncClient() as client:
        reponse = await client.get(
            url, headers=headers, params={"page_size": 1000}
        )
        reponse.raise_for_status()
        data = reponse.json()

    return data.get("items", [])