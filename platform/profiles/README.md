# Platform profiles

Bootstrap `PROFILE` selects one of:

| Profile | File | Intent |
|---------|------|--------|
| `minimal` | `minimal.yaml` | Orchestrator + inference gateway + OTel |
| `standard` | `standard.yaml` | Workshop MVP vertical slice (default OCP) |
| `full` | `full.yaml` | standard + later agents / RHACS / Quay options |
| `kind-oss` | `kind-oss.yaml` | Kind + EG + Kuadrant + Ollama small models + Langfuse (no paid RH) |

`standard` is the OCP presenter workshop profile.  
`kind-oss` is the laptop path — see `docs/workshop/kind-oss.md` and ADR-014.
