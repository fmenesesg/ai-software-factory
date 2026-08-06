# RHDH factory visualization (MVP)

RHDH shows factory and pipeline status. It is **not** HITL authority — Architect
approval, merge, and GitOps promote gates stay on GitHub (ADR-007).

## What to enable

1. Register the catalog component: `platform/rhdh/catalog-info.yaml`
2. Configure the GitHub integration with a bootstrap-prompted token (see
   `.env.example` / `docs/workshop/bootstrap.md`)
3. Enable the RHDH GitHub plugin so the factory Component shows:
   - Pull request Checks (`asf/ephemeral`, `asf/security-scan`, `asf/qa-tests`)
   - Linked repository activity for `fmenesesg/ai-software-factory`

## Presenter check

- Open the **AI Software Factory** Component in RHDH
- Confirm latest PR Check conclusions are visible from GitHub plugin data
- Do **not** approve promote or Architect reviews from RHDH UI

See also: `platform/rhdh/app-config.factory.yaml` (fragment) and
`docs/architecture/rhdh/README.md`.
