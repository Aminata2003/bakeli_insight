import re
from dataclasses import dataclass

from app.mapping import normaliser
from app.services.huggingface import analyze_sentiment


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

NEGATIONS = {"pas", "jamais", "aucun", "aucune", "sans", "ni", "non"}
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
    précédant tokens[index], DANS LA MÊME CLAUSE."""
    debut = max(0, index - FENETRE_NEGATION)
    return any(mot in NEGATIONS for mot in tokens[debut:index])


def _score_lexical(texte_normalise: str) -> tuple[int, set[str]]:
    """Score positif/négatif basé sur le lexique local (avec gestion de la
    négation). Sert de repli si Hugging Face est indisponible, et prime sur
    Hugging Face quand du wolof est détecté (non couvert par un modèle
    généraliste)."""
    positifs = 0
    negatifs = 0
    mots_rencontres: set[str] = set()

    for clause in _decouper_en_clauses(texte_normalise):
        tokens = _tokeniser(clause)
        for i, mot in enumerate(tokens):
            mots_rencontres.add(mot)
            negue = _est_negue(tokens, i)

            if mot in POSITIFS:
                negatifs += 1 if negue else 0
                positifs += 0 if negue else 1
            elif mot in NEGATIFS:
                positifs += 1 if negue else 0
                negatifs += 0 if negue else 1

    negatifs += sum(1 for phrase in PHRASES_NEGATIVES if phrase in texte_normalise)
    return positifs - negatifs, mots_rencontres


def _sentiment_note_depuis_score(score: int) -> tuple[str, int]:
    if score > 0:
        return "positif", min(5, 3 + score)
    if score < 0:
        return "negatif", max(1, 3 + score)
    return "neutre", 3


def _note_depuis_sentiment_hf(sentiment: str) -> int:
    """Hugging Face ne renvoie qu'un label, pas d'intensité exploitable pour
    une note /5 -- on retombe sur une note neutre par polarité."""
    return {"positif": 4, "negatif": 2, "neutre": 3}[sentiment]


async def analyser_texte(texte: str | None, score_explicite: int | None = None) -> ResultatAnalyse | None:
    if not texte or not texte.strip():
        return None

    texte_nettoye = " ".join(texte.split())
    texte_normalise = normaliser(texte_nettoye)
    score_lexique, mots_rencontres = _score_lexical(texte_normalise)
    contient_wolof = bool(mots_rencontres & MOTS_WOLOF)

    if score_explicite is not None:
        # La réponse qualitative de l'étudiant prime sur toute analyse IA.
        sentiment = "positif" if score_explicite >= 8 else "negatif" if score_explicite <= 4 else "neutre"
        note = max(1, min(5, round(score_explicite / 2)))
    elif contient_wolof and score_lexique != 0:
        # Wolof détecté et non ambigu -> le lexique dédié (section 3 du
        # cahier des charges) prime sur Hugging Face, qui ne le comprend pas.
        sentiment, note = _sentiment_note_depuis_score(score_lexique)
    else:
        sentiment_hf = await analyze_sentiment(texte_nettoye)
        if sentiment_hf is not None:
            sentiment = sentiment_hf
            note = _note_depuis_sentiment_hf(sentiment)
        else:
            # Hugging Face indisponible ou échec -> repli sur le lexique local.
            sentiment, note = _sentiment_note_depuis_score(score_lexique)

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
