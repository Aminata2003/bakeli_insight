import re
from collections import Counter

from app.mapping import normaliser
from app.models import Avis

# Section 3 du cahier des charges : dictionnaire contextuel sénégalais.
# Ces expressions sont cherchées comme des blocs entiers (pas mot par mot),
# avant la tokenisation générique -- sinon "dafa deugueur" serait cassé en
# deux mots isolés sans intérêt individuellement.
EXPRESSIONS_SENEGALAISES: dict[str, str] = {
    "nekhna": "positif",
    "machallah": "positif",
    "top": "positif",
    "bakeli dagnouy liguey": "positif",
    "metina": "negatif",
    "dafa deugueur": "negatif",
    "probleme la": "negatif",
    "amoul sens": "negatif",
}

# Mots français trop fréquents pour être informatifs dans un nuage de mots.
MOTS_VIDES: set[str] = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "est", "il", "elle",
    "que", "qui", "quoi", "pas", "plus", "avec", "pour", "dans", "sur", "ce",
    "cette", "ces", "ses", "son", "sa", "mais", "ou", "donc", "car", "ne", "se",
    "sont", "etait", "etre", "avoir", "ai", "as", "a", "au", "aux", "en", "je",
    "tu", "on", "nous", "vous", "ils", "elles", "mon", "ma", "mes", "ton", "ta",
    "tes", "leur", "leurs", "y", "si", "tres", "bien", "fait", "faire", "comme",
    "meme", "tout", "tous", "toute", "toutes", "aussi", "alors", "encore", "peu",
    "cela", "ca", "etc", "dont", "d", "l", "j", "n", "s", "c", "qu",
}

_MOT_REGEX = re.compile(r"[a-zàâäéèêëïîôöùûüç]+", re.IGNORECASE)


def _texte_prioritaire(avis: Avis) -> str | None:
    """Même priorité que dans imports.py / la déduction de thématique :
    texte_a_analyser_ia > commentaire_libre > points_amelioration > attentes_formation."""
    return (
        avis.texte_a_analyser_ia
        or avis.commentaire_libre
        or avis.points_amelioration
        or avis.attentes_formation
    )


_FR_VERS_EN = {"positif": "positive", "negatif": "negative", "neutre": "neutral"}


def _sentiment_effectif(avis: Avis) -> str:
    """Reproduit la logique de dashboard.py (vue-ensemble) : sentiment stocké en
    priorité, sinon dérivé du score /10. Valeur renvoyée en anglais
    (positive/neutral/negative) pour rester cohérent avec /dashboard/vue-ensemble
    et le format déjà utilisé par wordCloud côté frontend (mock-data.ts)."""
    if avis.sentiment:
        return _FR_VERS_EN.get(avis.sentiment, "neutral")

    score = avis.satisfaction_score_10 if avis.satisfaction_score_10 is not None else (
        avis.note * 2 if avis.note is not None else None
    )
    if score is None:
        return "neutral"
    if score >= 8:
        return "positive"
    if score <= 4:
        return "negative"
    return "neutral"


def calculer_wordcloud(avis_list: list[Avis], limite: int = 30) -> list[dict]:
    """Calcule les mots/expressions les plus fréquents, avec un poids normalisé
    sur 100 et un sentiment majoritaire par terme -- format attendu par le
    frontend : { text, weight, sentiment } (voir wordCloud dans mock-data.ts)."""

    compteur: Counter[str] = Counter()
    sentiments_par_terme: dict[str, Counter[str]] = {}
    libelle_original: dict[str, str] = {}

    for avis in avis_list:
        texte_brut = _texte_prioritaire(avis)
        if not texte_brut:
            continue

        texte_norm = normaliser(texte_brut)
        sentiment = _sentiment_effectif(avis)
        texte_restant = texte_norm

        # 1. Expressions sénégalaises connues, en priorité sur la tokenisation générique.
        for expression in EXPRESSIONS_SENEGALAISES:
            if expression in texte_restant:
                compteur[expression] += 1
                sentiments_par_terme.setdefault(expression, Counter())[sentiment] += 1
                libelle_original.setdefault(expression, expression.title())
                texte_restant = texte_restant.replace(expression, " ")

        # 2. Mots génériques restants (hors mots vides et mots trop courts).
        for mot in _MOT_REGEX.findall(texte_restant):
            if len(mot) < 3 or mot in MOTS_VIDES:
                continue
            compteur[mot] += 1
            sentiments_par_terme.setdefault(mot, Counter())[sentiment] += 1
            libelle_original.setdefault(mot, mot.capitalize())

    if not compteur:
        return []

    plus_frequent = compteur.most_common(1)[0][1]

    resultats = []
    for terme, frequence in compteur.most_common(limite):
        sentiment_dominant = sentiments_par_terme[terme].most_common(1)[0][0]
        resultats.append({
            "text": libelle_original[terme],
            "weight": round((frequence / plus_frequent) * 100),
            "sentiment": sentiment_dominant,
        })

    return resultats
