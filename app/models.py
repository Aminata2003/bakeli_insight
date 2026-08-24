import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, SmallInteger, ForeignKey, TIMESTAMP, Boolean, Integer, ARRAY, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Plateforme(Base):
    __tablename__ = "plateformes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    nom_affiche: Mapped[str] = mapped_column(String, nullable=False)
    categorie: Mapped[str] = mapped_column(String, nullable=False)  # reseau_public | canal_prive | canal_interne
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Thematique(Base):
    __tablename__ = "thematiques"

    id: Mapped[int] = mapped_column(primary_key=True)
    cle: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # 'plateforme', 'technique', 'coach'...
    nom_affiche: Mapped[str] = mapped_column(String, nullable=False)
    mots_cles_regex: Mapped[str | None] = mapped_column(Text, nullable=True)  # motif regex, comme dans TOPIC_RULES
class Apprenant(Base):
    __tablename__ = "apprenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_anonyme: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class IdentiteTemporaire(Base):
    """PII brute. Ne JAMAIS exposer via l'API. Purge automatique après 90 jours (section 5.2)."""
    __tablename__ = "identites_temporaires"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    apprenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("apprenants.id"), nullable=False)
    prenom: Mapped[str | None] = mapped_column(String, nullable=True)
    nom: Mapped[str | None] = mapped_column(String, nullable=True)
    source_fichier: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class Avis(Base):
    """
    Miroir exact du type `RealFeedback` défini dans dataset.ts côté frontend.
    Les noms de champs sont volontairement identiques pour que l'API puisse
    être consommée sans transformation supplémentaire dans use-feedback.ts.
    """
    __tablename__ = "avis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    apprenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("apprenants.id"), nullable=True)
    feedback_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # ex: 'GF2023-0001'

    date_avis: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    annee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mois: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plateforme_id: Mapped[int] = mapped_column(ForeignKey("plateformes.id"), nullable=False)
    campus: Mapped[str | None] = mapped_column(String, nullable=True)
    promotion: Mapped[str | None] = mapped_column(String, nullable=True)
    formation: Mapped[str | None] = mapped_column(String, nullable=True)
    coach: Mapped[str | None] = mapped_column(String, nullable=True)

    satisfaction_qualitative: Mapped[str | None] = mapped_column(String, nullable=True)
    satisfaction_score_10: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    frequence_feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    source_feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    attentes_formation: Mapped[str | None] = mapped_column(Text, nullable=True)
    attentes_remplies: Mapped[str | None] = mapped_column(String, nullable=True)
    besoin_cours_theorique: Mapped[str | None] = mapped_column(String, nullable=True)
    points_amelioration: Mapped[str | None] = mapped_column(Text, nullable=True)
    avis_activites_vendredi: Mapped[str | None] = mapped_column(Text, nullable=True)
    regroupement_niveaux: Mapped[str | None] = mapped_column(String, nullable=True)
    commentaire_libre: Mapped[str | None] = mapped_column(Text, nullable=True)
    langue: Mapped[str | None] = mapped_column(String, nullable=True)
    texte_a_analyser_ia: Mapped[str | None] = mapped_column(Text, nullable=True)

    thematique_id: Mapped[int | None] = mapped_column(ForeignKey("thematiques.id"), nullable=True)

    statut_moderation: Mapped[str] = mapped_column(String, default="nouveau")
    source_fichier: Mapped[str | None] = mapped_column(String, nullable=True)

    date_ingestion: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    plateforme: Mapped["Plateforme"] = relationship()
    thematique: Mapped["Thematique | None"] = relationship()