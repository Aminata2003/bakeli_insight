from datetime import datetime, timezone

from app.mongodb import obtenir_base_mongo
from app.services.ingestion.base import DonneeIngestion


async def archiver_donnee_brute(donnee: DonneeIngestion) -> None:
    """
    Archive ou met à jour la donnée brute dans MongoDB.

    Une donnée est identifiée de manière unique par :
        - plateforme_code
        - source_id

    Cela permet de relancer un import sans créer de doublons
    dans MongoDB.
    """
    base = obtenir_base_mongo()

    collection = base["donnees_brutes"]

    document = {
        "plateforme_code": donnee.plateforme_code,
        "source_id": donnee.source_id,
        "texte": donnee.texte,
        "auteur_nom": donnee.auteur_nom,
        "auteur_prenom": donnee.auteur_prenom,
        "metadata": donnee.metadata,
        "date_ingestion": datetime.now(timezone.utc),
    }

    await collection.update_one(
        {
            "plateforme_code": donnee.plateforme_code,
            "source_id": donnee.source_id,
        },
        {
            "$set": document,
        },
        upsert=True,
    )


async def creer_index_mongo() -> None:
    """
    Crée les index MongoDB nécessaires :

    - index unique sur plateforme_code + source_id
    - index TTL de 90 jours sur date_ingestion
    """
    base = obtenir_base_mongo()

    collection = base["donnees_brutes"]

    await collection.create_index(
        [
            ("plateforme_code", 1),
            ("source_id", 1),
        ],
        unique=True,
        name="unique_plateforme_source",
    )

    await collection.create_index(
        "date_ingestion",
        expireAfterSeconds=90 * 24 * 3600,
        name="ttl_90_jours",
    )