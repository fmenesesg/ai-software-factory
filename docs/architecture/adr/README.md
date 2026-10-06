# Architecture Decision Records (mirrors)

These entries are **pointers** to authoritative Engram ADRs. Full ADR text lives in Engram;
do not duplicate long-form decisions here unless intentionally syncing after review.

Engram topic prefix: `sdd/ai-software-factory/adr-NNN`

| ADR | Title | Engram topic |
|-----|-------|--------------|
| 001 | Monorepo layout with extractable sample-app | `sdd/ai-software-factory/adr-001` |
| 002 | LangGraph SDLC + Tekton CI/CD + GitOps promote | `sdd/ai-software-factory/adr-002` |
| 003 | Live Granite primary; pluggable gateway; emergency fallback | `sdd/ai-software-factory/adr-003` |
| 004 | MCP-first; A2A deferred | `sdd/ai-software-factory/adr-004` |
| 005 | One Deployment per agent + shared SDK | `sdd/ai-software-factory/adr-005` |
| 006 | Artifact contract Issue → promote | `sdd/ai-software-factory/adr-006` |
| 007 | HITL via GitHub only; RHDH visualization only | `sdd/ai-software-factory/adr-007` |
| 008 | Profiles minimal / standard / full | `sdd/ai-software-factory/adr-008` |
| 009 | RAG: PostgreSQL + pgvector for MVP | `sdd/ai-software-factory/adr-009` |
| 010 | OTel schema: run_id / tokens / tools / cost / fallback | `sdd/ai-software-factory/adr-010` |
| 011 | Bootstrap-prompted secrets; no hardcode | `sdd/ai-software-factory/adr-011` |
| 012 | Orders/inventory sample-app | `sdd/ai-software-factory/adr-012` |
| 013 | Engram-only SDD store (no `openspec/`) | `sdd/ai-software-factory/adr-013` |
| 014 | Kind OSS local platform (EG + Kuadrant) | `sdd/ai-software-factory/adr-014` (see [014-kind-oss.md](./014-kind-oss.md)) |

Index observation (Engram): `sdd/ai-software-factory/adr-index`

## Status

ADRs 001–013: **Accepted** (design phase 2026-08-06).  
ADR-014: **Accepted** (Kind OSS pivot 2026-10-06).
