"""API integration tests."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_task_creation_and_result_chain(client: TestClient, sample_event_payload: dict) -> None:
    user_requirement = "请用值班人员能直接执行的方式评估风险，并说明是否需要人工复核。"
    response = client.post(
        "/v1/tasks",
        data={
            "task_type": "collision_warning",
            "user_requirement": user_requirement,
            "inline_payload": json.dumps(sample_event_payload),
            "options_json": json.dumps({"enable_external_context": False}),
        },
    )

    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]

    detail = client.get(f"/v1/tasks/{task_id}")
    result = client.get(f"/v1/tasks/{task_id}/result")
    report = client.get(f"/v1/tasks/{task_id}/report")
    trace = client.get(f"/v1/tasks/{task_id}/trace")
    llm_calls = client.get(f"/v1/tasks/{task_id}/llm-calls")
    chat = client.get(f"/v1/tasks/{task_id}/chat")

    assert detail.status_code == 200
    assert result.status_code == 200
    assert report.status_code == 200
    assert trace.status_code == 200
    assert llm_calls.status_code == 200
    assert chat.status_code == 200
    assert detail.json()["data"]["user_requirement"] == user_requirement
    assert result.json()["data"]["events"]
    assert result.json()["data"]["user_requirement"] == user_requirement
    markdown = report.json()["data"]["markdown"]
    html = report.json()["data"]["html"]
    assert all(section in markdown for section in ["## 原因", "## 判据", "## 结论", "## 建议"])
    assert "## 不确定性" not in markdown
    assert "<pre>" not in html
    assert "<h2>原因</h2>" in html
    assert trace.json()["data"]["steps"]
    assert any("\u4e00" <= ch <= "\u9fff" for ch in result.json()["data"]["events"][0]["action_recommendation"])
    assert llm_calls.json()["data"][0]["prompt_text"].startswith("[system]")
    assert user_requirement in llm_calls.json()["data"][0]["prompt_text"]
    assert any(item["step_name"] == "llm_final_report" for item in llm_calls.json()["data"])
    assert chat.json()["data"][0]["role"] == "user"
    assert chat.json()["data"][0]["content"] == user_requirement


def test_task_chat_follow_up_is_persisted_and_audited(client: TestClient, sample_event_payload: dict) -> None:
    response = client.post(
        "/v1/tasks",
        data={
            "task_type": "collision_warning",
            "user_requirement": "先完成风险评估。",
            "inline_payload": json.dumps(sample_event_payload),
            "options_json": json.dumps({"enable_external_context": False}),
        },
    )
    task_id = response.json()["data"]["task_id"]

    reply = client.post(
        f"/v1/tasks/{task_id}/chat",
        json={"content": "为什么需要人工复核？证据来自哪里？"},
    )
    chat = client.get(f"/v1/tasks/{task_id}/chat")
    llm_calls = client.get(f"/v1/tasks/{task_id}/llm-calls")

    assert reply.status_code == 200
    assert reply.json()["data"]["role"] == "assistant"
    assert "任务报告" in reply.json()["data"]["content"]
    assert [item["role"] for item in chat.json()["data"]] == ["user", "user", "assistant"]
    assert any(item["step_name"] == "chat_reply" for item in llm_calls.json()["data"])
    chat_call = [item for item in llm_calls.json()["data"] if item["step_name"] == "chat_reply"][0]
    assert "为什么需要人工复核" in chat_call["prompt_text"]
    assert chat_call["parsed_output_json"]["prompt_name"] == "chat"


def test_task_chat_stream_is_persisted_and_audited(client: TestClient, sample_event_payload: dict) -> None:
    response = client.post(
        "/v1/tasks",
        data={
            "task_type": "collision_warning",
            "user_requirement": "生成一份最终报告。",
            "inline_payload": json.dumps(sample_event_payload),
            "options_json": json.dumps({"enable_external_context": False}),
        },
    )
    task_id = response.json()["data"]["task_id"]

    stream = client.post(
        f"/v1/tasks/{task_id}/chat/stream",
        json={"content": "请流式说明证据来自哪里。"},
    )
    chat = client.get(f"/v1/tasks/{task_id}/chat")
    llm_calls = client.get(f"/v1/tasks/{task_id}/llm-calls")

    assert stream.status_code == 200
    assert "任务报告" in stream.text
    assert [item["role"] for item in chat.json()["data"]][-2:] == ["user", "assistant"]
    assert any(
        item["step_name"] == "chat_reply" and item["parsed_output_json"].get("streamed")
        for item in llm_calls.json()["data"]
    )


def test_task_chat_stream_form_uploads_file_and_reruns_task(client: TestClient, sample_event_payload: dict) -> None:
    response = client.post(
        "/v1/tasks",
        data={
            "task_type": "collision_warning",
            "user_requirement": "先分析初始 CDM。",
            "inline_payload": json.dumps(sample_event_payload),
            "options_json": json.dumps({"enable_external_context": False}),
        },
    )
    task_id = response.json()["data"]["task_id"]

    project_root = Path(__file__).resolve().parents[2]
    v2 = (project_root / "data" / "mock" / "cdm_multiversion_v2.json").read_text(encoding="utf-8")
    stream = client.post(
        f"/v1/tasks/{task_id}/chat/stream-form",
        data={"content": "我补充了新版 CDM，请重新生成报告。"},
        files=[("files", ("cdm_v2.json", v2, "application/json"))],
    )
    detail = client.get(f"/v1/tasks/{task_id}")
    report = client.get(f"/v1/tasks/{task_id}/report")
    chat = client.get(f"/v1/tasks/{task_id}/chat")

    assert stream.status_code == 200
    assert "重新解析" in stream.text
    assert len(detail.json()["data"]["inputs"]) == 2
    assert "cdm_v2.json" in json.dumps(chat.json()["data"], ensure_ascii=False)
    assert "## 原因" in report.json()["data"]["markdown"]


def test_task_creation_with_multi_version_files_aggregates(client: TestClient) -> None:
    project_root = Path(__file__).resolve().parents[2]
    v1 = (project_root / "data" / "mock" / "cdm_multiversion_v1.json").read_text(encoding="utf-8")
    v2 = (project_root / "data" / "mock" / "cdm_multiversion_v2.json").read_text(encoding="utf-8")
    constraints = (project_root / "data" / "mock" / "mission_constraints.json").read_text(encoding="utf-8")

    response = client.post(
        "/v1/tasks",
        data={
            "task_type": "collision_warning",
            "user_requirement": "请比较多版本消息，使用最新版本给出处置建议。",
        },
        files=[
            ("files", ("v1.json", v1, "application/json")),
            ("files", ("v2.json", v2, "application/json")),
            ("files", ("mission_constraints.json", constraints, "application/json")),
        ],
    )

    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]
    result = client.get(f"/v1/tasks/{task_id}/result")
    chat = client.get(f"/v1/tasks/{task_id}/chat")

    assert result.status_code == 200
    payload = result.json()["data"]
    assert len(payload["events"]) == 1
    assert payload["events"][0]["risk_level"] == "unknown"
    assert payload["events"][0]["needs_manual_review"] is True
    assert chat.json()["data"][0]["attachments"]
