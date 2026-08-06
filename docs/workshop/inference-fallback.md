# Inference fallback (emergency-only)

**Live OSAI/Granite is the primary narrative.** Recorded/local fallback exists only for mid-demo resilience (ADR-003).

## Enable (emergency drill)

```bash
export GATEWAY_STUB_MODE=false
export INFERENCE_FALLBACK=true
# keep OSAI_INFERENCE_URL pointing at the failing/live endpoint for the drill
```

When live upstream exhausts retries:

- Response includes `factory.fallback=true` and `factory.fallback_label=emergency-only`
- OTel span `inference.chat` sets `workshop.fallback=true` and `inference.fallback=true`

## Do not

- Do not start the workshop with fallback as the default story.
- Do not document mock Granite as the MVP path.

See presenter script: `demo/workshop/presenter-script.md`.
