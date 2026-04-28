"""Evaluation route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_eval_route_runs_mock_dataset(client: TestClient) -> None:
    response = client.post("/v1/eval/run")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["task_id"]
    assert payload["artifact_paths"]["result_json_path"].endswith(".json")
