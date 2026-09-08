import logging
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models import IdentiteTemporaire

logger = logging.getLogger("bakeli.purge")


def purger_identites_expirees(db: Session) -> int:
    """Supprime les identités (prénom/nom) dont la date d'expiration (90 jours) est dépassée.
    Conforme à la section 5.2 du cahier des charges : les données nominatives ne sont
    conservées que 90 jours ; au-delà, seul le score agrégé (déjà dans `avis`) reste."""
    maintenant = datetime.now(timezone.utc)

    a_supprimer = db.scalars(
        select(IdentiteTemporaire).where(IdentiteTemporaire.expires_at < maintenant)
    ).all()
    nb = len(a_supprimer)

    if nb > 0:
        db.execute(delete(IdentiteTemporaire).where(IdentiteTemporaire.expires_at < maintenant))
        db.commit()
        logger.info(f"Purge RGPD : {nb} identité(s) expirée(s) supprimée(s).")

    return nb