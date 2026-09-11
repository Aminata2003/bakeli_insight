import sys
from pathlib import Path
import asyncio

# Ajouter la racine du projet au chemin Python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.mongodb import obtenir_base_mongo


async def main():
    try:
        db = obtenir_base_mongo()

        print("✅ Connexion à MongoDB réussie")
        print(f"📦 Base : {db.name}")
        print("\n📚 Collections :")

        collections = await db.list_collection_names()

        if not collections:
            print("   Aucune collection pour le moment.")
            return

        for collection_name in collections:
            collection = db[collection_name]
            count = await collection.count_documents({})

            print(f"   - {collection_name} : {count} document(s)")

        print("\n✅ Inspection terminée.")

    except Exception as e:
        print("❌ Erreur lors de l'inspection de MongoDB")
        print("Erreur :", e)


if __name__ == "__main__":
    asyncio.run(main())