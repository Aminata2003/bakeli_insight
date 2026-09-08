import asyncio

from app.database import SessionLocal
from app.services.ingestion.service import ServiceIngestion
from app.services.ingestion.persistence import enregistrer_donnee_ingestion
from app.services.ingestion.sources.google_forms import (
    GoogleFormsConnecteur,
    mapper_reponses_formulaire,
)


# Données fictives qui imitent EXACTEMENT ce que renverrait
# lire_google_sheet() une fois connecté au vrai Google Sheet.
LIGNES_BRUTES_SIMULEES = [
    {
        "Horodateur": "31/07/2026 12:39:58",
        "Prénom": "Salimata Mamadou",
        "Nom": "N'DIAYE",
        "Quel créneau horaire vous conviennent le mieux le VENDREDI ?": "15H-17H",
        "Quel créneau horaire vous conviennent le mieux le MARDI ?": "15H-17H",
        "Disposez-vous d'une connexion internet stable pendant les créneaux choisis ?": "Stable",
        "Remarques ou suggestions supplémentaires concernant l'organisation des séances  ?": (
            "Plus de clarté sur le prix à payer car il n'est toujours pas clair"
        ),
    },
    {
        "Horodateur": "31/07/2026 14:16:21",
        "Prénom": "Issa Mansour",
        "Nom": "Diop",
        "Quel créneau horaire vous conviennent le mieux le VENDREDI ?": "Mardi",
        "Quel créneau horaire vous conviennent le mieux le MARDI ?": "Vendredi",
        "Disposez-vous d'une connexion internet stable pendant les créneaux choisis ?": "Oui, toujours stable",
        "Remarques ou suggestions supplémentaires concernant l'organisation des séances  ?": (
            "On peut maintenir le Mardi"
        ),
    },
]


async def main():
    # 1. Simule ce que ferait lire_google_sheet()
    lignes_mappees = mapper_reponses_formulaire(LIGNES_BRUTES_SIMULEES)

    # 2. Passe par le connecteur + le service d'ingestion (normalisation)
    connecteur = GoogleFormsConnecteur(donnees=lignes_mappees)
    service_ingestion = ServiceIngestion([connecteur])
    donnees_normalisees = await service_ingestion.recuperer_toutes_les_donnees()

    print(f"{len(donnees_normalisees)} donnée(s) normalisée(s) récupérée(s).\n")

    # 3. Enregistre en base (PostgreSQL réel — attention si tu es en prod)
    db = SessionLocal()
    try:
        for donnee in donnees_normalisees:
            avis = await enregistrer_donnee_ingestion(db, donnee)
            print(f"-> Avis créé/trouvé : id={avis.id}, feedback_id={avis.feedback_id}")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())