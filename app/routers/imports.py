import io
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Avis, Plateforme, Thematique
from app.security import require_role
from app.mapping import (
    deduire_thematique,
    extraire_valeur,
    mapper_colonnes_automatiquement,
    transformer_ligne,
)
from app.anonymisation import resoudre_apprenant
from app.services.nlp import analyser_texte
from app.services.ingestion.base import DonneeIngestion
from app.services.ingestion.normalisation import normaliser_donnee
from app.config import settings
from app.services.ingestion.service import ServiceIngestion
from app.services.ingestion.persistence import enregistrer_donnee_ingestion
from app.services.ingestion.sources.google_forms import (
    GoogleFormsConnecteur,
    mapper_reponses_formulaire,
)
from app.services.ingestion.sources.google_sheets_client import (
    lire_google_sheet,
    ConfigurationGoogleManquante,
)
from app.services.ingestion.sources.typeform import (
    TypeformConnecteur,
    mapper_reponses_typeform,
)
from app.services.ingestion.sources.typeform_client import (
    lire_reponses_typeform,
    ConfigurationTypeformManquante,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/apercu")
async def apercu_fichier(
    fichier: UploadFile,
    _current=Depends(require_role("super_admin", "admin")),
):
    _valider_fichier(fichier)

    contenu = await fichier.read()
    df = _lire_fichier(fichier.filename, contenu)

    colonnes = list(df.columns)

    if df.empty:
        raise HTTPException(
            400,
            "Le fichier est vide ou ne contient aucune ligne exploitable.",
        )

    return {
        "nom_fichier": fichier.filename,
        "nb_lignes": len(df),
        "colonnes": colonnes,
        "mapping_propose": mapper_colonnes_automatiquement(colonnes),
    }


@router.post("/upload")
async def importer_fichier(
    fichier: UploadFile,
    plateforme_code: str = "google_forms",
    db: Session = Depends(get_db),
    _current=Depends(require_role("super_admin", "admin")),
):
    _valider_fichier(fichier)

    plateforme = db.scalar(
        select(Plateforme).where(
            Plateforme.code == plateforme_code
        )
    )

    if not plateforme:
        raise HTTPException(
            400,
            f"Plateforme inconnue : {plateforme_code}",
        )

    # Charge une seule fois la correspondance
    # clé de thématique -> ID
    thematiques_par_cle = {
        t.cle: t.id
        for t in db.scalars(select(Thematique)).all()
    }

    contenu = await fichier.read()
    df = _lire_fichier(fichier.filename, contenu)

    mapping = mapper_colonnes_automatiquement(
        list(df.columns)
    )

    feedback_ids = [
        f"{fichier.filename}-{index + 1:04d}"
        for index in range(len(df))
    ]

    feedback_ids_existants = set(
        db.scalars(
            select(Avis.feedback_id).where(
                Avis.feedback_id.in_(feedback_ids)
            )
        ).all()
    )

    lignes_ok = 0
    lignes_erreur = 0
    lignes_ignorees = 0
    erreurs = []

    for index, ligne in df.iterrows():

        if feedback_ids[index] in feedback_ids_existants:
            lignes_ignorees += 1
            continue

        try:
            with db.begin_nested():

                ligne_dict = ligne.to_dict()

                # -------------------------------------------------
                # Transformation de la ligne provenant de la source
                # -------------------------------------------------
                donnees = transformer_ligne(
                    ligne_dict,
                    mapping,
                    index,
                    fichier.filename,
                )

                donnees["plateforme_id"] = plateforme.id

                # -------------------------------------------------
                # Récupération des informations auteur
                # -------------------------------------------------
                prenom = extraire_valeur(
                    ligne_dict,
                    mapping,
                    "prenom",
                )

                nom = extraire_valeur(
                    ligne_dict,
                    mapping,
                    "nom",
                )

                # -------------------------------------------------
                # Nouvelle couche d'ingestion
                # -------------------------------------------------
                texte_source = (
                    donnees.get("texte_a_analyser_ia")
                    or donnees.get("commentaire_libre")
                    or donnees.get("points_amelioration")
                    or donnees.get("attentes_formation")
                    or ""
                )

                donnee_ingestion = DonneeIngestion(
                    plateforme_code=plateforme.code,
                    source_id=feedback_ids[index],
                    texte=str(texte_source),
                    auteur_nom=str(nom) if nom else None,
                    auteur_prenom=str(prenom) if prenom else None,
                    metadata={
                        "nom_fichier": fichier.filename,
                        "ligne": index + 2,
                    },
                )

                # -------------------------------------------------
                # Normalisation commune à toutes les sources
                # -------------------------------------------------
                donnee_ingestion = normaliser_donnee(
                    donnee_ingestion
                )

                # Le texte normalisé devient le texte de référence
                # pour la suite du pipeline.
                texte_analyse = donnee_ingestion.texte

                if donnees.get("texte_a_analyser_ia"):
                    donnees["texte_a_analyser_ia"] = texte_analyse
                elif donnees.get("commentaire_libre"):
                    donnees["commentaire_libre"] = texte_analyse
                elif donnees.get("points_amelioration"):
                    donnees["points_amelioration"] = texte_analyse
                elif donnees.get("attentes_formation"):
                    donnees["attentes_formation"] = texte_analyse

                # -------------------------------------------------
                # Anonymisation
                # -------------------------------------------------
                donnees["apprenant_id"] = resoudre_apprenant(
                    db,
                    donnee_ingestion.auteur_prenom,
                    donnee_ingestion.auteur_nom,
                    fichier.filename,
                )

                # -------------------------------------------------
                # Détermination de la thématique
                # -------------------------------------------------
                cle_thematique = deduire_thematique(
                    donnees.get("texte_a_analyser_ia"),
                    donnees.get("commentaire_libre"),
                    donnees.get("points_amelioration"),
                    donnees.get("attentes_formation"),
                )

                donnees["thematique_id"] = (
                    thematiques_par_cle.get(cle_thematique)
                )

                # -------------------------------------------------
                # Analyse NLP
                # -------------------------------------------------
                analyse = await analyser_texte(
                    texte_analyse,
                    donnees.get("satisfaction_score_10"),
                )

                if analyse:
                    donnees["sentiment"] = analyse.sentiment
                    donnees["note"] = analyse.note
                    donnees["resume"] = analyse.resume
                    donnees["langue_detectee"] = (
                        analyse.langue_detectee
                    )
                    donnees["date_traitement_ia"] = (
                        datetime.now(timezone.utc)
                    )

                # -------------------------------------------------
                # Enregistrement PostgreSQL
                # -------------------------------------------------
                db.add(Avis(**donnees))
                db.flush()

            lignes_ok += 1

        except Exception as e:
            lignes_erreur += 1

            erreurs.append(
                {
                    "ligne": index + 2,
                    "erreur": str(e),
                }
            )

    # -------------------------------------------------------------
    # Validation finale
    # -------------------------------------------------------------
    try:
        db.commit()

    except Exception as e:
        db.rollback()

        raise HTTPException(
            500,
            f"Impossible de finaliser l'import : {e}",
        ) from e

    return {
        "nom_fichier": fichier.filename,
        "plateforme": plateforme.code,
        "lignes_totales": len(df),
        "lignes_importees": lignes_ok,
        "lignes_deja_importees": lignes_ignorees,
        "lignes_en_erreur": lignes_erreur,
        "erreurs": erreurs,
    }


def _valider_fichier(fichier: UploadFile) -> None:
    nom = (fichier.filename or "").lower()

    if not nom:
        raise HTTPException(
            400,
            "Le fichier est sans nom.",
        )

    if not (
        nom.endswith(".csv")
        or nom.endswith(".xlsx")
        or nom.endswith(".xls")
    ):
        raise HTTPException(
            400,
            "Format de fichier non pris en charge. "
            "Utilisez CSV ou Excel.",
        )

    if fichier.size is not None and fichier.size == 0:
        raise HTTPException(
            400,
            "Le fichier est vide.",
        )


def _lire_fichier(
    nom_fichier: str,
    contenu: bytes,
) -> pd.DataFrame:
    try:
        if nom_fichier.lower().endswith(".csv"):
            df = pd.read_csv(
                io.BytesIO(contenu)
            )
        else:
            df = pd.read_excel(
                io.BytesIO(contenu)
            )

        if df.empty:
            raise HTTPException(
                400,
                "Le fichier est vide ou ne contient "
                "aucune ligne exploitable.",
            )

        return df

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            400,
            f"Impossible de lire le fichier : {e}",
        )


