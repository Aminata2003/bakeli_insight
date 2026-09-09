from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Avis, Import, Plateforme
from app.security import get_current_user


router = APIRouter(
    prefix="/assistant",
    tags=["Assistant IA"],
)


# ============================================================
# SCHEMAS
# ============================================================

class AssistantRequest(BaseModel):
    question: str
    lang: str = "fr"


class AssistantResponse(BaseModel):
    answer: str


# ============================================================
# OUTILS D'ANALYSE
# ============================================================

def compter_avis(db: Session) -> int:
    return db.query(func.count(Avis.id)).scalar() or 0


def compter_plateformes(db: Session) -> int:
    return (
        db.query(func.count(func.distinct(Avis.plateforme_id)))
        .scalar()
        or 0
    )


def plateforme_plus_active(db: Session):
    resultat = (
        db.query(
            Plateforme.nom_affiche,
            func.count(Avis.id).label("nombre"),
        )
        .join(Avis, Avis.plateforme_id == Plateforme.id)
        .group_by(Plateforme.id, Plateforme.nom_affiche)
        .order_by(func.count(Avis.id).desc())
        .first()
    )

    if not resultat:
        return None

    return {
        "plateforme": resultat.nom_affiche,
        "nombre": resultat.nombre,
    }


def satisfaction_globale(db: Session):
    resultat = (
        db.query(
            func.avg(Avis.satisfaction_score_10),
            func.count(Avis.id),
        )
        .filter(Avis.satisfaction_score_10.isnot(None))
        .first()
    )

    moyenne = resultat[0] if resultat else None
    nombre = resultat[1] if resultat else 0

    if moyenne is None:
        return None

    return {
        "moyenne": float(moyenne),
        "nombre": nombre,
    }


def sentiments(db: Session):
    resultat = (
        db.query(
            Avis.sentiment,
            func.count(Avis.id).label("nombre"),
        )
        .filter(Avis.sentiment.isnot(None))
        .group_by(Avis.sentiment)
        .all()
    )

    return {
        str(sentiment): nombre
        for sentiment, nombre in resultat
    }


def meilleur_coach(db: Session):
    resultat = (
        db.query(
            Avis.coach,
            func.avg(Avis.satisfaction_score_10).label("moyenne"),
            func.count(Avis.id).label("nombre"),
        )
        .filter(
            Avis.coach.isnot(None),
            Avis.coach != "",
            Avis.satisfaction_score_10.isnot(None),
        )
        .group_by(Avis.coach)
        .having(func.count(Avis.id) > 0)
        .order_by(func.avg(Avis.satisfaction_score_10).desc())
        .first()
    )

    if not resultat:
        return None

    return {
        "coach": resultat.coach,
        "moyenne": float(resultat.moyenne),
        "nombre": resultat.nombre,
    }


def campus_plus_negatif(db: Session):
    resultat = (
        db.query(
            Avis.campus,
            func.count(Avis.id).label("nombre"),
        )
        .filter(
            Avis.campus.isnot(None),
            Avis.sentiment == "negatif",
        )
        .group_by(Avis.campus)
        .order_by(func.count(Avis.id).desc())
        .first()
    )

    if not resultat:
        return None

    return {
        "campus": resultat.campus,
        "nombre": resultat.nombre,
    }


def compter_imports(db: Session) -> int:
    return db.query(func.count(Import.id)).scalar() or 0


# ============================================================
# ASSISTANT
# ============================================================

