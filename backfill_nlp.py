from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Avis
from app.services.nlp import analyser_texte, texte_a_analyser


def main() -> None:
    db = SessionLocal()
    try:
        avis = db.scalars(select(Avis)).all()
        analyses = 0
        for element in avis:
            resultat = analyser_texte(
                texte_a_analyser(element), element.satisfaction_score_10
            )
            if resultat is None:
                continue
            element.sentiment = resultat.sentiment
            element.note = resultat.note
            element.resume = resultat.resume
            element.langue_detectee = resultat.langue_detectee
            element.date_traitement_ia = datetime.now(timezone.utc)
            analyses += 1
        db.commit()
        print(f"Avis analyses : {analyses}/{len(avis)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()