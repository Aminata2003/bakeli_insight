from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    resultat = conn.execute(text("SELECT version();"))
    print("Connexion réussie !")
    print(resultat.fetchone())