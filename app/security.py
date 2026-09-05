from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import settings


# =========================================================
# CLÉ API (mécanisme historique, conservé pour les tests/scripts)
# =========================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme_optionnel = HTTPBearer(auto_error=False)


def _parse_api_keys() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_entry in settings.api_keys.split(","):
        entry = raw_entry.strip()
        if not entry or ":" not in entry:
            continue
        key, role = (part.strip() for part in entry.split(":", 1))
        if key and role:
            mapping[key] = role
    return mapping


# =========================================================
# JWT
# =========================================================

def creer_token_jwt(utilisateur_id: str, email: str, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    payload = {"sub": utilisateur_id, "email": email, "role": role, "exp": expiration}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decoder_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        utilisateur_id, email, role = payload.get("sub"), payload.get("email"), payload.get("role")
        if not utilisateur_id or not role:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide ou expiré")
        return {"id": utilisateur_id, "email": email, "role": role}
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Token invalide ou expiré", headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=True))],
) -> dict:
    """Utilisé par /api/auth/me -- exige toujours un JWT valide, jamais de clé API."""
    return _decoder_jwt(credentials.credentials)


# =========================================================
# AUTHENTIFICATION UNIFIÉE : JWT en priorité, sinon clé API
# =========================================================

def get_current_identity(
    x_api_key: Annotated[str | None, Depends(api_key_header)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme_optionnel)],
) -> dict:
    """Point d'entrée unique pour tous les endpoints de données : accepte
    SOIT un token JWT (Authorization: Bearer ..., utilisateur réel connecté),
    SOIT une clé API (X-API-Key, pour les scripts/tests). Le JWT est vérifié
    en priorité s'il est présent."""
    if credentials is not None:
        return _decoder_jwt(credentials.credentials)

    if x_api_key:
        role = _parse_api_keys().get(x_api_key)
        if role:
            return {"id": None, "email": None, "role": role}
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clé API invalide")

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification manquante (token ou clé API)")


def require_role(*allowed_roles: str):
    async def dependency(current: Annotated[dict, Depends(get_current_identity)]) -> dict:
        if current["role"] not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Rôle requis : {', '.join(allowed_roles)}")
        return current

    return dependency
def require_jwt_role(*allowed_roles: str):
    async def dependency(
        current: Annotated[dict, Depends(get_current_user)]
    ) -> dict:
        if current["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle requis : {', '.join(allowed_roles)}",
            )
        return current

    return dependency