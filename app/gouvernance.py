from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Avis, Plateforme

# Section 5.3 du cahier des charges -- gouvernance des accès par équipe.
# NULL (pas d'équipe assignée) = aucune restriction, accès complet.
CATEGORIES_AUTORISEES: dict[str, tuple[str, ...]] = {
    "marketing": ("reseau_public",),
    "pedagogie": ("canal_prive", "canal_interne"),
    # "direction" volontairement absent : la direction n'a pas accès à la liste
    # brute des avis, uniquement aux KPI agrégés (cf. filtrer_avis_par_equipe
    # lève une erreur explicite si on essaie de lister des avis bruts pour elle).
}


def filtrer_avis_par_equipe(stmt, equipe: str | None):
    """Restreint une requête SELECT(Avis) selon l'équipe de l'utilisateur.
    Ne fait rien si equipe est None (admin/super_admin -- accès complet)."""
    if equipe is None:
        return stmt
    if equipe == "direction":
        raise PermissionError("La direction n'a pas accès à la liste brute des avis, uniquement aux KPI agrégés.")
    categories = CATEGORIES_AUTORISEES.get(equipe)
    if categories is None:
        return stmt
    return stmt.where(Avis.plateforme.has(Plateforme.categorie.in_(categories)))


def plateformes_autorisees_ids(db: Session, equipe: str | None) -> set[int] | None:
    """Renvoie l'ensemble des ID de plateformes visibles par cette équipe,
    ou None si aucune restriction (accès à tout). Utile pour filtrer des
    listes déjà chargées en mémoire (ex: dans dashboard.py)."""
    if equipe is None or equipe == "direction":
        return None
    categories = CATEGORIES_AUTORISEES.get(equipe)
    if categories is None:
        return None
    ids = db.scalars(select(Plateforme.id).where(Plateforme.categorie.in_(categories))).all()
    return set(ids)