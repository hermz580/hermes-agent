"""Behavioral tests for the MMQP Cathedral Memory provider."""

import json

import pytest

from plugins.memory.mmqp import MMQPMemoryProvider, MMQP_SCHEMA
from plugins.memory.config_schema import get_provider_config_schema


@pytest.fixture
def provider(tmp_path):
    p = MMQPMemoryProvider(
        config={
            "db_path": str(tmp_path / "mmqp.db"),
            "prefetch_limit": 6,
        }
    )
    p.initialize("session-root", hermes_home=str(tmp_path))
    try:
        yield p
    finally:
        p.shutdown()


def _remember(provider, content="Do not merge until verified"):
    payload = json.loads(
        provider.handle_tool_call(
            "mmqp_memory",
            {
                "action": "remember",
                "content": content,
                "state": "candidate",
                "category": "project",
                "confidence": 0.9,
                "semantic_importance": 0.95,
            },
        )
    )
    return payload["memory_id"]


def test_model_tool_surface_cannot_promote_to_canon():
    actions = MMQP_SCHEMA["parameters"]["properties"]["action"]["enum"]
    assert "promote" not in actions


def test_turn_is_preserved_as_raw_episode(provider):
    provider.sync_turn(
        "Keep the source history intact.",
        "I will preserve the lineage.",
        session_id="session-root",
        messages=[{"role": "user", "content": "Keep the source history intact."}],
    )
    row = provider._conn.execute("SELECT * FROM episodes").fetchone()
    assert row is not None
    assert row["session_id"] == "session-root"
    assert row["modality"] == "text"
    assert row["user_content"] == "Keep the source history intact."


def test_new_model_memory_starts_as_candidate(provider):
    memory_id = _remember(provider)
    row = provider._conn.execute(
        "SELECT state FROM memories WHERE memory_id = ?", (memory_id,)
    ).fetchone()
    assert row["state"] == "candidate"


def test_host_authorized_promotion_is_audited(provider):
    memory_id = _remember(provider)

    with pytest.raises(ValueError, match="verified authorized_by"):
        provider.promote_authorized(
            memory_id,
            authorized_by="",
            authorization_source="",
        )

    result = provider.promote_authorized(
        memory_id,
        authorized_by="harpstar",
        authorization_source="operator-test",
        reason="explicit approval",
    )
    assert result["state"] == "canonical"

    event = provider._conn.execute(
        "SELECT * FROM promotion_events WHERE memory_id = ?", (memory_id,)
    ).fetchone()
    assert event is not None
    assert event["authorized_by"] == "harpstar"
    assert event["authorization_source"] == "operator-test"


def test_correction_preserves_version_lineage_and_reopens_dispute(provider):
    memory_id = _remember(provider, "Merge immediately.")
    provider.promote_authorized(
        memory_id,
        authorized_by="harpstar",
        authorization_source="operator-test",
    )

    result = json.loads(
        provider.handle_tool_call(
            "mmqp_memory",
            {
                "action": "correct",
                "memory_id": memory_id,
                "content": "Do not merge until verified.",
                "confidence": 1.0,
                "reason": "explicit user correction",
            },
        )
    )
    assert result["state"] == "disputed"
    assert result["requires_promotion"] is True

    versions = provider._conn.execute(
        "SELECT * FROM memory_versions WHERE memory_id = ? ORDER BY version_no",
        (memory_id,),
    ).fetchall()
    assert [row["version_no"] for row in versions] == [1, 2]
    assert versions[0]["content"] == "Merge immediately."
    assert versions[1]["content"] == "Do not merge until verified."

    link = provider._conn.execute(
        "SELECT relation FROM provenance_links WHERE relation='superseded_by'"
    ).fetchone()
    assert link is not None


def test_voice_observation_remains_a_signal_not_a_memory_claim(provider):
    provider.sync_turn("spoken transcript", "response", session_id="voice-session")
    episode = provider._conn.execute(
        "SELECT episode_id FROM episodes WHERE session_id='voice-session'"
    ).fetchone()

    result = json.loads(
        provider.handle_tool_call(
            "mmqp_memory",
            {
                "action": "signal",
                "episode_id": episode["episode_id"],
                "channel": "voice",
                "signal_name": "speech_rate_wpm",
                "value_num": 174.0,
                "start_ms": 0,
                "end_ms": 4200,
                "confidence": 0.98,
                "provenance": "observed",
            },
        )
    )
    signal = provider._conn.execute(
        "SELECT * FROM signals WHERE signal_id = ?", (result["signal_id"],)
    ).fetchone()
    assert signal["channel"] == "voice"
    assert signal["signal_name"] == "speech_rate_wpm"
    assert signal["provenance"] == "observed"
    assert provider._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0


def test_council_annotation_does_not_change_memory_state(provider):
    memory_id = _remember(provider)
    result = json.loads(
        provider.handle_tool_call(
            "mmqp_memory",
            {
                "action": "annotate",
                "memory_id": memory_id,
                "persona": "Curio",
                "content": "Treat as a release gate.",
                "confidence": 0.88,
            },
        )
    )
    assert result["annotation_id"].startswith("ann_")
    state = provider._conn.execute(
        "SELECT state FROM memories WHERE memory_id = ?", (memory_id,)
    ).fetchone()["state"]
    assert state == "candidate"


def test_braced_hermes_home_path_expands(tmp_path):
    p = MMQPMemoryProvider(config={"db_path": "${HERMES_HOME}/nested/mmqp.db"})
    try:
        p.initialize("session", hermes_home=str(tmp_path))
        p.sync_turn("hello", "world")
        assert (tmp_path / "nested" / "mmqp.db").exists()
    finally:
        p.shutdown()


def test_desktop_config_schema_is_declared():
    schema = get_provider_config_schema("mmqp")
    assert schema is not None
    assert schema.label == "MMQP Cathedral Memory"
    assert {field.key for field in schema.fields} == {"db_path", "prefetch_limit"}
