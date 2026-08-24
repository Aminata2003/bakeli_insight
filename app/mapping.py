import unicodedata


def normaliser(texte: str) -> str:
    """Enlève les accents et met en minuscule, pour comparer les colonnes sans se soucier de la casse/accents."""
    texte = texte.lower().strip()
    texte = unicodedata.normalize("NFD", texte)
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


# Mêmes champs cibles que RealFeedback (dataset.ts), avec les mots-clés qui permettent
# de reconnaître une colonne de fichier Excel/CSV brut.
ALIASES: dict[str, list[str]] = {
    "date_avis": ["horodateur", "horodatage", "timestamp", "date"],
    "formation": ["domaine de formation", "formation", "programme", "cours"],
    "campus": ["campus"],
    "promotion": ["promotion"],
    "coach": ["coach", "qui est ton coach"],
    "satisfaction_qualitative": ["satisfait du coaching", "satisfaction", "niveau de satisfaction"],
    "frequence_feedback": ["frequence"],
    "source_feedback": ["source"],
    "attentes_formation": ["attentes de la formation", "attentes"],
    "attentes_remplies": ["remplies", "attentes_remplies"],
    "besoin_cours_theorique": ["cours theorique"],
    "points_amelioration": ["ameliorer", "points a ameliorer", "suggestions"],
    "avis_activites_vendredi": ["vendredi"],
    "regroupement_niveaux": ["regroupement"],
    "commentaire_libre": ["commentaire", "remarque"],
    "langue": ["langue"],
}


def mapper_colonnes_automatiquement(colonnes: list[str]) -> dict[str, str | None]:
    """Pour chaque colonne du fichier, cherche le mot-clé le PLUS LONG qui correspond,
    tous champs confondus -- ça évite qu'un mot générique comme "formation" ou "coach"
    l'emporte à tort sur un mot-clé plus précis comme "attentes de la formation"."""
    resultat: dict[str, str | None] = {}

    for colonne in colonnes:
        col_norm = normaliser(colonne)
        meilleur_champ: str | None = None
        meilleure_longueur = 0

        for champ, mots_cles in ALIASES.items():
            for mot in mots_cles:
                mot_norm = normaliser(mot)
                if mot_norm in col_norm and len(mot_norm) > meilleure_longueur:
                    meilleur_champ = champ
                    meilleure_longueur = len(mot_norm)

        resultat[colonne] = meilleur_champ

    return resultat
import pandas as pd

SATISFACTION_SCALE: dict[str, int] = {
    "tres satisfait": 10,
    "satisfait": 8,
    "peu satisfait": 5,
    "insatisfait": 2,
}


def score_depuis_qualitatif(valeur) -> int | None:
    """Reproduit SATISFACTION_SCALE de dataset.ts : convertit une réponse qualitative en score /10."""
    if not isinstance(valeur, str) or not valeur.strip():
        return None
    cle = normaliser(valeur)
    return SATISFACTION_SCALE.get(cle)


def transformer_ligne(ligne: dict, mapping: dict[str, str | None], index: int, nom_fichier: str) -> dict:
    """Convertit une ligne brute du fichier (dict colonne->valeur) en dict prêt pour la table `avis`,
    en utilisant le mapping de colonnes déjà calculé."""

    def valeur_pour(champ_cible: str):
        for colonne, champ in mapping.items():
            if champ == champ_cible:
                v = ligne.get(colonne)
                if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
                    return None
                return v
        return None

    date_avis_brute = valeur_pour("date_avis")
    date_avis = None
    annee = mois = None
    if date_avis_brute is not None:
        try:
            d = pd.to_datetime(date_avis_brute)
            date_avis = d.to_pydatetime()
            annee, mois = d.year, d.month
        except Exception:
            pass  # date illisible : on laisse tout à None plutôt que de faire planter l'import

    satisfaction_qualitative = valeur_pour("satisfaction_qualitative")
    satisfaction_qualitative_str = str(satisfaction_qualitative) if satisfaction_qualitative else None

    return {
        "feedback_id": f"{nom_fichier}-{index + 1:04d}",
        "date_avis": date_avis,
        "annee": annee,
        "mois": mois,
        "campus": str(valeur_pour("campus")) if valeur_pour("campus") else None,
        "promotion": str(valeur_pour("promotion")) if valeur_pour("promotion") else None,
        "formation": str(valeur_pour("formation")) if valeur_pour("formation") else None,
        "coach": str(valeur_pour("coach")) if valeur_pour("coach") else None,
        "satisfaction_qualitative": satisfaction_qualitative_str,
        "satisfaction_score_10": score_depuis_qualitatif(satisfaction_qualitative_str),
        "frequence_feedback": str(valeur_pour("frequence_feedback")) if valeur_pour("frequence_feedback") else None,
        "source_feedback": str(valeur_pour("source_feedback")) if valeur_pour("source_feedback") else None,
        "attentes_formation": str(valeur_pour("attentes_formation")) if valeur_pour("attentes_formation") else None,
        "attentes_remplies": str(valeur_pour("attentes_remplies")) if valeur_pour("attentes_remplies") else None,
        "besoin_cours_theorique": str(valeur_pour("besoin_cours_theorique")) if valeur_pour("besoin_cours_theorique") else None,
        "points_amelioration": str(valeur_pour("points_amelioration")) if valeur_pour("points_amelioration") else None,
        "avis_activites_vendredi": str(valeur_pour("avis_activites_vendredi")) if valeur_pour("avis_activites_vendredi") else None,
        "regroupement_niveaux": str(valeur_pour("regroupement_niveaux")) if valeur_pour("regroupement_niveaux") else None,
        "commentaire_libre": str(valeur_pour("commentaire_libre")) if valeur_pour("commentaire_libre") else None,
        "langue": str(valeur_pour("langue")) if valeur_pour("langue") else "Français",
        "source_fichier": nom_fichier,
    }
import re

# Reproduit TOPIC_RULES de derive.ts (frontend) -- même ordre, mêmes motifs.
TOPIC_RULES: list[tuple[str, str]] = [
    ("plateforme",      r"platefor|plateform|platform|connexion|login|compte|site"),
    ("technique",       r"wifi|bug|technique|ordinateur|machine|réseau|reseau|panne|électric|electric"),
    ("coach",           r"coach|formateur|encadr|prof"),
    ("planning",        r"rythme|horaire|planning|retard|temps|durée|duree|vendredi"),
    ("projets",         r"projet|exercice|pratique|tp\b"),
    ("administration",  r"administra|inscription|paiement|frais|attestation|certificat"),
    ("pedagogie",       r"cours|théori|theori|contenu|apprentissage|module|niveau|pédagog|pedagog"),
]


def deduire_thematique(*textes: str | None) -> str:
    """Cherche la première règle qui matche dans les textes fournis (dans l'ordre donné).
    Reproduit inferTopic() de derive.ts. Retombe sur 'pedagogie' si rien ne matche (comportement identique au frontend)."""
    texte_complet = " ".join(t for t in textes if t) or ""
    for cle, motif in TOPIC_RULES:
        if re.search(motif, texte_complet, re.IGNORECASE):
            return cle
    return "pedagogie"