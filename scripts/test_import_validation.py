from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_apercu_rejects_unsupported_file_type():
    response = client.post(
        "/imports/apercu",
        files={"fichier": ("notes.txt", b"bonjour", "text/plain")},
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"


def test_upload_rejects_empty_csv():
    response = client.post(
        "/imports/upload",
        files={"fichier": ("empty.csv", b"", "text/csv")},
        headers={"X-API-Key": "admin-secret"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "bad_request"
