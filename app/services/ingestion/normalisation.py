import re
import unicodedata

from app.services.ingestion.base import DonneeIngestion


def normaliser_texte(texte: str | None) -> str:
    """
    Nettoie un texte avant son passage dans le pipeline IA.

    Cette étape ne fait PAS d'analyse de sentiment.
    Elle prépare simplement le texte.
    """

    if texte is None:
        return ""

    texte = str(texte)

    # Suppression des espaces inutiles
    texte = re.sub(r"\s+", " ", texte)

    # Suppression des espaces au début et à la fin
    texte = texte.strip()

    return texte


def normaliser_identifiant(valeur: str | None) -> str | None:
    """
    Normalise un identifiant provenant d'une source externe.
    """

    if not valeur:
        return None

    valeur = str(valeur).strip()

    return valeur or None


def normaliser_donnee(donnee: DonneeIngestion) -> DonneeIngestion:
    """
    Applique les règles de normalisation communes à toutes les sources.
    """

    donnee.texte = normaliser_texte(donnee.texte)

    donnee.source_id = normaliser_identifiant(
        donnee.source_id
    ) or ""

    donnee.auteur_nom = normaliser_identifiant(
        donnee.auteur_nom
    )

    donnee.auteur_prenom = normaliser_identifiant(
        donnee.auteur_prenom
    )

    donnee.url_source = normaliser_identifiant(
        donnee.url_source
    )

    if donnee.metadata is None:
        donnee.metadata = {}

    return donnee


def supprimer_accents(texte: str) -> str:
    """
    Utilitaire pour les comparaisons de texte.

    Exemple :
        "Pédagogie" -> "Pedagogie"
    """

    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texte)
        if unicodedata.category(caractere) != "Mn"
    )