import asyncio
from urllib.parse import quote

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

from app.config import settings


SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class ConfigurationGoogleManquante(Exception):
    """
    Levée quand les credentials Google Cloud ne sont pas
    encore configurés.
    """


def _verifier_configuration() -> None:
    if not settings.google_service_account_file:
        raise ConfigurationGoogleManquante(
            "GOOGLE_SERVICE_ACCOUNT_FILE n'est pas configuré. "
            "Le fichier de credentials Google Cloud doit être "
            "fourni avant de pouvoir lire un Google Sheet."
        )


def _construire_session() -> AuthorizedSession:
    _verifier_configuration()

    credentials = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=SCOPES,
    )

    return AuthorizedSession(credentials)


def _lire_google_sheet_sync(
    spreadsheet_id: str,
    plage: str
) -> list[dict]:

    session = _construire_session()

    # Encodage de la plage pour pouvoir gérer correctement
    # les noms contenant des espaces ou caractères spéciaux.
    plage_encodee = quote(plage, safe="")

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{spreadsheet_id}/values/{plage_encodee}"
    )

    try:
        response = session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        resultat = response.json()

    except Exception as exc:
        raise RuntimeError(
            f"Impossible de lire le Google Sheet. "
            f"Spreadsheet ID: {spreadsheet_id}. "
            f"Plage: {plage}. "
            f"Erreur: {exc}"
        ) from exc

    valeurs = resultat.get("values", [])

    if not valeurs:
        return []

    en_tetes = valeurs[0]

    lignes = valeurs[1:]

    donnees = []

    for ligne in lignes:

        # Google Sheets n'envoie pas les cellules vides
        # situées à la fin d'une ligne.
        ligne_completee = ligne + [
            ""
        ] * max(0, len(en_tetes) - len(ligne))

        donnees.append(
            dict(
                zip(
                    en_tetes,
                    ligne_completee
                )
            )
        )

    return donnees


async def lire_google_sheet(
    spreadsheet_id: str,
    plage: str = "Form_Responses",
) -> list[dict]:
    """
    Lit les réponses d'un Google Sheet.

    L'appel Google est exécuté dans un thread afin
    de ne pas bloquer l'event loop FastAPI.
    """

    return await asyncio.to_thread(
        _lire_google_sheet_sync,
        spreadsheet_id,
        plage,
    )