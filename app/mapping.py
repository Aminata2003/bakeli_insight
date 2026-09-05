
import re
import unicodedata

import pandas as pd


def normaliser(texte: str) -> str:
    """Normalise un texte pour faciliter la comparaison."""
    texte = str(texte).lower().strip()
    texte = unicodedata.normalize("NFD", texte)
    return "".join(
        c for c in texte
        if unicodedata.category(c) != "Mn"
    )


# Les alias les plus spécifiques sont placés en premier.
# On évite ainsi qu'un mot générique comme "coach" ou
# "nom" ne prenne une colonne qui appartient à un autre champ.
ALIASES: dict[str, list[str]] = {
    "date_avis": [
        "horodateur",
        "horodatage",
        "timestamp",
        "date de reponse",
        "date de réponse",
        "date",
    ],

    "formation": [
        "domaine de formation",
        "domaine de la formation",
        "nom de la formation",
        "formation suivie",
        "formation",
        "programme",
        "cours",
    ],

    "campus": [
        "quel est ton campus",
        "quel est votre campus",
        "votre campus",
        "ton campus",
        "campus",
    ],

    "promotion": [
        "quelle est ta promotion",
        "quelle est votre promotion",
        "votre promotion",
        "ta promotion",
        "promotion",
    ],

    "coach": [
        "qui est ton coach",
        "qui est votre coach",
        "nom du coach",
        "nom de ton coach",
        "nom de votre coach",
        "quel est le nom de ton coach",
        "quel est le nom de votre coach",
    ],

    "satisfaction_qualitative": [
        "quel est ton niveau de satisfaction concernant le coaching",
        "quel est votre niveau de satisfaction concernant le coaching",
        "niveau de satisfaction concernant le coaching",
        "satisfaction concernant le coaching",
        "es tu satisfait du coaching",
        "etes vous satisfait du coaching",
        "êtes vous satisfait du coaching",
        "satisfait du coaching",
        "niveau de satisfaction",
        "satisfaction",
    ],

    "frequence_feedback": [
        "frequence",
        "fréquence",
    ],

    "source_feedback": [
        "source du feedback",
        "source du retour",
        "source",
    ],

    "attentes_formation": [
        "quelles etaient tes attentes de la formation",
        "quelles étaient tes attentes de la formation",
        "attentes de la formation",
        "attentes concernant la formation",
        "attentes",
    ],

    "attentes_remplies": [
        "tes attentes ont elles ete remplies",
        "tes attentes ont-elles été remplies",
        "vos attentes ont elles ete remplies",
        "vos attentes ont-elles été remplies",
        "attentes remplies",
        "attentes_remplies",
    ],

    "besoin_cours_theorique": [
        "besoin de cours theorique",
        "besoin de cours théorique",
        "cours theorique",
        "cours théorique",
    ],

    "points_amelioration": [
        "quels sont les points a ameliorer",
        "quels sont les points à améliorer",
        "points a ameliorer",
        "points à améliorer",
        "axes d amelioration",
        "axes d'amélioration",
        "suggestions d amelioration",
        "suggestions d'amélioration",
        "suggestions",
    ],

    "avis_activites_vendredi": [
        "avis sur les activites du vendredi",
        "avis sur les activités du vendredi",
        "activites du vendredi",
        "activités du vendredi",
        "vendredi",
    ],

    "regroupement_niveaux": [
        "regroupement des niveaux",
        "regroupement de niveaux",
        "regroupement",
    ],

    "commentaire_libre": [
        "commentaire libre",
        "commentaire general",
        "commentaire général",
        "remarque",
        "commentaire",
    ],

    "texte_a_analyser_ia": [
        "texte a analyser ia",
        "texte à analyser ia",
        "texte ia",
        "analyse ia",
    ],

    "langue": [
        "langue",
    ],

    "prenom": [
        "prenom",
        "prénom",
        "first name",
    ],

    "nom": [
        "nom de famille",
        "ton nom de famille",
        "votre nom de famille",
        "nom",
    ],
}


# Champs dont les alias génériques sont volontairement interdits.
# Par exemple, "coach" seul ne doit pas permettre de reconnaître
# une question comme "satisfaction concernant le coaching".
ALIASES_GENERIQUES_INTERDITS = {
    "coach": {"coach"},
}


