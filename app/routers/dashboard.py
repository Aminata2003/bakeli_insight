from fastapi import APIRouter, Depends
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Avis
from app.security import require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/vue-ensemble")
def get_vue_ensemble(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    """Reproduit deriveKpis() de derive.ts (frontend), pour que les chiffres soient identiques
    que la donnée vienne de dataset.ts (démo) ou de notre vraie base."""
    tous_les_avis = db.scalars(select(Avis)).all()
    total = len(tous_les_avis) or 1  # évite une division par zéro si la base est vide

    scores = [a.satisfaction_score_10 for a in tous_les_avis if a.satisfaction_score_10 is not None]

    def categorie(avis: Avis) -> str:
        if avis.sentiment:
            return avis.sentiment
        score = avis.satisfaction_score_10
        if score is None:
            return "neutre"
        if score >= 8:
            return "positif"
        if score <= 4:
            return "negatif"
        return "neutre"

    categories = [categorie(a) for a in tous_les_avis]
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


def _avis_charges(db: Session) -> list[Avis]:
    return db.scalars(
        select(Avis).options(
            joinedload(Avis.plateforme),
            joinedload(Avis.thematique),
        )
    ).all()


@router.get("/plateformes")
def repartition_plateformes(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    avis = _avis_charges(db)
    compteurs = Counter(a.plateforme.nom_affiche for a in avis)
    return {"items": [{"label": label, "value": value} for label, value in compteurs.most_common()]}


@router.get("/thematiques")
def repartition_thematiques(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    avis = _avis_charges(db)
    compteurs = Counter(a.thematique.nom_affiche if a.thematique else "Non classé" for a in avis)
    return {"items": [{"label": label, "value": value} for label, value in compteurs.most_common()]}


@router.get("/sentiments")
def repartition_sentiments(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    avis = _avis_charges(db)
    compteurs = Counter(a.sentiment or "neutre" for a in avis)
    total = len(avis) or 1
    return {
        "total": len(avis),
        "items": [
            {
                "label": label,
                "value": value,
                "pourcentage": round(value * 100 / total),
            }
            for label, value in compteurs.most_common()
        ],
    }


@router.get("/evolution")
def evolution_mensuelle(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    avis = db.scalars(select(Avis)).all()
    groupes: dict[str, dict[str, list[int]]] = {}
    for element in avis:
        if element.date_avis is None:
            continue
        cle = element.date_avis.strftime("%Y-%m")
        groupe = groupes.setdefault(cle, {"scores": [], "sentiments": []})
        if element.satisfaction_score_10 is not None:
            groupe["scores"].append(element.satisfaction_score_10)
        if element.sentiment:
            groupe["sentiments"].append(element.sentiment)

    items = []
    for mois, groupe in sorted(groupes.items()):
        scores = groupe["scores"]
        sentiments = Counter(groupe["sentiments"])
        items.append({
            "periode": mois,
            "avis": len([a for a in avis if a.date_avis and a.date_avis.strftime("%Y-%m") == mois]),
            "satisfaction": round(sum(scores) / len(scores), 1) if scores else None,
            "positifs": sentiments.get("positif", 0),
            "neutres": sentiments.get("neutre", 0),
            "negatifs": sentiments.get("negatif", 0),
        })
    return {"items": items}