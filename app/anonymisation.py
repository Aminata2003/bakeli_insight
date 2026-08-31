import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mapping import normaliser
from app.models import Apprenant, IdentiteTemporaire


def generer_token_anonyme() -> str:
    return f"User_{uuid.uuid4().hex[:12]}"


def _trouver_identite_active(db: Session, cle: str) -> IdentiteTemporaire | None:
    maintenant = datetime.now(timezone.utc)
    identites = db.scalars(
        select(IdentiteTemporaire).where(IdentiteTemporaire.expires_at > maintenant)
    )
    return next(
        (
            identite
            for identite in identites
            if normaliser(f"{identite.prenom or ''} {identite.nom or ''}") == cle
        ),
        None,
    )


def resoudre_apprenant(db: Session, prenom: str | None, nom: str | None, source_fichier: str) -> uuid.UUID | None:
    """Retrouve l'apprenant déjà connu sous ce nom, ou en crée un nouveau anonymisé.
    La table `avis` ne reçoit jamais prenom/nom -- seulement cet identifiant technique."""
    if not prenom and not nom:
        return None

    cle = normaliser(f"{prenom or ''} {nom or ''}")

    identite = _trouver_identite_active(db, cle)
    if identite:
        return identite.apprenant_id

    token = generer_token_anonyme()
    while db.scalar(select(Apprenant.id).where(Apprenant.token_anonyme == token)):
        token = generer_token_anonyme()

    apprenant = Apprenant(token_anonyme=token)
    db.add(apprenant)
    db.flush()  # récupère apprenant.id sans valider toute la transaction

    db.add(IdentiteTemporaire(
        apprenant_id=apprenant.id,
        prenom=prenom,
        nom=nom,
        source_fichier=source_fichier,
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    ))

    return apprenant.id