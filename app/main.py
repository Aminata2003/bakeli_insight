import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.purge import purger_identites_expirees
from app.routers import reference, avis, imports, dashboard, auth
from app.security import require_role


async def purge_quotidienne():
    """
    Lance la purge RGPD au démarrage puis toutes les 24 heures.
    """
    while True:
        db = SessionLocal()

        try:
            nb = purger_identites_expirees(db)

            if nb:
                print(
                    f"[Purge RGPD] {nb} identite(s) expiree(s) "
                    f"supprimee(s)."
                )
            else:
                print("[Purge RGPD] Aucune identite expiree a supprimer.")

        except Exception as exc:
            print(f"[Purge RGPD] Erreur pendant la purge : {exc}")

        finally:
            db.close()

        # Attendre 24 heures avant la prochaine purge
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.

    La purge RGPD démarre avec l'application et tourne
    automatiquement toutes les 24 heures.
    """
    purge_task = asyncio.create_task(purge_quotidienne())

    try:
        yield
    finally:
        purge_task.cancel()

        try:
            await purge_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Bakeli Insights API",
    description="Backend de la plateforme d'ecoute et d'analyse de sentiments Bakeli.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": {
                    400: "bad_request",
                    401: "unauthorized",
                    403: "forbidden",
                    404: "not_found",
                    409: "conflict",
                    422: "validation_error",
                    500: "internal_error",
                }.get(exc.status_code, "http_error"),
                "message": exc.detail,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Donnees invalides",
                "details": exc.errors(),
            }
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bakeli-pulse-insight.lovable.app",
        "https://insights.bakeli.tech",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8081",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(reference.router)
app.include_router(avis.router)
app.include_router(imports.router)
app.include_router(dashboard.router)
app.include_router(auth.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/secure-status")
def secure_status(
    current=Depends(require_role("admin")),
):
    return {
        "status": "ok",
        "role": current["role"],
    }


@app.post("/admin/purge")
def declencher_purge(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin")),
):
    nb = purger_identites_expirees(db)

    return {
        "identites_supprimees": nb,
    }