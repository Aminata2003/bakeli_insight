from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Avis, Plateforme, Thematique

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def populated_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.query(Avis).delete()
        db.query(Thematique).delete()
        db.query(Plateforme).delete()

        plateforme = Plateforme(
            code="google_forms",
            nom_affiche="Google Forms",
            categorie="canal_public",
            actif=True,
        )
        thematique = Thematique(
            cle="pedagogie",
            nom_affiche="Pédagogie",
            mots_cles_regex="cours",
        )
        db.add_all([plateforme, thematique])
        db.commit()
        db.refresh(plateforme)
        db.refresh(thematique)

        avis = Avis(
            feedback_id="TEST-001",
            date_avis=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
            annee=2025,
            mois=1,
            plateforme_id=plateforme.id,
            campus="Dakar",
            promotion="Promo A",
            formation="Data",
            coach="Coach A",
            satisfaction_qualitative="Satisfait",
            satisfaction_score_10=8,
            sentiment="positif",
            note=4,
            resume="Très bon",
            source_feedback="Google Forms",
            thematique_id=thematique.id,
            statut_moderation="nouveau",
            source_fichier="test.csv",
        )
        db.add(avis)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)


def test_lister_avis_requires_api_key(populated_db):
    response = client.get("/avis")
    assert response.status_code == 401


def test_lister_avis_returns_contract(populated_db):
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()
    response = client.get("/avis", headers={"X-API-Key": "analyst-secret"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["feedback_id"] == "TEST-001"
    assert payload["items"][0]["statut_moderation"] == "nouveau"


def test_dashboard_vue_ensemble_contract(populated_db):
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()
    response = client.get("/dashboard/vue-ensemble", headers={"X-API-Key": "analyst-secret"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["positive"] >= 0
    assert "satisfaction" in payload