@router.post("/chat", response_model=AssistantResponse)
def assistant_chat(
    request: AssistantRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    question = request.question.strip().lower()

    if not question:
        return {
            "answer": (
                "Posez-moi une question sur les avis, les plateformes, "
                "les coachs, les campus ou la satisfaction."
            )
        }

    lang = request.lang if request.lang in {"fr", "en"} else "fr"

    # ========================================================
    # NOMBRE TOTAL D'AVIS
    # ========================================================

    if (
        ("combien" in question or "nombre" in question or "total" in question)
        and any(
            mot in question
            for mot in ["avis", "feedback", "commentaire", "retour"]
        )
    ):
        nombre = compter_avis(db)

        if lang == "en":
            return {
                "answer": f"There are currently {nombre:,} feedback items in the database."
            }

        return {
            "answer": f"Nous avons actuellement {nombre:,} avis enregistrés dans la base de données."
        }

    # ========================================================
    # NOMBRE DE PLATEFORMES
    # ========================================================

    if (
        ("combien" in question or "nombre" in question)
        and any(
            mot in question
            for mot in ["plateforme", "plateformes", "platform"]
        )
    ):
        nombre = compter_plateformes(db)

        if lang == "en":
            return {
                "answer": f"There are currently {nombre} platforms represented in the feedback."
            }

        return {
            "answer": (
                f"Il y a actuellement {nombre} plateforme"
                f"{'s' if nombre > 1 else ''} représentée"
                f"{'s' if nombre > 1 else ''} dans les avis."
            )
        }

    # ========================================================
    # PLATEFORME LA PLUS ACTIVE
    # ========================================================

    if (
        any(mot in question for mot in ["plateforme", "platform"])
        and any(
            mot in question
            for mot in [
                "plus",
                "most",
                "active",
                "genere",
                "génère",
            ]
        )
    ):
        resultat = plateforme_plus_active(db)

        if not resultat:
            return {
                "answer": (
                    "Aucune donnée de plateforme n'est actuellement disponible."
                    if lang == "fr"
                    else "No platform data is currently available."
                )
            }

        if lang == "en":
            return {
                "answer": (
                    f"{resultat['plateforme']} generates the most feedback "
                    f"with {resultat['nombre']:,} items."
                )
            }

        return {
            "answer": (
                f"{resultat['plateforme']} génère le plus d'avis "
                f"avec {resultat['nombre']:,} avis."
            )
        }

    # ========================================================
    # SATISFACTION
    # ========================================================

    if any(
        mot in question
        for mot in [
            "satisfaction",
            "satisfait",
            "indice de satisfaction",
            "score global",
        ]
    ):
        resultat = satisfaction_globale(db)

        if not resultat:
            return {
                "answer": (
                    "Aucune note de satisfaction n'est disponible."
                    if lang == "fr"
                    else "No satisfaction score is available."
                )
            }

        if lang == "en":
            return {
                "answer": (
                    f"The average satisfaction score is "
                    f"{resultat['moyenne']:.1f}/10 "
                    f"based on {resultat['nombre']:,} ratings."
                )
            }

        return {
            "answer": (
                f"L'indice moyen de satisfaction est de "
                f"{resultat['moyenne']:.1f}/10 "
                f"sur {resultat['nombre']:,} avis notés."
            )
        }

    # ========================================================
    # MEILLEUR COACH
    # ========================================================

    if (
        "coach" in question
        and any(
            mot in question
            for mot in [
                "meilleur",
                "meilleure",
                "meilleurs",
                "top",
                "best",
                "note",
                "score",
            ]
        )
    ):
        resultat = meilleur_coach(db)

        if not resultat:
            return {
                "answer": (
                    "Aucun coach avec des notes exploitables n'est disponible."
                    if lang == "fr"
                    else "No coach with usable ratings is available."
                )
            }

        if lang == "en":
            return {
                "answer": (
                    f"The top-rated coach is {resultat['coach']}, "
                    f"with an average score of {resultat['moyenne']:.1f}/10 "
                    f"across {resultat['nombre']} feedback items."
                )
            }

        return {
            "answer": (
                f"Le coach avec le meilleur score est {resultat['coach']}, "
                f"avec une moyenne de {resultat['moyenne']:.1f}/10 "
                f"sur {resultat['nombre']} avis."
            )
        }

    # ========================================================
    # CAMPUS AVEC LE PLUS D'AVIS NEGATIFS
    # ========================================================

    if (
        "campus" in question
        and any(
            mot in question
            for mot in [
                "plainte",
                "plaintes",
                "negatif",
                "négatif",
                "probleme",
                "problème",
                "complaint",
                "negative",
            ]
        )
    ):
        resultat = campus_plus_negatif(db)

        if not resultat:
            return {
                "answer": (
                    "Aucun avis négatif n'est actuellement recensé par campus."
                    if lang == "fr"
                    else "No negative feedback is currently recorded by campus."
                )
            }

        if lang == "en":
            return {
                "answer": (
                    f"{resultat['campus']} has the most negative feedback, "
                    f"with {resultat['nombre']} negative items."
                )
            }

        return {
            "answer": (
                f"Le campus qui reçoit le plus d'avis négatifs est "
                f"{resultat['campus']}, avec {resultat['nombre']} avis négatifs."
            )
        }

    # ========================================================
    # NOMBRE D'IMPORTS
    # ========================================================

    if (
        any(mot in question for mot in ["import", "imports", "fichier"])
        and any(
            mot in question
            for mot in ["combien", "nombre", "total"]
        )
    ):
        nombre = compter_imports(db)

        if lang == "en":
            return {
                "answer": f"There are currently {nombre} imports recorded."
            }

        return {
            "answer": f"Il y a actuellement {nombre} import(s) enregistré(s) dans la base de données."
        }

    # ========================================================
    # FALLBACK
    # ========================================================

    if lang == "en":
        return {
            "answer": (
                "I don't understand this question yet. "
                "Try asking about the number of feedback items, "
                "platforms, coaches, campuses, satisfaction, or imports."
            )
        }

    return {
        "answer": (
            "Je ne comprends pas encore cette question. "
            "Essayez par exemple : « Combien d'avis avons-nous ? », "
            "« Quelle plateforme génère le plus d'avis ? », "
            "« Quel coach reçoit les meilleurs avis ? » ou "
            "« Quel est le taux de satisfaction ? »"
        )
    }