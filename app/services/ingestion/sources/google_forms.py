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
                    auteur_nom=ligne.get("nom"),
                    auteur_prenom=ligne.get("prenom"),
                    url_source=ligne.get("url"),
                    metadata=ligne,
                )
            )

        return resultat
COLONNE_HORODATEUR = "Horodateur"
COLONNE_PRENOM = "Prénom"
COLONNE_NOM = "Nom"
COLONNE_REMARQUES = (
    "Remarques ou suggestions supplémentaires concernant "
    "l'organisation des séances  ?"
)


def mapper_reponses_formulaire(lignes_brutes: list[dict]) -> list[dict]:
    """
    Convertit les lignes brutes du Google Sheet (en-têtes en
    français, propres à ce formulaire) vers le format générique
    attendu par GoogleFormsConnecteur.
    """
    lignes_mappees = []

    for ligne in lignes_brutes:
        lignes_mappees.append(
            {
                "source_id": ligne.get(COLONNE_HORODATEUR),
                "nom": ligne.get(COLONNE_NOM),
                "prenom": ligne.get(COLONNE_PRENOM),
                "texte": ligne.get(COLONNE_REMARQUES),
                **ligne,  # le reste (créneaux, connexion) part dans metadata
            }
        )

    return lignes_mappees