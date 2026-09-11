from datetime import datetime

from app.mapping import normaliser
from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class GoogleFormsConnecteur(ConnecteurIngestion):
    """
    Connecteur Google Forms.

    Google Forms ne fournit pas directement un endpoint webhook
    universel pour récupérer les réponses. L'intégration sera donc
    branchée sur la source de réponses configurée par Bakeli
    (notamment Google Sheets/API ou export).

    Cette classe définit déjà le contrat utilisé par le pipeline.
    """

    plateforme_code = "google_forms"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for ligne in self.donnees:
            texte = (
                ligne.get("texte")
                or ligne.get("commentaire_libre")
                or ligne.get("points_amelioration")
                or ligne.get("attentes_formation")
                or ""
            )

            source_id = str(
                ligne.get("source_id")
                or ligne.get("id")
                or ""
            )

            resultat.append(
                DonneeIngestion(
                    plateforme_code=self.plateforme_code,
                    source_id=source_id,
                    texte=str(texte),
                    date_source=_parser_horodateur(source_id),
                    auteur_nom=ligne.get("nom"),
                    auteur_prenom=ligne.get("prenom"),
                    url_source=ligne.get("url"),
                    metadata=ligne,
                )
            )

        return resultat


def _parser_horodateur(valeur: str) -> datetime | None:
    """
    Convertit l'Horodateur d'un Google Form (format
    "31/07/2026 12:39:58") en datetime exploitable.

    Sans cette date, l'avis retombe sur une date par défaut très
    ancienne côté frontend, et disparaît silencieusement de tous
    les filtres de période (Aujourd'hui/Semaine/Mois/Année).
    """
    if not valeur:
        return None

    try:
        return datetime.strptime(valeur, "%d/%m/%Y %H:%M:%S")
    except ValueError:
        return None


def _trouver_cle_colonne(ligne: dict, mots_cles: list[str]) -> str | None:
    """
    Trouve la clé (en-tête d'origine) d'une ligne dont le nom,
    une fois normalisé (minuscules, sans accents), commence par
    l'un des mots-clés donnés.

    Plus robuste qu'une comparaison de chaîne exacte : insensible
    aux accents, à la casse, et aux petites variations de
    ponctuation/espaces qu'on ne maîtrise pas sur un Google Sheet
    externe (apostrophe courbe vs droite, espace en trop, etc.).
    """
    for cle in ligne.keys():
        cle_normalisee = normaliser(cle)
        for mot in mots_cles:
            if cle_normalisee.startswith(normaliser(mot)):
                return cle
    return None


def mapper_reponses_formulaire(lignes_brutes: list[dict]) -> list[dict]:
    """
    Convertit les lignes brutes du Google Sheet (en-têtes en
    français, propres à ce formulaire) vers le format générique
    attendu par GoogleFormsConnecteur.

    Les colonnes sont retrouvées par mot-clé plutôt que par
    correspondance exacte, pour ne pas dépendre d'un en-tête
    recopié caractère pour caractère.
    """
    lignes_mappees = []

    for ligne in lignes_brutes:
        cle_horodateur = _trouver_cle_colonne(ligne, ["horodateur"])
        cle_prenom = _trouver_cle_colonne(ligne, ["prenom"])
        cle_nom = _trouver_cle_colonne(ligne, ["nom"])
        cle_remarques = _trouver_cle_colonne(ligne, ["remarques"])

        lignes_mappees.append(
            {
                "source_id": ligne.get(cle_horodateur) if cle_horodateur else None,
                "nom": ligne.get(cle_nom) if cle_nom else None,
                "prenom": ligne.get(cle_prenom) if cle_prenom else None,
                "texte": ligne.get(cle_remarques) if cle_remarques else None,
                **ligne,  # le reste (créneaux, connexion) part dans metadata
            }
        )

    return lignes_mappees