def mapper_colonnes_automatiquement(
    colonnes: list[str],
) -> dict[str, str | None]:
    """
    Associe chaque colonne Excel à un champ métier.

    La correspondance se fait en deux passes :
    1. correspondance exacte ;
    2. recherche d'un alias contenu dans le nom de colonne.

    Le match le plus spécifique (le plus long) est conservé.
    """

    resultat: dict[str, str | None] = {}

    # ---------------------------------------------------------
    # PASSAGE 1 : correspondance exacte
    # ---------------------------------------------------------
    for colonne in colonnes:
        col_norm = normaliser(colonne)

        meilleur_champ: str | None = None
        meilleure_longueur = 0

        for champ, mots_cles in ALIASES.items():
            for mot in mots_cles:
                mot_norm = normaliser(mot)

                if not mot_norm:
                    continue

                # Évite les alias génériques dangereux.
                if mot_norm in ALIASES_GENERIQUES_INTERDITS.get(
                    champ,
                    set(),
                ):
                    continue

                if col_norm == mot_norm:
                    if len(mot_norm) > meilleure_longueur:
                        meilleur_champ = champ
                        meilleure_longueur = len(mot_norm)

        if meilleur_champ:
            resultat[colonne] = meilleur_champ

    # ---------------------------------------------------------
    # PASSAGE 2 : correspondance partielle
    # ---------------------------------------------------------
    for colonne in colonnes:
        if colonne in resultat:
            continue

        col_norm = normaliser(colonne)

        meilleur_champ: str | None = None
        meilleure_longueur = 0

        for champ, mots_cles in ALIASES.items():
            for mot in mots_cles:
                mot_norm = normaliser(mot)

                if not mot_norm:
                    continue

                # Alias générique interdit.
                if mot_norm in ALIASES_GENERIQUES_INTERDITS.get(
                    champ,
                    set(),
                ):
                    continue

                # Pour éviter des correspondances trop faibles,
                # on demande au minimum 4 caractères.
                if len(mot_norm) < 4:
                    continue

                if mot_norm in col_norm:
                    if len(mot_norm) > meilleure_longueur:
                        meilleur_champ = champ
                        meilleure_longueur = len(mot_norm)

        resultat[colonne] = meilleur_champ

    return resultat


# -------------------------------------------------------------
# SATISFACTION
# -------------------------------------------------------------

SATISFACTION_SCALE: dict[str, int] = {
    "tres satisfait": 10,
    "satisfait": 8,
    "peu satisfait": 5,
    "insatisfait": 2,

    # Variantes fréquentes dans les formulaires.
    "tres bonne": 10,
    "tres bon": 10,
    "excellente": 10,
    "excellent": 10,
    "bonne": 8,
    "bon": 8,
    "moyenne": 5,
    "moyen": 5,
    "mauvaise": 2,
    "mauvais": 2,
    "tres mauvaise": 2,
    "tres mauvais": 2,
}


def score_depuis_qualitatif(
    valeur,
) -> int | None:
    """
    Convertit une satisfaction qualitative en score /10.
    """

    if not isinstance(valeur, str) or not valeur.strip():
        return None

    cle = normaliser(valeur)

    return SATISFACTION_SCALE.get(cle)


# -------------------------------------------------------------
# EXTRACTION
# -------------------------------------------------------------

def extraire_valeur(
    ligne: dict,
    mapping: dict[str, str | None],
    champ_cible: str,
):
    """
    Récupère la valeur correspondant à un champ cible.
    """

    for colonne, champ in mapping.items():

        if champ != champ_cible:
            continue

        v = ligne.get(colonne)

        if v is None:
            return None

        if isinstance(v, float) and pd.isna(v):
            return None

        if isinstance(v, str) and not v.strip():
            return None

        return v

    return None


# -------------------------------------------------------------
# TRANSFORMATION
# -------------------------------------------------------------

