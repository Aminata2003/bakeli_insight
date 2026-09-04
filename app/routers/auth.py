from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Utilisateur
from app.auth_password import verifier_mot_de_passe
from app.security import creer_token_jwt, get_current_user


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