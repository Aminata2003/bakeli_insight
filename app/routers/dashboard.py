from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Avis

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/vue-ensemble")
def get_vue_ensemble(db: Session = Depends(get_db)):
    """Reproduit deriveKpis() de derive.ts (frontend), pour que les chiffres soient identiques
    que la donnée vienne de dataset.ts (démo) ou de notre vraie base."""
    tous_les_avis = db.scalars(select(Avis)).all()
    total = len(tous_les_avis) or 1  # évite une division par zéro si la base est vide

    scores = [a.satisfaction_score_10 for a in tous_les_avis if a.satisfaction_score_10 is not None]

    def categorie(score: int | None) -> str:
        if score is None:
            return "neutre"
        if score >= 8:
            return "positif"
        if score <= 4:
            return "negatif"
        return "neutre"

    categories = [categorie(a.satisfaction_score_10) for a in tous_les_avis]
    nb_positif = categories.count("positif")
    nb_neutre = categories.count("neutre")
    nb_negatif = categories.count("negatif")

    satisfaction_moyenne = round((sum(scores) / len(scores)) * 10) if scores else 0

    return {
        "satisfaction": satisfaction_moyenne,               # /100, comme deriveKpis
        "positive": round((nb_positif / total) * 100),
        "neutral": round((nb_neutre / total) * 100),
        "negative": round((nb_negatif / total) * 100),
        "total": len(tous_les_avis),
        "platforms": len({a.plateforme_id for a in tous_les_avis}),
    }