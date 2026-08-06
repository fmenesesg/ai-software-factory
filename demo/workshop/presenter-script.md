# Presenter script — AI Software Factory workshop

**Venue:** one presenter executes; audience observes.  
**Language:** English. **License:** Apache-2.0.

## Before the room

1. Copy `.env.example` → `.env` (never commit secrets).
2. Confirm `PROFILE=standard` for the MVP narrative (use `full` only for RHACS/Quay optional path).
3. Dry-run bootstrap:

```bash
./scripts/workshop-bootstrap.sh --dry-run
./demo/workshop/run-slice.sh --help
```

4. Verify live Granite path: `GATEWAY_STUB_MODE=false`, `OSAI_*` set.  
   Keep `INFERENCE_FALLBACK=false` unless rehearsing the **emergency-only** drill.

## Live slice (talk track)

| Step | Action | Audience sees |
|------|--------|---------------|
| 1 | Bootstrap session | Secrets land in session Secrets — not in git |
| 2 | Seed GitHub Issue | Issue URL becomes `issue_url` |
| 3 | Start orchestrator run | PM → Architect artifacts |
| 4 | Architect HITL on GitHub | Approval gates Developer |
| 5 | Developer PR | PR URL + Reviewer light |
| 6 | Tekton → GHCR → ephemeral | PR Check + URL + ns under `NAMESPACE_PREFIX` |
| 7 | GitOps promote HITL | No prod-like sync without approval |
| 8 | RHDH component | Visualization only — not HITL |
| 9 | Optional: docs/deploy/SRE agents | TechDocs notes, pipeline evidence, SLO notes |
| 10 | Teardown + revoke | `scripts/teardown-ephemeral.sh` + secrets checklist |

## Emergency fallback drill (optional, label clearly)

Only if live Granite fails mid-demo:

1. Set `INFERENCE_FALLBACK=true` (emergency-only — not the primary story).
2. Confirm OTel / response shows `fallback=true` / `workshop.fallback`.
3. Tell the room: “This is the emergency recorded/local path; live Granite is the default.”

## After the session

Follow [teardown runbook](../../docs/workshop/teardown.md).
