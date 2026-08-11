# Trace schema

Trace is a durable, secret-safe record of admitted lifecycle facts. It correlates project, Run, Task, Dispatch, operation, contract and provider evidence without becoming a second provider state machine.

`swarm_trace` supports:

- `query` for ordered lifecycle evidence;
- `record_decision` for a real authorized decision and its affected identities;
- `record_evidence` for an artifact/test reference, producer, digest, observed outcome, criteria, unknowns and limitations.

Trace records must not contain credentials, raw prompts, raw model responses or unrestricted transcripts. Append replay under one operation ID must be byte-equivalent. Historical entries are immutable.

The exact fields and limits are defined in the v1alpha2 JSON bundle and `protocol.py`.
