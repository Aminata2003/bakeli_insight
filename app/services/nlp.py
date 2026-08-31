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


def analyser_texte(texte: str | None, score_explicite: int | None = None) -> ResultatAnalyse | None:
    if not texte or not texte.strip():
        return None

    texte_nettoye = " ".join(texte.split())
    mots = set(re.findall(r"[a-zA-ZÀ-ÿ]+", normaliser(texte_nettoye)))
    positifs = len(mots & POSITIFS)
    negatifs = len(mots & NEGATIFS)
    texte_normalise = normaliser(texte_nettoye)
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

    contient_wolof = bool(mots & MOTS_WOLOF)
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
