import httpx

from app.config import settings


class ConfigurationGoogleBusinessManquante(Exception):
    """
    Levée quand les credentials Google Business Profile
    ne sont pas configurés.
    """


def _verifier_configuration() -> None:
    if not settings.google_service_account_file:
        raise ConfigurationGoogleBusinessManquante(
            "GOOGLE_SERVICE_ACCOUNT_FILE n'est pas configuré."
        )

    if not settings.google_business_account_id:
        raise ConfigurationGoogleBusinessManquante(
            "GOOGLE_BUSINESS_ACCOUNT_ID n'est pas configuré."
        )

    if not settings.google_business_location_id:
        raise ConfigurationGoogleBusinessManquante(
            "GOOGLE_BUSINESS_LOCATION_ID n'est pas configuré."
        )


def _obtenir_token_acces() -> str:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    scopes = ["https://www.googleapis.com/auth/business.manage"]

    credentials = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=scopes,
    )
    credentials.refresh(Request())

    return credentials.token


async def lire_avis_google_business() -> list[dict]:
    """
    Récupère les avis d'une fiche Google Business Profile
    (campus Bakeli) via l'API officielle.

    Nécessite un accès validé par Google (l'API Business Profile
    n'est pas activable librement, contrairement à Sheets).
    """
    _verifier_configuration()

    token = _obtenir_token_acces()

    url = (
        "https://mybusiness.googleapis.com/v4/accounts/"
        f"{settings.google_business_account_id}/locations/"
        f"{settings.google_business_location_id}/reviews"
    )

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        reponse = await client.get(url, headers=headers)
        reponse.raise_for_status()
        data = reponse.json()

    return data.get("reviews", [])