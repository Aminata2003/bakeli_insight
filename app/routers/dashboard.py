from fastapi import APIRouter, Depends, HTTPException
from collections import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Avis
from app.security import require_role
from app.wordcloud import calculer_wordcloud
from app.gouvernance import plateformes_autorisees_ids

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _avis_visibles(db: Session, current: dict, avec_relations: bool = False) -> list[Avis]:
    """Renvoie les avis visibles par l'utilisateur connecté, restreints par équipe
    (section 5.3). None = pas de restriction (admin/super_admin/direction --
    la direction a accès aux KPI agrégés, juste pas à la liste brute des avis)."""
    stmt = select(Avis)
    if avec_relations:
        stmt = stmt.options(joinedload(Avis.plateforme), joinedload(Avis.thematique))

    allowed_ids = plateformes_autorisees_ids(db, current.get("equipe"))
    avis = db.scalars(stmt).all()
    if allowed_ids is None:
        return avis
    return [a for a in avis if a.plateforme_id in allowed_ids]


@router.get("/vue-ensemble")
def get_vue_ensemble(
    db: Session = Depends(get_db),
    current=Depends(require_role("super_admin", "admin", "collaborator")),
):
    """Reproduit deriveKpis() de derive.ts (frontend). Un seul score par avis est utilisé
    à la fois pour la catégorie (positif/neutre/négatif) et pour la moyenne, afin que les
    deux chiffres restent toujours cohérents entre eux."""
    tous_les_avis = _avis_visibles(db, current)
    total = len(tous_les_avis) or 1

    def score_effectif(avis: Avis) -> int | None:
        if avis.satisfaction_score_10 is not None:
            return avis.satisfaction_score_10
        if avis.note is not None:
            return avis.note * 2
        return None

    def categorie(avis: Avis, score: int | None) -> str:
        if avis.sentiment:
            return avis.sentiment
        if score is None:
            return "neutre"
        if score >= 8:
            return "positif"
        if score <= 4:
            return "negatif"
        return "neutre"

    scores_et_categories = [(score_effectif(a), categorie(a, score_effectif(a))) for a in tous_les_avis]

    scores_valides = [s for s, _ in scores_et_categories if s is not None]
    categories = [c for _, c in scores_et_categories]

    nb_positif = categories.count("positif")
    nb_neutre = categories.count("neutre")
    nb_negatif = categories.count("negatif")

    satisfaction_moyenne = round((sum(scores_valides) / len(scores_valides)) * 10) if scores_valides else 0

    return {
        "satisfaction": satisfaction_moyenne,
        "positive": round((nb_positif / total) * 100),
        "neutral": round((nb_neutre / total) * 100),
        "negative": round((nb_negatif / total) * 100),
        "total": len(tous_les_avis),
        "platforms": len({a.plateforme_id for a in tous_les_avis}),
    }


@router.get("/plateformes")
def repartition_plateformes(
    db: Session = Depends(get_db),
    current=Depends(require_role("super_admin", "admin", "collaborator")),
):
    avis = _avis_visibles(db, current, avec_relations=True)
    compteurs = Counter(a.plateforme.nom_affiche for a in avis)
    return {"items": [{"label": label, "value": value} for label, value in compteurs.most_common()]}


@router.get("/thematiques")
def repartition_thematiques(
    db: Session = Depends(get_db),
    current=Depends(require_role("super_admin", "admin", "collaborator")),
):
    avis = _avis_visibles(db, current, avec_relations=True)
    compteurs = Counter(a.thematique.nom_affiche if a.thematique else "Non classé" for a in avis)
    return {"items": [{"label": label, "value": value} for label, value in compteurs.most_common()]}


@router.get("/sentiments")
def repartition_sentiments(
    db: Session = Depends(get_db),
    current=Depends(require_role("super_admin", "admin", "collaborator")),
):
    avis = _avis_visibles(db, current, avec_relations=True)
    compteurs = Counter(a.sentiment or "neutre" for a in avis)
    total = len(avis) or 1
    return {
        "total": len(avis),
        "items": [
            {"label": label, "value": value, "pourcentage": round(value * 100 / total)}
            for label, value in compteurs.most_common()
        ],
    }


@router.get("/wordcloud")
def get_wordcloud(
    limite: int = 30,
    db: Session = Depends(get_db),
    current=Depends(require_role("super_admin", "admin", "collaborator")),
):
    """Nuage de mots dynamique -- Vue Community Manager (section 4.C du cahier
    des charges). Reconnaît les expressions wolof/franglais de la section 3
    en plus des mots français génériques."""
    if limite < 1 or limite > 100:
        raise HTTPException(400, "limite invalide -- attendu entre 1 et 100")
    avis = _avis_visibles(db, current)
    return {"items": calculer_wordcloud(avis, limite)}


@router.get("/evolution")
def evolution_mensuelle(
    db: Session = Depends(get_db),
    current=Depends(require_role("super_admin", "admin", "collaborator")),
):
    avis = _avis_visibles(db, current)
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