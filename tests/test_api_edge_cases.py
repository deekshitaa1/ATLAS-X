from fastapi.testclient import TestClient

from atlas.api import create_app


def test_deleted_key_stays_deleted_after_restart(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.put("/kv/restart-delete", json={"value": "data"})
        assert client.delete("/kv/restart-delete").status_code == 200

    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/kv/restart-delete").status_code == 404


def test_empty_prefix_scan_returns_all_records(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        for key, value in [("a", 1), ("b", 2), ("c", 3)]:
            client.put(f"/kv/{key}", json={"value": value})

        response = client.get("/scan")
        assert response.status_code == 200
        assert response.json() == {"a": 1, "b": 2, "c": 3}


def test_special_character_key_round_trip(tmp_path):
    key = "user:123@example.com"

    with TestClient(create_app(tmp_path)) as client:
        assert client.put(f"/kv/{key}", json={"value": "ATLAS"}).status_code == 200
        response = client.get(f"/kv/{key}")
        assert response.status_code == 200
        assert response.json()["value"] == "ATLAS"


def test_non_finite_number_is_rejected(tmp_path):
    with TestClient(create_app(tmp_path), raise_server_exceptions=False) as client:
        response = client.put(
            "/kv/non-finite",
            content=b'{"value": NaN}',
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422
