from fastapi.testclient import TestClient

from atlas.api import create_app


def test_health_endpoint(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_put_and_get(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        put = client.put("/kv/name", json={"value": "ATLAS-X"})
        assert put.status_code == 200

        get = client.get("/kv/name")
        assert get.status_code == 200
        assert get.json()["value"] == "ATLAS-X"


def test_missing_key_returns_404(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/kv/missing").status_code == 404


def test_delete_endpoint(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.put("/kv/name", json={"value": "Atlas"})
        response = client.delete("/kv/name")
        assert response.status_code == 200
        assert client.get("/kv/name").status_code == 404


def test_scan_prefix_endpoint(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.put("/kv/user:1", json={"value": "A"})
        client.put("/kv/user:2", json={"value": "B"})
        client.put("/kv/order:1", json={"value": "C"})

        response = client.get("/scan", params={"prefix": "user:"})
        assert response.status_code == 200
        assert response.json() == {"user:1": "A", "user:2": "B"}


def test_api_data_survives_restart(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.put("/kv/persistent", json={"value": 123})

    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/kv/persistent")
        assert response.json()["value"] == 123


def test_api_stores_none(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.put("/kv/nullable", json={"value": None})
        response = client.get("/kv/nullable")
        assert response.status_code == 200
        assert response.json()["value"] is None

def test_concurrent_api_writes(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    with TestClient(create_app(tmp_path)) as client:
        def write_value(number):
            response = client.put(
                f"/kv/item:{number}",
                json={"value": number},
            )
            assert response.status_code == 200

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(write_value, range(50)))

        response = client.get("/scan", params={"prefix": "item:"})
        assert response.status_code == 200
        assert len(response.json()) == 50
        assert response.json()["item:25"] == 25


def test_delete_missing_key_returns_404(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.delete("/kv/missing")
        assert response.status_code == 404


def test_api_validation_error_returns_422(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.put("/kv/name", json={})
        assert response.status_code == 422
