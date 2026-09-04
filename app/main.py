from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import SessionLocal
from app.database import SessionLocal
from app.purge import purger_identites_expirees
from app.routers import reference, avis, imports, dashboard, auth
from app.security import require_role
from app.database import SessionLocal
from app.purge import purger_identites_expirees

app = FastAPI(
    title="Bakeli Insights API",
    description="Backend de la plateforme d'écoute et d'analyse de sentiments Bakeli.",
    version="0.1.0",
)

@app.on_event("startup")
def purge_au_demarrage():
    db = SessionLocal()
    try:
        nb = purger_identites_expirees(db)
        if nb:
            print(f"[Purge RGPD] {nb} identité(s) expirée(s) supprimée(s) au démarrage.")
    finally:
        db.close()
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
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Données invalides",
                "details": exc.errors(),
            }
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bakeli-pulse-insight.lovable.app",
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
def secure_status(current=Depends(require_role("admin"))):
    return {"status": "ok", "role": current["role"]}

from app.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session


@app.post("/admin/purge")
def declencher_purge(
    db: Session = Depends(get_db),
    _current=Depends(require_role("admin")),
):
    nb = purger_identites_expirees(db)
    return {"identites_supprimees": nb}