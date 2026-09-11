import sys
from pathlib import Path
import asyncio

# Ajouter la racine du projet au chemin Python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mongodb import obtenir_client_mongo


async def main():
    try:
        client = obtenir_client_mongo()

        await client.admin.command("ping")

        print("✅ Connexion à MongoDB Atlas réussie !")
        print("✅ Base utilisée :", "bakeli_insights")

    except Exception as e:
        print("❌ Échec de connexion à MongoDB")
        print("Erreur :", e)


if __name__ == "__main__":
    asyncio.run(main())