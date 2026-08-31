from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Plateforme, Thematique
from app.schemas import PlateformeOut, ThematiqueOut
from app.security import require_role

router = APIRouter(tags=["reference"])


@router.get("/plateformes", response_model=list[PlateformeOut])
def lister_plateformes(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    return db.scalars(select(Plateforme).order_by(Plateforme.nom_affiche)).all()


@router.get("/thematiques", response_model=list[ThematiqueOut])
def lister_thematiques(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin", "analyst", "moderator")),
):
    return db.scalars(select(Thematique).order_by(Thematique.nom_affiche)).all()