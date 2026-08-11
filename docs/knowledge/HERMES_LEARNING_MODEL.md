# Hermes learning model

Aether uses Hermes-native knowledge layers:

| Layer | Purpose | Examples |
|---|---|---|
| current conversation | active intent and corrections | task scope, immediate preference |
| `USER.md` | durable user preferences | communication style, standing choices |
| `MEMORY.md` and memory tools | stable environment/user facts | recurring constraints, verified setup facts |
| sessions/search | prior conversational context | earlier rationale or outcome |
| project docs/source | project-specific authority and truth | contracts, architecture, tests |
| skills | reusable procedures | debugging, documents, research workflows |
| trace/evidence | attributable runtime facts | operation outcome, artifact reference |

Do not store secrets, temporary observations, raw prompts, provider tokens or speculative conclusions as durable knowledge. A project-specific workaround becomes a skill only after its trigger, limits, safe procedure and verification are generalized.

Aether has no automatic prompt/model promotion or causal self-improvement service. Prompt experiments require a preserved rollback version, a frozen comparison, equivalent conditions and explicit promotion authority. Activity volume or self-reported confidence is not proof of improvement.