@router.post("/google-sheets/disponibilite")
async def importer_google_sheet_disponibilite(
    db: Session = Depends(get_db),
    _current=Depends(require_role("super_admin", "admin")),
):
    """
    Récupère les réponses du Google Form "Disponibilité — Séances
    en ligne" via Google Sheets et les fait passer par le pipeline
    d'ingestion (normalisation, anonymisation, thématique, NLP,
    PostgreSQL).
    """

    if not settings.google_sheets_id_disponibilite:
        raise HTTPException(
            400,
            "GOOGLE_SHEETS_ID_DISPONIBILITE n'est pas configuré.",
        )

    try:
        lignes_brutes = await lire_google_sheet(
            settings.google_sheets_id_disponibilite,
            settings.google_sheets_plage_disponibilite,
        )
    except ConfigurationGoogleManquante as e:
        raise HTTPException(400, str(e)) from e

    lignes_mappees = mapper_reponses_formulaire(lignes_brutes)

    connecteur = GoogleFormsConnecteur(donnees=lignes_mappees)
    service_ingestion = ServiceIngestion([connecteur])

    donnees_normalisees = (
        await service_ingestion.recuperer_toutes_les_donnees()
    )

    lignes_ok = 0
    lignes_erreur = 0
    erreurs = []

    for donnee in donnees_normalisees:
        try:
            with db.begin_nested():
                await enregistrer_donnee_ingestion(db, donnee)
            lignes_ok += 1
        except Exception as e:
            lignes_erreur += 1
            erreurs.append(
                {
                    "source_id": donnee.source_id,
                    "erreur": str(e),
                }
            )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            500,
            f"Impossible de finaliser l'import : {e}",
        ) from e

    return {
        "source": "google_sheets_disponibilite",
        "lignes_recuperees": len(donnees_normalisees),
        "lignes_importees": lignes_ok,
        "lignes_en_erreur": lignes_erreur,
        "erreurs": erreurs,
    }


