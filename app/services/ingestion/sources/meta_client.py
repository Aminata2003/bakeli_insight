import httpx

from app.config import settings

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class ConfigurationMetaManquante(Exception):
    """
    Levée quand le token d'accès Meta (Facebook/Instagram)
    n'est pas configuré.
    """


def _verifier_configuration() -> None:
    if not settings.meta_page_access_token:
        raise ConfigurationMetaManquante(
            "META_PAGE_ACCESS_TOKEN n'est pas configuré."
        )


async def lire_commentaires_instagram(media_ids: list[str]) -> list[dict]:
    """
    Récupère les commentaires des publications Instagram spécifiées
    (posts, reels) via l'API Graph.
    """
    _verifier_configuration()

    tous_commentaires = []

    async with httpx.AsyncClient() as client:
        for media_id in media_ids:
            url = f"{GRAPH_API_BASE}/{media_id}/comments"
            params = {
                "fields": "id,text,username,timestamp",
                "access_token": settings.meta_page_access_token,
            }
            reponse = await client.get(url, params=params)
            reponse.raise_for_status()
            data = reponse.json()
            tous_commentaires.extend(data.get("data", []))

    return tous_commentaires


async def lire_commentaires_facebook(post_ids: list[str]) -> list[dict]:
    """
    Récupère les commentaires des publications de la Page Facebook
    officielle de Bakeli via l'API Graph.
    """
    _verifier_configuration()

    tous_commentaires = []

    async with httpx.AsyncClient() as client:
        for post_id in post_ids:
            url = f"{GRAPH_API_BASE}/{post_id}/comments"
            params = {
                "fields": "id,message,from,created_time",
                "access_token": settings.meta_page_access_token,
            }
            reponse = await client.get(url, params=params)
            reponse.raise_for_status()
            data = reponse.json()
            tous_commentaires.extend(data.get("data", []))

    return tous_commentaires