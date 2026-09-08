from app.services.ingestion.base import ConnecteurIngestion, DonneeIngestion


class TypeformConnecteur(ConnecteurIngestion):
    """
    Connecteur Typeform.

    Alimenté via l'API Typeform (récupération périodique),
    conformément au cahier des charges.
    """

    plateforme_code = "typeform"

    def __init__(self, donnees: list[dict] | None = None):
        self.donnees = donnees or []

    async def recuperer(self) -> list[DonneeIngestion]:
        resultat = []

        for ligne in self.donnees:
            texte = (
                ligne.get("texte")
                or ligne.get("commentaire_libre")
                or ligne.get("message")
                or ligne.get("feedback")
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


def _extraire_champs_reponse(reponse: dict) -> dict:
    """
    Transforme une réponse Typeform (un item renvoyé par l'API)
    en un dictionnaire {titre_de_la_question: réponse}.
    """
    champs: dict = {
        "source_id": reponse.get("token"),
    }

    for answer in reponse.get("answers", []):
        titre = answer.get("field", {}).get("title", "")
        type_reponse = answer.get("type")

        if type_reponse in ("text", "long_text"):
            valeur = answer.get(type_reponse)
        elif type_reponse == "email":
            valeur = answer.get("email")
        elif type_reponse == "choice":
            valeur = answer.get("choice", {}).get("label")
        elif type_reponse == "choices":
            valeur = ", ".join(
                answer.get("choices", {}).get("labels", [])
            )
        elif type_reponse == "phone_number":
            valeur = answer.get("phone_number")
        else:
            valeur = None

        if titre:
            champs[titre] = valeur

    champs["metadata"] = champs.copy()

    return champs


def mapper_reponses_typeform(items: list[dict]) -> list[dict]:
    """
    Applique l'extraction à toutes les réponses récupérées
    depuis l'API Typeform.
    """
    return [_extraire_champs_reponse(item) for item in items]