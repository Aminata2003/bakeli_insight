from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_public():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_secure_route_requires_api_key():
    response = client.get('/secure-status')
    assert response.status_code == 401
    payload = response.json()
    assert 'error' in payload
    assert payload['error']['code'] == 'unauthorized'
    assert 'message' in payload['error']


def test_secure_route_accepts_valid_api_key():
    response = client.get('/secure-status', headers={'X-API-Key': 'admin-secret'})
    assert response.status_code == 200
    assert response.json()['role'] == 'admin'
