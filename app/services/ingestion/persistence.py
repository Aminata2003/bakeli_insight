from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.anonymisation import resoudre_apprenant
from app.mapping import deduire_thematique
from app.models import Avis, Plateforme, Thematique
from app.services.ingestion.base import DonneeIngestion
from app.services.nlp import analyser_texte
from app.services.archivage import archiver_donnee_brute


async def enregistrer_donnee_ingestion(
    db: Session,
    donnee: DonneeIngestion,
) -> Avis:
    """
    Enregistre une donnée provenant d'un connecteur d'ingestion
    dans PostgreSQL en réutilisant le pipeline existant.

    Pipeline :
        ingestion
        -> normalisation
        -> anonymisation
        -> thématique
        -> NLP
        -> PostgreSQL
        -> archivage brut (MongoDB)
    """

    plateforme = db.scalar(
        select(Plateforme).where(
            Plateforme.code == donnee.plateforme_code
        )
    )

    if not plateforme:
        raise ValueError(
            f"Plateforme inconnue : {donnee.plateforme_code}"
        )

    # Vérification anti-duplication
    feedback_existant = db.scalar(
        select(Avis).where(
            Avis.feedback_id == donnee.source_id
        )
    )

    if feedback_existant:
        return feedback_existant

    texte = donnee.texte.strip()

    # Résolution de l'identité temporaire
    apprenant_id = resoudre_apprenant(
        db,
        donnee.auteur_prenom,
        donnee.auteur_nom,
        f"ingestion_{donnee.plateforme_code}",
    )

    # Recherche de la thématique
    cle_thematique = deduire_thematique(
        texte,
        texte,
        None,
        None,
    )

    thematique = db.scalar(
        select(Thematique).where(
            Thematique.cle == cle_thematique
        )
    )

    # Analyse NLP / IA
    analyse = await analyser_texte(
        texte,
        None,
    )

    avis = Avis(
        feedback_id=donnee.source_id,
        plateforme_id=plateforme.id,
        apprenant_id=apprenant_id,
        thematique_id=thematique.id if thematique else None,
        texte_a_analyser_ia=texte,
        commentaire_libre=texte,
        sentiment=analyse.sentiment if analyse else None,
        note=analyse.note if analyse else None,
        resume=analyse.resume if analyse else None,
        langue_detectee=(
            analyse.langue_detectee if analyse else None
        ),
        date_avis=donnee.date_source,
        date_ingestion=datetime.now(timezone.utc),
        date_traitement_ia=(
            datetime.now(timezone.utc)
            if analyse
            else None
        ),
    )

    db.add(avis)
    db.flush()

    # -------------------------------------------------------------
    # Archivage de la donnée brute dans MongoDB
    # (best-effort : ne doit jamais faire échouer l'ingestion
    # PostgreSQL si MongoDB est indisponible)
    # -------------------------------------------------------------
    try:
        await archiver_donnee_brute(donnee)
    except Exception as e:
        print(f"[Archivage MongoDB] Échec : {e}")

    return avis