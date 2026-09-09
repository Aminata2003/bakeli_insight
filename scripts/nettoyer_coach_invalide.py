from sqlalchemy import select

from app.database import SessionLocal
from app.models import Avis
from app.mapping import _est_nom_coach_plausible


def nettoyer_coachs_invalides():
    db = SessionLocal()

    try:
        avis_avec_coach = db.scalars(
            select(Avis).where(Avis.coach.is_not(None))
        ).all()

        nb_corriges = 0

        for avis in avis_avec_coach:
            if not _est_nom_coach_plausible(avis.coach):
                print(
                    f"-> Correction : avis id={avis.id}, "
                    f"coach='{avis.coach}' -> None"
                )
                avis.coach = None
                nb_corriges += 1

        db.commit()
        print(f"\n{nb_corriges} avis corrigé(s) sur {len(avis_avec_coach)}.")

    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}")

    finally:
        db.close()


if __name__ == "__main__":
    nettoyer_coachs_invalides()