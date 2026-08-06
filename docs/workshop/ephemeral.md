# Ephemeral namespaces (M3)

PR pipelines deploy the sample-app into namespaces named:

```text
${NAMESPACE_PREFIX}pr-<pull_request_number>
```

Default prefix: `asf-workshop-` (see `.env.example`).

## PR evidence

On success the pipeline publishes:

- GitHub PR comment with **URL** and **namespace**
- Check stub name `asf/ephemeral` with the same evidence
- Artifact IDs: `image_digest`, `ephemeral_url`, `ns_name` (ADR-006)

Helper: `platform/pipelines/src/asf_pipelines/pr_evidence.py`

## Teardown

```bash
NAMESPACE_PREFIX=asf-workshop- DRY_RUN=true ./scripts/teardown-ephemeral.sh
NAMESPACE_PREFIX=asf-workshop- ./scripts/teardown-ephemeral.sh
```

The script refuses empty prefixes and only deletes namespaces that start with
`NAMESPACE_PREFIX`.
