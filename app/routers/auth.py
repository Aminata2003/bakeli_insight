import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Utilisateur
from app.auth_password import verifier_mot_de_passe, hacher_mot_de_passe
from app.security import creer_token_jwt, get_current_user, require_jwt_role
from app.schemas import UtilisateurOut


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentification"],
)


# ============================================================
# SCHEMAS
# ============================================================

class LoginRequest(BaseModel):
    email: str
    mot_de_passe: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    utilisateur: dict


class CreerUtilisateurRequest(BaseModel):
    email: str
    nom_complet: str
    mot_de_passe: str
    role: str


class ChangerMotDePasseRequest(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):

    utilisateur = (
        db.query(Utilisateur)
        .filter(Utilisateur.email == credentials.email)
        .first()
    )

    if not utilisateur:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not utilisateur.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé",
        )

    mot_de_passe_valide = verifier_mot_de_passe(
        credentials.mot_de_passe,
        utilisateur.mot_de_passe_hash,
    )

    if not mot_de_passe_valide:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    token = creer_token_jwt(
        utilisateur_id=str(utilisateur.id),
        email=utilisateur.email,
        role=utilisateur.role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "utilisateur": {
            "id": str(utilisateur.id),
            "email": utilisateur.email,
            "nom_complet": utilisateur.nom_complet,
            "role": utilisateur.role,
        },
    }


# ============================================================
# UTILISATEUR CONNECTÉ
# ============================================================

@router.get("/me")
def me(
    current_user: dict = Depends(get_current_user),
):
    return current_user


# ============================================================
# LISTE DES UTILISATEURS (pour la page Paramètres -> Équipe)
# ============================================================

@router.get("/utilisateurs", response_model=list[UtilisateurOut])
def lister_utilisateurs(
    db: Session = Depends(get_db),
    _current=Depends(require_jwt_role("super_admin", "admin")),
):
    """Réservé aux admins -- affiche les vrais comptes de la plateforme,
    jamais les mots de passe hashés (cf. UtilisateurOut)."""
    return db.query(Utilisateur).order_by(Utilisateur.nom_complet).all()


ROLES_VALIDES = {"super_admin", "admin", "collaborator"}


@router.post("/utilisateurs", response_model=UtilisateurOut, status_code=status.HTTP_201_CREATED)
def creer_utilisateur(
    donnees: CreerUtilisateurRequest,
    db: Session = Depends(get_db),
    _current=Depends(require_jwt_role("super_admin")),
):
    """Création directe d'un compte par un super_admin -- pas d'auto-
    inscription (note du DG) : c'est la seule façon de créer un compte."""
    if donnees.role not in ROLES_VALIDES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rôle invalide -- attendu : {', '.join(sorted(ROLES_VALIDES))}",
        )

    existant = db.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if existant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà.",
        )

    utilisateur = Utilisateur(
        email=donnees.email,
        nom_complet=donnees.nom_complet,
        role=donnees.role,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
    )
    db.add(utilisateur)
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


# ============================================================
# CHANGEMENT DE MOT DE PASSE (compte connecté uniquement)
# ============================================================

@router.patch("/mot-de-passe")
def changer_mot_de_passe(
    donnees: ChangerMotDePasseRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Permet à l'utilisateur connecté de changer SON PROPRE mot de passe --
    aucun rôle particulier requis au-delà d'être authentifié, mais on ne
    touche jamais au compte d'un autre utilisateur ici."""
    utilisateur = db.get(Utilisateur, uuid.UUID(current_user["id"]))
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable")

    if not verifier_mot_de_passe(donnees.ancien_mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ancien mot de passe incorrect",
        )

    if len(donnees.nouveau_mot_de_passe) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit contenir au moins 8 caractères",
        )

    utilisateur.mot_de_passe_hash = hacher_mot_de_passe(donnees.nouveau_mot_de_passe)
    db.commit()
    return {"message": "Mot de passe mis à jour"}