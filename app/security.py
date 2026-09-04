from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import settings


# =========================================================
# API KEY
# =========================================================

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


def _parse_api_keys() -> dict[str, str]:
    mapping: dict[str, str] = {}

    for raw_entry in settings.api_keys.split(","):
        entry = raw_entry.strip()

        if not entry or ":" not in entry:
            continue

        key, role = (
            part.strip()
            for part in entry.split(":", 1)
        )

        if key and role:
            mapping[key] = role

    return mapping


def get_current_api_key(
    x_api_key: Annotated[str | None, Depends(api_key_header)],
) -> dict[str, str]:

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API manquante"
        )

    key_roles = _parse_api_keys()
    role = key_roles.get(x_api_key)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide"
        )

    return {
        "key": x_api_key,
        "role": role
    }


def require_role(*allowed_roles: str):

    async def dependency(
        current: Annotated[
            dict[str, str],
            Depends(get_current_api_key)
        ],
    ) -> dict[str, str]:

        if current["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle requis : {', '.join(allowed_roles)}"
            )

        return current

    return dependency


# =========================================================
# JWT
# =========================================================

bearer_scheme = HTTPBearer(
    auto_error=True
)


def creer_token_jwt(
    utilisateur_id: str,
    email: str,
    role: str,
) -> str:

    expiration = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.jwt_expiration_minutes
        )
    )

    payload = {
        "sub": utilisateur_id,
        "email": email,
        "role": role,
        "exp": expiration,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme)
    ],
) -> dict:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        utilisateur_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")

        if not utilisateur_id or not email or not role:
            raise credentials_exception

        return {
            "id": utilisateur_id,
            "email": email,
            "role": role,
        }

    except JWTError:
        raise credentials_exception


def require_jwt_role(*allowed_roles: str):

    async def dependency(
        current: Annotated[
            dict,
            Depends(get_current_user)
        ],
    ) -> dict:

        if current["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle requis : {', '.join(allowed_roles)}"
            )

        return current

    return dependency