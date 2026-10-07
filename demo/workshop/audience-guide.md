# Audience guide — observe only

You are attending a **presenter-led** demo. You do **not** need cluster credentials or GitHub tokens.

## What you will watch

- The presenter creates a **GitHub Issue** with label `asf/run`.
- The Kind stack poller starts an orchestrator run (`asf-run-id` comment on the Issue).
- Agents hand off artifacts: PM → Architect → **GitHub HITL** → Developer → Reviewer → Security → QA → Docs → Tekton ephemeral → GitOps promote gate → SRE.
- **GitHub** is the only HITL authority.
- **Jaeger** + the status board show run/agent health (not RHDH on this laptop path).

## What you should not do

- Do not run bootstrap or mutate the cluster.
- Do not paste or request secrets in chat.

## Useful links (presenter will open)

- Status: http://asf.demo.local:8080/status/
- Jaeger: http://jaeger.asf.demo.local:8080/
- Presenter script: `demo/workshop/presenter-script.md`
