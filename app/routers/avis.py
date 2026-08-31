from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Avis, Plateforme, Thematique
from app.schemas import AvisOut, AvisListResponse
from app.security import require_role
import uuid

router = APIRouter(prefix="/avis", tags=["avis"])


def _to_avis_out(avis: Avis) -> AvisOut:
    score = avis.satisfaction_score_10
    sentiment = avis.sentiment
    if sentiment is None and score is not None:
        sentiment = "positif" if score >= 8 else "negatif" if score <= 4 else "neutre"

    return AvisOut(
        feedback_id=avis.feedback_id,
        apprenant=avis.apprenant.token_anonyme if avis.apprenant else None,
        plateforme=avis.plateforme.nom_affiche,
        thematique=avis.thematique.nom_affiche if avis.thematique else None,
        date_avis=avis.date_avis,
        annee=avis.annee,
        mois=avis.mois,
        campus=avis.campus,
        promotion=avis.promotion,
        formation=avis.formation,
        coach=avis.coach,
        satisfaction_qualitative=avis.satisfaction_qualitative,
        satisfaction_score_10=avis.satisfaction_score_10,
        note=avis.note if avis.note is not None else round(score / 2) if score is not None else None,
        sentiment=sentiment,
        resume=avis.resume,
        langue_detectee=avis.langue_detectee,
        frequence_feedback=avis.frequence_feedback,
        source_feedback=avis.source_feedback,
        attentes_formation=avis.attentes_formation,
        attentes_remplies=avis.attentes_remplies,
        besoin_cours_theorique=avis.besoin_cours_theorique,
        points_amelioration=avis.points_amelioration,
        avis_activites_vendredi=avis.avis_activites_vendredi,
        regroupement_niveaux=avis.regroupement_niveaux,
        commentaire_libre=avis.commentaire_libre,
        commentaire=avis.commentaire_libre or avis.texte_a_analyser_ia,
        langue=avis.langue,
        texte_a_analyser_ia=avis.texte_a_analyser_ia,
        statut_moderation=avis.statut_moderation,
    )

@router.get("", response_model=AvisListResponse)
def lister_avis(
    campus: str | None = None,
    formation: str | None = None,
    plateforme: str | None = None,
    thematique: str | None = None,
    sentiment: str | None = None,
    statut_moderation: str | None = None,
    page: int = 1,
    taille_page: int = 20,
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    """Alimente l'Explorateur des avis. Renvoie le format RealFeedback attendu par use-feedback.ts."""
    if page < 1 or taille_page < 1 or taille_page > 100:
        raise HTTPException(400, "pagination invalide : page >= 1 et taille_page entre 1 et 100")

    stmt = select(Avis).options(
        joinedload(Avis.plateforme),
        joinedload(Avis.thematique),
        joinedload(Avis.apprenant),
    )

    if campus:
        stmt = stmt.where(Avis.campus == campus)
    if formation:
        stmt = stmt.where(Avis.formation == formation)
    if plateforme:
        stmt = stmt.where(Avis.plateforme.has(Plateforme.code == plateforme))
    if thematique:
        stmt = stmt.where(Avis.thematique.has(Thematique.cle == thematique))
    if sentiment:
        if sentiment not in ("positif", "neutre", "negatif"):
            raise HTTPException(400, "sentiment invalide -- attendu : positif | neutre | negatif")
        if sentiment == "positif":
            stmt = stmt.where(Avis.sentiment == "positif")
        elif sentiment == "negatif":
            stmt = stmt.where(Avis.sentiment == "negatif")
        else:
            stmt = stmt.where(Avis.sentiment == "neutre")
    if statut_moderation:
        stmt = stmt.where(Avis.statut_moderation == statut_moderation)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = stmt.order_by(Avis.date_avis.desc()).offset((page - 1) * taille_page).limit(taille_page)
    rows = db.scalars(stmt).all()

    return AvisListResponse(total=total or 0, items=[_to_avis_out(a) for a in rows])



@router.patch("/{avis_id}/statut")
def changer_statut_moderation(
    avis_id: uuid.UUID,
    nouveau_statut: str,
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "moderator")),
):
    """Permet au Community Manager de faire avancer un avis dans le Mur des plaintes :
    nouveau -> en_cours -> traite."""
    if nouveau_statut not in ("nouveau", "en_cours", "traite"):
        raise HTTPException(400, "statut invalide -- attendu : nouveau | en_cours | traite")

    avis = db.get(Avis, avis_id)
    if not avis:
        raise HTTPException(404, "avis introuvable")

    avis.statut_moderation = nouveau_statut
    db.commit()

    return {"feedback_id": avis.feedback_id, "statut_moderation": avis.statut_moderation}


@router.patch("/feedback/{feedback_id}/statut")
def changer_statut_par_feedback(
    feedback_id: str,
    nouveau_statut: str,
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "moderator")),
):
    """Version pratique pour le frontend, qui connaît le feedback_id mais pas l'UUID interne."""
    correspondances = {
        "new": "nouveau",
        "reviewed": "en_cours",
        "escalated": "en_cours",
        "resolved": "traite",
    }
    statut = correspondances.get(nouveau_statut, nouveau_statut)
    if statut not in ("nouveau", "en_cours", "traite"):
        raise HTTPException(400, "statut invalide")

    avis = db.scalar(select(Avis).where(Avis.feedback_id == feedback_id))
    if not avis:
        raise HTTPException(404, "avis introuvable")

    avis.statut_moderation = statut
    db.commit()
    return {"feedback_id": avis.feedback_id, "statut_moderation": avis.statut_moderation}