# MMQP 2.0 — Recursive Cathedral Architecture

## Core rule

Recursive learning may propose change; it may not silently redefine canon.

MMQP separates raw experience, interpretation, and authorized truth.

## Reuse the Hermes seams

Hermes already exposes the integration points MMQP needs through `MemoryProvider` and `MemoryManager`: pre-turn recall, post-turn sync, pre-compression preservation, session lineage, delegation observations, built-in memory mirroring, and provider tools. MMQP should therefore be a provider/bridge, not a replacement runtime.

Hermes also already contains local holographic memory, multiple external memory adapters, desktop voice transcription, context compression, and session persistence. Those become inputs or optional backends rather than systems we re-create.

## Harpstar systems that feed MMQP

### Deep Work Assistant
DWA already stores session history and learns behavioral patterns. Treat it as an episodic sensor: focus sessions, reminder outcomes, app categories, and human-vs-agent activity become structured MMQP episodes.

### Emerald Grid / Sentra
Sentra already uses timelines, source times, event times, verification status, and signal provenance. Those patterns are useful for the future MMQP Observatory while civic/security domain data remains separate.

## MMQP layers

1. **Chronicle** — immutable episodes: conversations, tool events, DWA sessions, documents, corrections.
2. **Signal intake** — measurable text/voice signals stored separately from meaning.
3. **Candidate memory** — extracted claims, preferences, project rules, relationships, and lessons.
4. **Canon** — explicitly promoted high-trust memory.
5. **Council lenses** — Olari, Curio, Mithua, Syra, Aether, Rekharis, and Ashtem annotate the shared substrate.
6. **Ancestral Ledger** — versions and corrections retain lineage.
7. **Reflection/consolidation** — cheap models propose merges, conflicts, stale claims, and lessons but cannot self-promote them.

## Dual intake

For voice, the same episode should eventually carry both transcript/content and time-aligned audio observations. Increased volume or faster speech is an observation; an emotion label remains an interpretation unless the user explicitly states it.

## Retrieval target

Hybrid ranking should eventually combine semantic similarity, graph proximity, recency, repetition, importance, emotional salience, correction weight, project/persona relevance, confidence, and contradiction/staleness penalties.

## Borrow, do not surrender the architecture

- **Graphiti/Zep pattern:** temporal graph, episodes as source material, fact validity windows, source provenance.
- **Mem0 pattern:** practical semantic-memory integration and optional self-hosted vector backends.
- **Letta pattern:** small always-visible core memory blocks for identity and active constraints.
- **Hermes holographic provider:** local-first storage, trust feedback, entity recall.
- **Governance-kernel patterns:** append-only audit events, deterministic policy checks, drift detection, explicit authorization boundaries.

## Build sequence

**Phase 0:** provider scaffold, SQLite schema, episode capture, candidate/canon state, versioning, provenance, Council annotations, signal intake.
**Phase 1:** tests, deterministic promotion policy, correction/conflict rules, retrieval feedback.
**Phase 2:** embeddings + hybrid search; local first, pgvector/Qdrant optional.
**Phase 3:** temporal graph adapter, with Graphiti as the first implementation to test.
**Phase 4:** voice bridge from Hermes Desktop, preserving episode IDs and attaching acoustic observations.
**Phase 5:** reflection worker + Ancestral Ledger visualization.
**Phase 6:** MMQP MCP server so Hermes, DWA, future Council workers, IDE agents, and other models share one governed substrate.

## Non-negotiable invariants

- raw source is never silently overwritten
- interpretations identify themselves as interpretations
- corrections preserve lineage
- canon changes are auditable
- persona annotations do not become fact by repetition
- retrieval exposes provenance
- multimodal signals remain distinguishable
- recursive learning proposes; policy authorizes
