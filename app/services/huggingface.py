import httpx

from app.config import settings


async def analyze_sentiment(text: str) -> str | None:
    """
    Analyse le sentiment d'un texte avec Hugging Face.

    Retourne :
    - "positif"
    - "negatif"
    - "neutre"
    - None si l'IA est indisponible ou si l'analyse échoue.
    """

    if not settings.hf_api_token:
        return None

    if not text or not text.strip():
        return None

    headers = {
        "Authorization": f"Bearer {settings.hf_api_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": text.strip()
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.hf_inference_url,
                headers=headers,
                json=payload,
            )

        if response.status_code != 200:
            print(
                f"Hugging Face erreur {response.status_code}: "
                f"{response.text}"
            )
            return None

        result = response.json()

        # Exemple de réponse :
        # [[
        #   {"label": "positive", "score": 0.95},
        #   {"label": "neutral", "score": 0.03},
        #   {"label": "negative", "score": 0.02}
        # ]]

        if not result or not isinstance(result, list):
            return None

        predictions = result[0]

        if not isinstance(predictions, list) or not predictions:
            return None

        best_prediction = max(
            predictions,
            key=lambda item: item.get("score", 0)
        )

        label = str(best_prediction.get("label", "")).lower()

        if label == "positive":
            return "positif"

        if label == "negative":
            return "negatif"

        if label == "neutral":
            return "neutre"

        return None

    except Exception as e:
        print(f"Erreur Hugging Face : {e}")
        return None