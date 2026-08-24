from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Avis
from app.schemas import AvisOut, AvisListResponse
import uuid
from fastapi import HTTPException

router = APIRouter(prefix="/avis", tags=["avis"])


def _to_avis_out(avis: Avis) -> AvisOut:
    return AvisOut(
        feedback_id=avis.feedback_id,
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
        frequence_feedback=avis.frequence_feedback,
        source_feedback=avis.source_feedback,
        attentes_formation=avis.attentes_formation,
        attentes_remplies=avis.attentes_remplies,
        besoin_cours_theorique=avis.besoin_cours_theorique,
        points_amelioration=avis.points_amelioration,
        avis_activites_vendredi=avis.avis_activites_vendredi,
        regroupement_niveaux=avis.regroupement_niveaux,
        commentaire_libre=avis.commentaire_libre,
        langue=avis.langue,
        texte_a_analyser_ia=avis.texte_a_analyser_ia,
        statut_moderation=avis.statut_moderation,
    )

@router.get("", response_model=AvisListResponse)
def lister_avis(
    campus: str | None = None,
    formation: str | None = None,
    statut_moderation: str | None = Query(None, description="nouveau | en_cours | traite"),
    page: int = 1,
    taille_page: int = 20,
    db: Session = Depends(get_db),
):
    """Alimente l'Explorateur des avis. Renvoie le format RealFeedback attendu par use-feedback.ts."""
    stmt = select(Avis).options(joinedload(Avis.plateforme), joinedload(Avis.thematique))

    if campus:
        stmt = stmt.where(Avis.campus == campus)
    if formation:
        stmt = stmt.where(Avis.formation == formation)
    if statut_moderation:
        stmt = stmt.where(Avis.statut_moderation == statut_moderation)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    stmt = stmt.order_by(Avis.date_avis.desc()).offset((page - 1) * taille_page).limit(taille_page)
    rows = db.scalars(stmt).all()

    return AvisListResponse(total=total or 0, items=[_to_avis_out(a) for a in rows])



@router.patch("/{avis_id}/statut")
def changer_statut_moderation(avis_id: uuid.UUID, nouveau_statut: str, db: Session = Depends(get_db)):
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