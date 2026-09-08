import asyncio

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class ConfigurationGoogleManquante(Exception):
    """
    Levée quand les credentials Google Cloud ne sont pas
    encore configurés (fichier de compte de service absent).
    """


def _verifier_configuration() -> None:
    if not settings.google_service_account_file:
        raise ConfigurationGoogleManquante(
            "GOOGLE_SERVICE_ACCOUNT_FILE n'est pas configuré. "
            "Le fichier de credentials Google Cloud doit être "
            "fourni avant de pouvoir lire un Google Sheet."
        )


def _construire_service():
    _verifier_configuration()

    credentials = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=SCOPES,
    )
    return build("sheets", "v4", credentials=credentials)


def _lire_google_sheet_sync(spreadsheet_id: str, plage: str) -> list[dict]:
    service = _construire_service()

    resultat = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=plage)
        .execute()
    )

    valeurs = resultat.get("values", [])

    if not valeurs:
        return []

    en_tetes = valeurs[0]
    lignes = valeurs[1:]

    donnees = []
    for ligne in lignes:
        # On complète les lignes plus courtes que l'en-tête
        # (Google Sheets n'envoie pas les cellules vides en fin de ligne)
        ligne_completee = ligne + [""] * (len(en_tetes) - len(ligne))
        donnees.append(dict(zip(en_tetes, ligne_completee)))

    return donnees


async def lire_google_sheet(
    spreadsheet_id: str,
    plage: str = "Form_Responses",
) -> list[dict]:
    """
    Lit les réponses d'un Google Sheet.

    Lève ConfigurationGoogleManquante si les credentials
    Google Cloud ne sont pas encore configurés.

    L'appel à l'API Google étant bloquant (synchrone), on le
    déporte dans un thread pour ne pas bloquer l'event loop.
    """
    return await asyncio.to_thread(
        _lire_google_sheet_sync, spreadsheet_id, plage
    )