from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sample_generation_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    response = client.post("/generate/sample")

    assert response.status_code == 200
    payload = response.json()
    assert payload["slide_count"] == 15
    assert payload["selected_bom_profile"] == "generic_json"
    assert payload["blocking_errors"] == []

    ppt_path = Path(payload["ppt_path"])
    report_data_path = Path(payload["report_data_path"])
    assert ppt_path.exists()
    assert ppt_path.suffix == ".pptx"
    assert report_data_path.exists()
    assert report_data_path.suffix == ".json"
    assert (ppt_path.parent / "assets" / ppt_path.stem).exists()