def transformer_ligne(
    ligne: dict,
    mapping: dict[str, str | None],
    index: int,
    nom_fichier: str,
) -> dict:
    """
    Convertit une ligne brute Excel/CSV vers le modèle Avis.
    """

    date_avis_brute = extraire_valeur(
        ligne,
        mapping,
        "date_avis",
    )

    date_avis = None
    annee = None
    mois = None

    if date_avis_brute is not None:
        try:
            d = pd.to_datetime(date_avis_brute)

            date_avis = d.to_pydatetime()
            annee = d.year
            mois = d.month

        except Exception:
            pass

    # ---------------------------------------------------------
    # Satisfaction
    # ---------------------------------------------------------

    satisfaction_qualitative = extraire_valeur(
        ligne,
        mapping,
        "satisfaction_qualitative",
    )

    satisfaction_qualitative_str = (
        str(satisfaction_qualitative)
        if satisfaction_qualitative is not None
        else None
    )

    satisfaction_score_10 = score_depuis_qualitatif(
        satisfaction_qualitative_str
    )

    # ---------------------------------------------------------
    # Autres valeurs
    # ---------------------------------------------------------

    campus = extraire_valeur(
        ligne,
        mapping,
        "campus",
    )

    promotion = extraire_valeur(
        ligne,
        mapping,
        "promotion",
    )

    formation = extraire_valeur(
        ligne,
        mapping,
        "formation",
    )

    coach = extraire_valeur(
        ligne,
        mapping,
        "coach",
    )

    return {
        "feedback_id": (
            f"{nom_fichier}-{index + 1:04d}"
        ),

        "date_avis": date_avis,
        "annee": annee,
        "mois": mois,

        "campus": (
            str(campus)
            if campus is not None
            else None
        ),

        "promotion": (
            str(promotion)
            if promotion is not None
            else None
        ),

        "formation": (
            str(formation)
            if formation is not None
            else None
        ),

        "coach": (
            str(coach)
            if coach is not None
            else None
        ),

        "satisfaction_qualitative": (
            satisfaction_qualitative_str
        ),

        "satisfaction_score_10": (
            satisfaction_score_10
        ),

        "frequence_feedback": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "frequence_feedback",
            )
        ),

        "source_feedback": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "source_feedback",
            )
        ),

        "attentes_formation": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "attentes_formation",
            )
        ),

        "attentes_remplies": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "attentes_remplies",
            )
        ),

        "besoin_cours_theorique": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "besoin_cours_theorique",
            )
        ),

        "points_amelioration": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "points_amelioration",
            )
        ),

        "avis_activites_vendredi": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "avis_activites_vendredi",
            )
        ),

        "regroupement_niveaux": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "regroupement_niveaux",
            )
        ),

        "commentaire_libre": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "commentaire_libre",
            )
        ),

        "texte_a_analyser_ia": _str_val(
            extraire_valeur(
                ligne,
                mapping,
                "texte_a_analyser_ia",
            )
        ),

        "langue": (
            _str_val(
                extraire_valeur(
                    ligne,
                    mapping,
                    "langue",
                )
            )
            or "Français"
        ),

        "source_fichier": nom_fichier,
    }


def _str_val(valeur) -> str | None:
    """
    Convertit proprement une valeur en chaîne.
    """

    if valeur is None:
        return None

    if isinstance(valeur, float) and pd.isna(valeur):
        return None

    texte = str(valeur).strip()

    return texte if texte else None


# -------------------------------------------------------------
# THÉMATIQUES
# -------------------------------------------------------------

TOPIC_RULES: list[tuple[str, str]] = [
    (
        "plateforme",
        r"platefor|plateform|platform|connexion|login|compte|site",
    ),
    (
        "technique",
        r"wifi|bug|technique|ordinateur|machine|réseau|reseau|panne|électric|electric",
    ),
    (
        "coach",
        r"coach|formateur|encadr|prof",
    ),
    (
        "planning",
        r"rythme|horaire|planning|retard|temps|durée|duree|vendredi",
    ),
    (
        "projets",
        r"projet|exercice|pratique|tp\b",
    ),
    (
        "administration",
        r"administra|inscription|paiement|frais|attestation|certificat",
    ),
    (
        "pedagogie",
        r"cours|théori|theori|contenu|apprentissage|module|niveau|pédagog|pedagog",
    ),
]


def deduire_thematique(
    *textes: str | None,
) -> str:
    """
    Déduit la thématique à partir des textes disponibles.
    """

    texte_complet = " ".join(
        str(t)
        for t in textes
        if t
    ) or ""

    for cle, motif in TOPIC_RULES:

        if re.search(
            motif,
            texte_complet,
            re.IGNORECASE,
        ):
            return cle

    return "pedagogie"

