import io
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Avis, Plateforme
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

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/apercu")
async def apercu_fichier(
    fichier: UploadFile,
    _current=Depends(require_role("admin", "analyst")),
):
    _valider_fichier(fichier)
    contenu = await fichier.read()
    df = _lire_fichier(fichier.filename, contenu)
    colonnes = list(df.columns)
    if df.empty:
        raise HTTPException(400, "Le fichier est vide ou ne contient aucune ligne exploitable.")
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
    _current=Depends(require_role("admin", "analyst")),
):
    _valider_fichier(fichier)
    plateforme = db.scalar(select(Plateforme).where(Plateforme.code == plateforme_code))
    if not plateforme:
        raise HTTPException(400, f"Plateforme inconnue : {plateforme_code}")

    # Charge une seule fois la correspondance cle -> id des thématiques (évite 28 requêtes en boucle)
    thematiques_par_cle = {t.cle: t.id for t in db.scalars(select(Thematique)).all()}

    contenu = await fichier.read()
    df = _lire_fichier(fichier.filename, contenu)
    mapping = mapper_colonnes_automatiquement(list(df.columns))

    feedback_ids = [
        f"{fichier.filename}-{index + 1:04d}" for index in range(len(df))
    ]
    feedback_ids_existants = set(
        db.scalars(
            select(Avis.feedback_id).where(Avis.feedback_id.in_(feedback_ids))
        ).all()
    )

    lignes_ok, lignes_erreur, lignes_ignorees = 0, 0, 0
    erreurs = []

    for index, ligne in df.iterrows():
        if feedback_ids[index] in feedback_ids_existants:
            lignes_ignorees += 1
            continue

        try:
            with db.begin_nested():
                donnees = transformer_ligne(ligne.to_dict(), mapping, index, fichier.filename)
                donnees["plateforme_id"] = plateforme.id
                ligne_dict = ligne.to_dict()
                prenom = extraire_valeur(ligne_dict, mapping, "prenom")
                nom = extraire_valeur(ligne_dict, mapping, "nom")
                donnees["apprenant_id"] = resoudre_apprenant(
                    db, str(prenom) if prenom else None, str(nom) if nom else None, fichier.filename
                )
                # Priorité de texte identique à toFeedbackItem() du frontend :
                # texte_a_analyser_ia > commentaire_libre > points_amelioration > attentes_formation
                cle_thematique = deduire_thematique(
                    donnees.get("texte_a_analyser_ia"),
                    donnees.get("commentaire_libre"),
                    donnees.get("points_amelioration"),
                    donnees.get("attentes_formation"),
                )
                donnees["thematique_id"] = thematiques_par_cle.get(cle_thematique)
                texte_analyse = (
                    donnees.get("texte_a_analyser_ia")
                    or donnees.get("commentaire_libre")
                    or donnees.get("points_amelioration")
                    or donnees.get("attentes_formation")
                )
                analyse = analyser_texte(texte_analyse, donnees.get("satisfaction_score_10"))
                if analyse:
                    donnees["sentiment"] = analyse.sentiment
                    donnees["note"] = analyse.note
                    donnees["resume"] = analyse.resume
                    donnees["langue_detectee"] = analyse.langue_detectee
                    donnees["date_traitement_ia"] = datetime.now(timezone.utc)

                db.add(Avis(**donnees))
                db.flush()
            lignes_ok += 1
        except Exception as e:
            lignes_erreur += 1
            erreurs.append({"ligne": index + 2, "erreur": str(e)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Impossible de finaliser l'import : {e}") from e

    return {
        "nom_fichier": fichier.filename,
        "lignes_totales": len(df),
        "lignes_importees": lignes_ok,
        "lignes_deja_importees": lignes_ignorees,
        "lignes_en_erreur": lignes_erreur,
        "erreurs": erreurs,
    }


def _valider_fichier(fichier: UploadFile) -> None:
    nom = (fichier.filename or "").lower()
    if not nom:
        raise HTTPException(400, "Le fichier est sans nom.")
    if not (nom.endswith(".csv") or nom.endswith(".xlsx") or nom.endswith(".xls")):
        raise HTTPException(400, "Format de fichier non pris en charge. Utilisez CSV ou Excel.")

    if fichier.size is not None and fichier.size == 0:
        raise HTTPException(400, "Le fichier est vide.")


def _lire_fichier(nom_fichier: str, contenu: bytes) -> pd.DataFrame:
    try:
        if nom_fichier.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contenu))
        else:
            df = pd.read_excel(io.BytesIO(contenu))
        if df.empty:
            raise HTTPException(400, "Le fichier est vide ou ne contient aucune ligne exploitable.")
        return df
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Impossible de lire le fichier : {e}")