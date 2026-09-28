# MMQP Cathedral Memory Provider

MMQP is an experimental Hermes memory provider that treats memory as a governed lifecycle rather than a bag of facts.

## Foundation

1. Raw episodes are preserved before interpretation.
2. Text and voice are distinct intake channels.
3. Observable signals are stored separately from emotional interpretation.
4. Model-derived memory starts as an observation or candidate.
5. Canonical promotion is an explicit second step with an audit event.
6. Corrections preserve prior versions instead of deleting history.
7. Council personas annotate shared memories; they do not own separate competing truth stores.
8. Provenance and lineage are first-class.

## Current phase

This spike is deliberately dependency-light:

- SQLite persistence
- append-style raw episodes
- memory versioning
- candidate/canon/disputed state machine
- provenance links
- Council annotations
- dual-intake signal table
- simple weighted lexical retrieval
- Hermes MemoryProvider integration

It does **not** yet claim production-grade semantic retrieval, graph reasoning, acoustic emotion inference, or cryptographically secure human authorization.

## Setup

On this branch:

```bash
hermes memory setup
```

Select `mmqp` if plugin discovery exposes it, or set:

```bash
hermes config set memory.provider mmqp
```

Default DB: `$HERMES_HOME/mmqp.db`.

## Next layers

- Vector retrieval (pgvector/Qdrant)
- temporal knowledge graph adapter (Graphiti-compatible)
- voice feature bridge from Hermes Desktop audio capture
- deterministic policy gate for canonical promotion
- consolidation/reflection worker
- memory conflict detector
- retrieval feedback and decay
- Observatory graph/timeline UI
- DWA session-history ingestion
- MCP server so non-Hermes agents can share the same memory substrate
