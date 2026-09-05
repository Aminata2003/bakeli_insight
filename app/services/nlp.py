import re
from dataclasses import dataclass

from app.mapping import normaliser


POSITIFS = {
    "bon", "bonne", "excellent", "excellente", "top", "super", "bravo",
    "satisfait", "satisfaite", "clair", "patiente", "utile", "nekhna",
    "machallah", "liguey", "progresser", "progression", "pepite",
}
NEGATIFS = {
    "probleme", "bug", "panne", "lent", "lente", "frustrant", "frustrante",
    "difficile", "mauvais", "mauvaise", "insatisfait", "insatisfaite", "deugueur",
    "metina", "amoul", "crash", "crashing", "perdu", "perdue", "trop",
}
PHRASES_NEGATIVES = (
    "plus de coach",
    "augmenter les ateliers",
    "faire plus de pratique",
    "renforcer l'assistance",
    "renforcer l’assistance",
    "trop rapide",
    "trop long",
    "trop serré",
    "trop serre",
)
MOTS_WOLOF = {"nekhna", "machallah", "liguey", "metina", "deugueur", "amoul", "dafa"}

# Marqueurs de négation français courants (y compris à l'oral, sans le "ne").
# "plus" est volontairement exclu : trop ambigu ("plus de coach" est déjà une
# phrase-signal à part, et "plus" seul sert aussi de comparatif/quantité).
NEGATIONS = {"pas", "jamais", "aucun", "aucune", "sans", "ni", "non"}

# Nombre de mots précédents à vérifier pour détecter une négation portant sur
# le mot courant -- couvre "pas très satisfait", "aucun vrai probleme", etc.
FENETRE_NEGATION = 3


@dataclass(frozen=True)
class ResultatAnalyse:
    sentiment: str
    note: int
    langue_detectee: str
    resume: str


def texte_a_analyser(avis) -> str | None:
    return (
        avis.texte_a_analyser_ia
        or avis.commentaire_libre
        or avis.points_amelioration
        or avis.attentes_formation
        or avis.avis_activites_vendredi
    )


def _tokeniser(texte_normalise: str) -> list[str]:
    return re.findall(r"[a-z]+", texte_normalise)


def _decouper_en_clauses(texte_normalise: str) -> list[str]:
    """Découpe sur la ponctuation forte pour que la négation ne "traverse" pas
    une virgule/un point -- sinon "sans bug, excellent travail" négrait aussi
    "excellent" à tort."""
    return [c for c in re.split(r"[.,;!?()]+", texte_normalise) if c.strip()]


def _est_negue(tokens: list[str], index: int) -> bool:
    """Vrai si un marqueur de négation apparaît dans les FENETRE_NEGATION mots
    précédant tokens[index], DANS LA MÊME CLAUSE -- ex: pour "tres" dans
    "pas tres satisfait", on regarde ["pas"] avant "satisfait"."""
    debut = max(0, index - FENETRE_NEGATION)
    return any(mot in NEGATIONS for mot in tokens[debut:index])


def analyser_texte(texte: str | None, score_explicite: int | None = None) -> ResultatAnalyse | None:
    if not texte or not texte.strip():
        return None

    texte_nettoye = " ".join(texte.split())
    texte_normalise = normaliser(texte_nettoye)

    positifs = 0
    negatifs = 0
    mots_rencontres: set[str] = set()

    for clause in _decouper_en_clauses(texte_normalise):
        tokens = _tokeniser(clause)
        for i, mot in enumerate(tokens):
            mots_rencontres.add(mot)
            negue = _est_negue(tokens, i)

            if mot in POSITIFS:
                # "pas satisfait" -> compte comme négatif, pas positif.
                negatifs += 1 if negue else 0
                positifs += 0 if negue else 1
            elif mot in NEGATIFS:
                # "aucun probleme" -> compte comme positif, pas négatif.
                positifs += 1 if negue else 0
                negatifs += 0 if negue else 1

    negatifs += sum(1 for phrase in PHRASES_NEGATIVES if phrase in texte_normalise)
    score = positifs - negatifs

    if score_explicite is not None:
        sentiment = "positif" if score_explicite >= 8 else "negatif" if score_explicite <= 4 else "neutre"
        note = max(1, min(5, round(score_explicite / 2)))
    elif score > 0:
        sentiment, note = "positif", min(5, 3 + score)
    elif score < 0:
        sentiment, note = "negatif", max(1, 3 + score)
    else:
        sentiment, note = "neutre", 3

    contient_wolof = bool(mots_rencontres & MOTS_WOLOF)
    contient_anglais = bool(re.search(r"\b(the|learning|platform|best|support|project)\b", texte_nettoye, re.I))
    if contient_wolof and contient_anglais:
        langue = "fr-wo-en"
    elif contient_wolof:
        langue = "fr-wo"
    elif contient_anglais:
        langue = "fr-en"
    else:
        langue = "fr"

    resume = texte_nettoye[:160]
    if len(texte_nettoye) > 160:
        resume = resume.rsplit(" ", 1)[0] + "..."

    return ResultatAnalyse(sentiment, note, langue, resume)