@router.post("/typeform")
async def importer_typeform(
    db: Session = Depends(get_db),
    _current=Depends(require_role("super_admin", "admin")),
):
    """
    Récupère les réponses du formulaire Typeform via l'API
    (conformément au cahier des charges : intégration via API,
    envoyée périodiquement) et les fait passer par le pipeline
    d'ingestion (normalisation, anonymisation, thématique, NLP,
    PostgreSQL).
    """

    if not settings.typeform_form_id:
        raise HTTPException(
            400,
            "TYPEFORM_FORM_ID n'est pas configuré.",
        )

    try:
        items = await lire_reponses_typeform(
            settings.typeform_form_id
        )
    except ConfigurationTypeformManquante as e:
        raise HTTPException(400, str(e)) from e

    lignes_mappees = mapper_reponses_typeform(items)

    connecteur = TypeformConnecteur(donnees=lignes_mappees)
    service_ingestion = ServiceIngestion([connecteur])

    donnees_normalisees = (
        await service_ingestion.recuperer_toutes_les_donnees()
    )

    lignes_ok = 0
    lignes_erreur = 0
    erreurs = []

    for donnee in donnees_normalisees:
        try:
            with db.begin_nested():
                await enregistrer_donnee_ingestion(db, donnee)
            lignes_ok += 1
        except Exception as e:
            lignes_erreur += 1
            erreurs.append(
                {
                    "source_id": donnee.source_id,
                    "erreur": str(e),
                }
            )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            500,
            f"Impossible de finaliser l'import : {e}",
        ) from e

    return {
        "source": "typeform",
        "lignes_recuperees": len(donnees_normalisees),
        "lignes_importees": lignes_ok,
        "lignes_en_erreur": lignes_erreur,
        "erreurs": erreurs,
    }