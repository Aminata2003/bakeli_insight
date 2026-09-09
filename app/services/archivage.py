from datetime import datetime, timezone

from app.mongodb import obtenir_base_mongo
from app.services.ingestion.base import DonneeIngestion


async def archiver_donnee_brute(donnee: DonneeIngestion) -> None:
    """
    Archive temporairement la donnée brute (texte non anonymisé,
    tel que reçu de la source) dans MongoDB.

    Une expiration automatique après 90 jours est configurée via
    un index TTL (voir creer_index_mongo), conformément à
    l'exigence "Cycle de Vie Limité" du cahier des charges.
    """
    base = obtenir_base_mongo()

    await base["donnees_brutes"].insert_one(
        {
            "plateforme_code": donnee.plateforme_code,
            "source_id": donnee.source_id,
            "texte": donnee.texte,
            "auteur_nom": donnee.auteur_nom,
            "auteur_prenom": donnee.auteur_prenom,
            "metadata": donnee.metadata,
            "date_ingestion": datetime.now(timezone.utc),
        }
    )


async def creer_index_mongo() -> None:
    """
    Crée l'index TTL qui supprime automatiquement les documents
    90 jours après leur date d'ingestion.

    MongoDB vérifie et supprime les documents expirés en tâche
    de fond (pas instantané, mais dans la minute qui suit
    l'expiration en général).
    """
    base = obtenir_base_mongo()

    await base["donnees_brutes"].create_index(
        "date_ingestion",
        expireAfterSeconds=90 * 24 * 3600,
    )