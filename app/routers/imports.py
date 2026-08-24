import io
import pandas as pd
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Avis, Plateforme
from app.mapping import mapper_colonnes_automatiquement, transformer_ligne, deduire_thematique
from app.models import Thematique  # ajoutez Thematique à l'import existant de app.models


router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/apercu")
async def apercu_fichier(fichier: UploadFile):
    contenu = await fichier.read()
    df = _lire_fichier(fichier.filename, contenu)
    colonnes = list(df.columns)
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
):
    plateforme = db.scalar(select(Plateforme).where(Plateforme.code == plateforme_code))
    if not plateforme:
        raise HTTPException(400, f"Plateforme inconnue : {plateforme_code}")

    # Charge une seule fois la correspondance cle -> id des thématiques (évite 28 requêtes en boucle)
    thematiques_par_cle = {t.cle: t.id for t in db.scalars(select(Thematique)).all()}

    contenu = await fichier.read()
    df = _lire_fichier(fichier.filename, contenu)
    mapping = mapper_colonnes_automatiquement(list(df.columns))

    lignes_ok, lignes_erreur = 0, 0
    erreurs = []

    for index, ligne in df.iterrows():
        try:
            donnees = transformer_ligne(ligne.to_dict(), mapping, index, fichier.filename)
            donnees["plateforme_id"] = plateforme.id

            # Priorité de texte identique à toFeedbackItem() du frontend :
            # texte_a_analyser_ia > commentaire_libre > points_amelioration > attentes_formation
            cle_thematique = deduire_thematique(
                donnees.get("commentaire_libre"),
                donnees.get("points_amelioration"),
                donnees.get("attentes_formation"),
            )
            donnees["thematique_id"] = thematiques_par_cle.get(cle_thematique)

            db.add(Avis(**donnees))
            lignes_ok += 1
        except Exception as e:
            lignes_erreur += 1
            erreurs.append({"ligne": index + 2, "erreur": str(e)})

    db.commit()

    return {
        "nom_fichier": fichier.filename,
        "lignes_totales": len(df),
        "lignes_importees": lignes_ok,
        "lignes_en_erreur": lignes_erreur,
        "erreurs": erreurs,
    }


def _lire_fichier(nom_fichier: str, contenu: bytes) -> pd.DataFrame:
    try:
        if nom_fichier.endswith(".csv"):
            return pd.read_csv(io.BytesIO(contenu))
        return pd.read_excel(io.BytesIO(contenu))
    except Exception as e:
        raise HTTPException(400, f"Impossible de lire le fichier : {e}")