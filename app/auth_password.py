import bcrypt


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Hash un mot de passe en clair avec bcrypt. À utiliser uniquement à la
    création d'un compte (aucune auto-inscription : les comptes sont créés
    manuellement par un super_admin, cf. note du DG)."""
    sel = bcrypt.gensalt()
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe_clair: str, hash_stocke: str) -> bool:
    """Compare un mot de passe en clair (saisi au login) avec le hash stocké en base."""
    return bcrypt.checkpw(mot_de_passe_clair.encode("utf-8"), hash_stocke.encode("utf-8"))
