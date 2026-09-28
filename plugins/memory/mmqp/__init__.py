"""MMQP Cathedral Memory provider.

Phase-0 goals:
- Preserve raw episodes before interpretation.
- Keep voice/text signal channels separate from semantic content.
- Never silently promote model-derived memory to canonical truth.
- Preserve provenance, corrections, Council annotations, and lineage.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

logger = logging.getLogger(__name__)


def _load_config() -> dict:
    """Load profile-scoped MMQP configuration from $HERMES_HOME/mmqp.json."""
    try:
        from hermes_constants import get_hermes_home
        path = get_hermes_home() / "mmqp.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.debug("Failed to load MMQP config: %s", exc)
    return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _clamp(value: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


MMQP_SCHEMA = {
    "name": "mmqp_memory",
    "description": (
        "Durable, provenance-aware Cathedral memory. New model-derived memories "
        "must begin as observation or candidate. Promotion to canonical is a "
        "separate audited action and should only follow explicit user/Cipher Seat authorization. "
        "Voice/text signals remain distinct from emotional interpretation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["remember", "recall", "inspect", "correct", "annotate", "signal", "lineage"],
            },
            "content": {"type": "string"},
            "query": {"type": "string"},
            "memory_id": {"type": "string"},
            "episode_id": {"type": "string"},
            "state": {"type": "string", "enum": ["observation", "candidate"]},
            "category": {"type": "string"},
            "confidence": {"type": "number"},
            "semantic_importance": {"type": "number"},
            "emotional_salience": {"type": "number"},
            "persona": {"type": "string"},
            "reason": {"type": "string"},
            "authorized_by": {"type": "string"},
            "authorization_source": {"type": "string"},
            "channel": {"type": "string", "enum": ["text", "voice", "mixed", "system"]},
            "signal_name": {"type": "string"},
            "value_num": {"type": "number"},
            "value_text": {"type": "string"},
            "start_ms": {"type": "integer"},
            "end_ms": {"type": "integer"},
            "provenance": {"type": "string", "enum": ["explicit", "observed", "interpreted"]},
            "limit": {"type": "integer"},
        },
        "required": ["action"],
    },
}


class MMQPMemoryProvider(MemoryProvider):
    def __init__(self, config: Optional[dict] = None):
        self._config = config if config is not None else _load_config()
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._session_id = ""
        self._parent_session_id = ""

    @property
    def name(self) -> str:
        return "mmqp"

    def is_available(self) -> bool:
        return True

    def get_config_schema(self):
        from hermes_constants import display_hermes_home
        return [
            {
                "key": "db_path",
                "description": "MMQP SQLite database path",
                "default": f"{display_hermes_home()}/mmqp.db",
            },
            {
                "key": "prefetch_limit",
                "description": "Maximum memories prefetched per turn",
                "default": "6",
            },
        ]

    def initialize(self, session_id: str, **kwargs) -> None:
        hermes_home = Path(kwargs.get("hermes_home") or Path.home() / ".hermes")
        raw_path = str(self._config.get("db_path", hermes_home / "mmqp.db"))
        raw_path = raw_path.replace("$HERMES_HOME", str(hermes_home)).replace("${HERMES_HOME}", str(hermes_home))
        db_path = Path(raw_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=10.0, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        schema_path = Path(__file__).with_name("schema.sql")
        self._conn.executescript(schema_path.read_text(encoding="utf-8"))
        self._session_id = session_id
        self._parent_session_id = kwargs.get("parent_session_id", "") or ""

    def system_prompt_block(self) -> str:
        return (
            "# MMQP Cathedral Memory\n"
            "MMQP preserves raw episodes, provenance, corrections, multimodal signals, and Council annotations. "
            "Treat canonical memories as high-trust reference, candidates as proposals, and observations as source material. "
            "Never promote model-derived content to canonical without explicit authorization."
        )

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if not self._conn:
            return
        episode_id = _id("ep")
        metadata = {"message_count": len(messages or [])}
        self._conn.execute(
            """
            INSERT INTO episodes(
                episode_id, session_id, parent_session_id, modality, source_kind,
                user_content, assistant_content, metadata_json, created_at
            ) VALUES (?, ?, ?, 'text', 'chat_turn', ?, ?, ?, ?)
            """,
            (
                episode_id,
                session_id or self._session_id,
                self._parent_session_id,
                user_content or "",
                assistant_content or "",
                json.dumps(metadata),
                _now(),
            ),
        )
        self._conn.commit()

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if not self._conn or not query.strip():
            return ""
        results = self._search(query, limit=int(self._config.get("prefetch_limit", 6)))
        if not results:
            return ""
        lines = [
            f"- [{row['state']} conf={row['confidence']:.2f} id={row['memory_id']}] {row['content']}"
            for row in results
        ]
        return "## MMQP Recall\n" + "\n".join(lines)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [MMQP_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        if tool_name != "mmqp_memory":
            return tool_error(f"Unknown MMQP tool: {tool_name}")
        try:
            action = args.get("action")
            if action == "remember":
                return json.dumps(self._remember(args))
            if action == "recall":
                return json.dumps({"results": self._search(args.get("query", ""), int(args.get("limit", 10)))})
            if action == "inspect":
                return json.dumps(self._inspect(args["memory_id"]))
            if action == "correct":
                return json.dumps(self._correct(args))
            if action == "annotate":
                return json.dumps(self._annotate(args))
            if action == "signal":
                return json.dumps(self._signal(args))
            if action == "lineage":
                return json.dumps(self._lineage(args["memory_id"]))
            return tool_error(f"Unknown action: {action}")
        except KeyError as exc:
            return tool_error(f"Missing required argument: {exc}")
        except Exception as exc:
            logger.exception("MMQP tool error")
            return tool_error(str(exc))

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs,
    ) -> None:
        self._parent_session_id = parent_session_id or self._session_id
        self._session_id = new_session_id

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        if not self._conn or not self._session_id:
            return ""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM episodes WHERE session_id = ?",
            (self._session_id,),
        ).fetchone()
        count = int(row["n"]) if row else 0
        return f"MMQP lineage note: {count} raw episodes are preserved outside the compressed context."

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        if action != "add" or not content:
            return
        self._remember({
            "content": content,
            "state": "candidate",
            "category": "user_pref" if target == "user" else "general",
            "confidence": 0.8,
            "reason": "mirrored from Hermes built-in memory write",
        })

    def shutdown(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _remember(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        content = (args.get("content") or "").strip()
        if not content:
            raise ValueError("remember requires content")
        state = args.get("state", "candidate")
        if state not in {"observation", "candidate"}:
            raise ValueError("new memories may only start as observation or candidate")

        memory_id, version_id, created = _id("mem"), _id("ver"), _now()
        confidence = _clamp(args.get("confidence"), 0.5)
        semantic = _clamp(args.get("semantic_importance"), 0.5)
        emotional = _clamp(args.get("emotional_salience"), 0.0)

        self._conn.execute(
            """
            INSERT INTO memories(
                memory_id, current_version_id, state, category, semantic_importance,
                emotional_salience, confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id, version_id, state, args.get("category", "general"),
                semantic, emotional, confidence, created, created,
            ),
        )
        self._conn.execute(
            """
            INSERT INTO memory_versions(
                version_id, memory_id, version_no, content, source_episode_id,
                created_by, reason, valid_from, created_at
            ) VALUES (?, ?, 1, ?, ?, 'mmqp', ?, ?, ?)
            """,
            (
                version_id, memory_id, content, args.get("episode_id"),
                args.get("reason", ""), created, created,
            ),
        )
        if args.get("episode_id"):
            self._link("episode", args["episode_id"], "supports", "memory", memory_id)
        self._conn.commit()
        return {"memory_id": memory_id, "version_id": version_id, "state": state}

    def _search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self._conn:
            return []
        tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9_'-]{3,}", query)]
        if not tokens:
            return []
        rows = self._conn.execute(
            """
            SELECT m.*, v.content
            FROM memories m
            JOIN memory_versions v ON v.version_id = m.current_version_id
            WHERE m.state IN ('canonical','candidate','disputed')
            ORDER BY CASE m.state WHEN 'canonical' THEN 0 WHEN 'candidate' THEN 1 ELSE 2 END,
                     m.updated_at DESC
            LIMIT 250
            """
        ).fetchall()

        ranked = []
        for row in rows:
            text = row["content"].lower()
            lexical = sum(1 for t in tokens if t in text) / max(1, len(tokens))
            if lexical <= 0:
                continue
            state_bonus = {"canonical": 0.20, "candidate": 0.05, "disputed": -0.10}.get(row["state"], 0.0)
            score = (
                0.45 * lexical
                + 0.20 * float(row["semantic_importance"])
                + 0.15 * float(row["confidence"])
                + 0.10 * float(row["emotional_salience"])
                + 0.10 * float(row["correction_weight"])
                + state_bonus
            )
            item = dict(row)
            item["score"] = round(score, 4)
            ranked.append(item)

        ranked.sort(key=lambda x: x["score"], reverse=True)
        out = ranked[: max(1, min(limit, 50))]
        for item in out:
            self._conn.execute(
                """
                INSERT INTO retrieval_events(
                    retrieval_id, query, memory_id, score, session_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (_id("ret"), query, item["memory_id"], item["score"], self._session_id, _now()),
            )
        self._conn.commit()
        return out

    def _inspect(self, memory_id: str) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        memory = self._conn.execute(
            "SELECT * FROM memories WHERE memory_id = ?", (memory_id,)
        ).fetchone()
        if not memory:
            raise ValueError("memory not found")
        versions = [
            dict(r) for r in self._conn.execute(
                "SELECT * FROM memory_versions WHERE memory_id = ? ORDER BY version_no",
                (memory_id,),
            ).fetchall()
        ]
        annotations = [
            dict(r) for r in self._conn.execute(
                "SELECT * FROM council_annotations WHERE memory_id = ? ORDER BY created_at",
                (memory_id,),
            ).fetchall()
        ]
        return {"memory": dict(memory), "versions": versions, "council_annotations": annotations}

    def promote_authorized(
        self,
        memory_id: str,
        *,
        authorized_by: str,
        authorization_source: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Promote a memory through trusted host code, never a model tool call.

        The MemoryProvider tool surface intentionally does not expose this method.
        A future MMQP UI/CLI policy gate can call it only after it has independently
        verified the human/Cipher Seat authorization event.
        """
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        authorized_by = (authorized_by or "").strip()
        authorization_source = (authorization_source or "").strip()
        if not authorized_by or not authorization_source:
            raise ValueError("promotion requires verified authorized_by and authorization_source")
        with self._lock:
            row = self._conn.execute(
                "SELECT state FROM memories WHERE memory_id = ?", (memory_id,)
            ).fetchone()
            if not row:
                raise ValueError("memory not found")
            old = row["state"]
            if old not in {"candidate", "disputed"}:
                raise ValueError(f"memory in state {old!r} cannot be promoted")
            now = _now()
            self._conn.execute(
                "UPDATE memories SET state='canonical', updated_at=? WHERE memory_id=?",
                (now, memory_id),
            )
            self._conn.execute(
                """
                INSERT INTO promotion_events(
                    event_id, memory_id, from_state, to_state, authorized_by,
                    authorization_source, reason, created_at
                ) VALUES (?, ?, ?, 'canonical', ?, ?, ?, ?)
                """,
                (_id("prom"), memory_id, old, authorized_by, authorization_source, reason, now),
            )
        return {"memory_id": memory_id, "state": "canonical", "previous_state": old}

    def _correct(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        memory_id = args["memory_id"]
        content = (args.get("content") or "").strip()
        if not content:
            raise ValueError("correct requires replacement content")
        row = self._conn.execute(
            "SELECT current_version_id FROM memories WHERE memory_id = ?", (memory_id,)
        ).fetchone()
        if not row:
            raise ValueError("memory not found")
        current = self._conn.execute(
            "SELECT version_no FROM memory_versions WHERE version_id = ?",
            (row["current_version_id"],),
        ).fetchone()
        next_no = int(current["version_no"]) + 1
        version_id, created = _id("ver"), _now()
        self._conn.execute(
            """
            INSERT INTO memory_versions(
                version_id, memory_id, version_no, content, source_episode_id,
                created_by, reason, valid_from, created_at
            ) VALUES (?, ?, ?, ?, ?, 'mmqp', ?, ?, ?)
            """,
            (
                version_id, memory_id, next_no, content, args.get("episode_id"),
                args.get("reason", "correction proposed"), created, created,
            ),
        )
        self._conn.execute(
            """
            UPDATE memories
            SET current_version_id=?, state='disputed', correction_weight=1.0,
                confidence=?, updated_at=?
            WHERE memory_id=?
            """,
            (version_id, _clamp(args.get("confidence"), 0.8), created, memory_id),
        )
        self._link("memory_version", row["current_version_id"], "superseded_by", "memory_version", version_id)
        self._conn.commit()
        return {
            "memory_id": memory_id,
            "version_id": version_id,
            "state": "disputed",
            "requires_promotion": True,
        }

    def _annotate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        annotation_id = _id("ann")
        self._conn.execute(
            """
            INSERT INTO council_annotations(annotation_id, memory_id, persona, content, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                annotation_id, args["memory_id"], args["persona"], args.get("content", ""),
                _clamp(args.get("confidence"), 0.5), _now(),
            ),
        )
        self._conn.commit()
        return {"annotation_id": annotation_id}

    def _signal(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        episode_id = args["episode_id"]
        exists = self._conn.execute(
            "SELECT 1 FROM episodes WHERE episode_id=?", (episode_id,)
        ).fetchone()
        if not exists:
            raise ValueError("episode not found")
        signal_id = _id("sig")
        self._conn.execute(
            """
            INSERT INTO signals(
                signal_id, episode_id, channel, signal_name, value_num, value_text,
                start_ms, end_ms, confidence, provenance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id, episode_id, args.get("channel", "system"), args["signal_name"],
                args.get("value_num"), args.get("value_text"), args.get("start_ms"), args.get("end_ms"),
                _clamp(args.get("confidence"), 1.0), args.get("provenance", "observed"), _now(),
            ),
        )
        self._conn.commit()
        return {"signal_id": signal_id}

    def _lineage(self, memory_id: str) -> Dict[str, Any]:
        if not self._conn:
            raise RuntimeError("MMQP is not initialized")
        links = [
            dict(r) for r in self._conn.execute(
                """
                SELECT * FROM provenance_links
                WHERE (from_type='memory' AND from_id=?)
                   OR (to_type='memory' AND to_id=?)
                   OR (from_type='memory_version' AND from_id IN (
                       SELECT version_id FROM memory_versions WHERE memory_id=?
                   ))
                   OR (to_type='memory_version' AND to_id IN (
                       SELECT version_id FROM memory_versions WHERE memory_id=?
                   ))
                ORDER BY created_at
                """,
                (memory_id, memory_id, memory_id, memory_id),
            ).fetchall()
        ]
        return {
            "memory_id": memory_id,
            "links": links,
            "versions": self._inspect(memory_id)["versions"],
        }

    def _link(self, from_type: str, from_id: str, relation: str, to_type: str, to_id: str) -> None:
        if not self._conn:
            return
        self._conn.execute(
            """
            INSERT INTO provenance_links(
                link_id, from_type, from_id, relation, to_type, to_id, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, '{}', ?)
            """,
            (_id("lnk"), from_type, from_id, relation, to_type, to_id, _now()),
        )


def create_provider(config: Optional[dict] = None):
    return MMQPMemoryProvider(config=config)
