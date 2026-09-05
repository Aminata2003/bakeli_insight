import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PlateformeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    nom_affiche: str
    categorie: str
    actif: bool


class UtilisateurOut(BaseModel):
    """Ne jamais inclure mot_de_passe_hash ici -- c'est justement le but de
    ce schéma séparé plutôt que de renvoyer le modèle Utilisateur brut."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    nom_complet: str
    role: str
    actif: bool


class ThematiqueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cle: str
    nom_affiche: str


class AvisOut(BaseModel):
    """Miroir exact du type RealFeedback attendu par use-feedback.ts côté frontend."""
    model_config = ConfigDict(from_attributes=True)

    feedback_id: str
    apprenant: str | None = None
    plateforme: str | None = None
    date_avis: datetime | None = None
    date_ingestion: datetime | None = None
    annee: int | None = None
    mois: int | None = None
    campus: str | None = None
    promotion: str | None = None
    formation: str | None = None
    coach: str | None = None
    satisfaction_qualitative: str | None = None
    satisfaction_score_10: int | None = None
    note: int | None = None
    sentiment: str | None = None
    resume: str | None = None
    langue_detectee: str | None = None
    frequence_feedback: str | None = None
    source_feedback: str | None = None
    attentes_formation: str | None = None
    attentes_remplies: str | None = None
    besoin_cours_theorique: str | None = None
    points_amelioration: str | None = None
    avis_activites_vendredi: str | None = None
    regroupement_niveaux: str | None = None
    commentaire_libre: str | None = None
    commentaire: str | None = None
    langue: str | None = None
    texte_a_analyser_ia: str | None = None
    statut_moderation: str
    thematique: str | None = None

class AvisListResponse(BaseModel):
    total: int
    items: list[AvisOut]