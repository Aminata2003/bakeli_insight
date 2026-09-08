import asyncio

from app.services.huggingface import analyze_sentiment


async def main():
    textes = [
        "La formation était excellente, j'ai beaucoup appris.",
        "La formation était moyenne, il y a plusieurs choses à améliorer.",
        "La formation était très mauvaise et je suis déçu.",
    ]

    for texte in textes:
        resultat = await analyze_sentiment(texte)

        print("\nTexte :", texte)
        print("Sentiment :", resultat)


if __name__ == "__main__":
    asyncio.run(main())