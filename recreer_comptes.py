from app.database import SessionLocal
from app.models import Utilisateur
from app.auth_password import hacher_mot_de_passe


COMPTES = [
    {
        "email": "superadmin@bakeli.tech",
        "mot_de_passe": "SuperAdmin123!",
        "nom_complet": "Super Administrateur",
        "role": "super_admin",
    },
    {
        "email": "admin@bakeli.tech",
        "mot_de_passe": "Admin123!",
        "nom_complet": "Administrateur Bakeli",
        "role": "admin",
    },
    {
        "email": "collaborateur@bakeli.tech",
        "mot_de_passe": "Collaborateur123!",
        "nom_complet": "Collaborateur Bakeli",
        "role": "collaborator",
    },
]


def creer_comptes():
    db = SessionLocal()

    try:
        for compte in COMPTES:
            utilisateur_existant = (
                db.query(Utilisateur)
                .filter(Utilisateur.email == compte["email"])
                .first()
            )

            if utilisateur_existant:
                print(
                    f"⚠️ Le compte {compte['email']} existe déjà."
                )
                continue

            utilisateur = Utilisateur(
                email=compte["email"],
                mot_de_passe_hash=hacher_mot_de_passe(
                    compte["mot_de_passe"]
                ),
                nom_complet=compte["nom_complet"],
                role=compte["role"],
                actif=True,
            )

            db.add(utilisateur)

            print(
                f"✅ Compte créé : "
                f"{compte['email']} ({compte['role']})"
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    creer_comptes()