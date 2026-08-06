# Audience guide — observe only

You are attending a **presenter-led** workshop. You do **not** need cluster credentials, GitHub tokens, or a personal lab environment.

## What you will watch

- A single presenter bootstraps the AI Software Factory session.
- Agents (PM → Architect → Developer → Reviewer → …) hand off **artifact IDs** through LangGraph.
- **GitHub** is the only HITL authority (reviews / approvals / promote PRs).
- **Tekton** builds, tests, pushes to **ghcr.io**, and deploys an ephemeral namespace.
- **RHDH** shows pipeline/check status for visualization — it does not approve promote.

## What you should not do

- Do not run bootstrap or mutate the cluster.
- Do not paste or request secrets in chat.
- Do not treat recorded/local Granite as the main story — that path is **emergency-only**.

## Useful links (presenter will open)

- Architecture overview: `docs/architecture/overview.md`
- Bootstrap docs: `docs/workshop/bootstrap.md`
- Presenter script: `demo/workshop/presenter-script.md`
