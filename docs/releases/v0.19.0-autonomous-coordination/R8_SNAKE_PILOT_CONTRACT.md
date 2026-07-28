# R8 Bounded Active Pilot — Three.js Snake

**Status:** APPROVED FOR IMPLEMENTATION; ACTIVATION REQUIRES PRE-PILOT SECURITY PASS

## Objective

Prove whether the new coordination architecture can autonomously finish a real, polished product. The product is a disposable local Three.js Snake game. The R8 coordinator—not manual Hermes `talk_to` calls—must own task progression, assignment, dispatch decisions, retries, evidence, review generation, and closure proposal. Olympus remains the only owner of ACP processes and sessions.

## Exact authority boundary

R8 may:

- create and write only inside one canonical disposable pilot root;
- compile the fixed Snake task graph into immutable proposals;
- use admitted E1 repository-local file/build/test effects;
- dispatch contract-bound tasks through `OlympusRuntimeAdapter`;
- poll known Olympus sessions;
- validate structured filesystem/build/test evidence;
- generate bounded correction and independent review tasks;
- propose closure after all gates pass.

R8 may not:

- mutate Aether live config, gateway, authentication, credentials, services, or databases outside its pilot store;
- deploy, publish, merge, tag, release, open PRs, or contact external product services;
- execute arbitrary caller-supplied commands or prompts;
- own or terminate ACP processes directly;
- infer semantic completion from Olympus technical status;
- self-review or self-approve closure;
- write outside the exact pilot root, including through symlinks.

## Fixed pilot identity and workspace

- Pilot ID: `snake-r8`
- Project ID: `snake-r8`
- Product root: `/home/arty/Escritorio/agentes/aether-pilots/snake-r8`
- Store: `<pilot-root>/.aether-pilot/pilot.db`
- Marker: `<pilot-root>/.aether-pilot/marker.json`
- Local-only operation; no live Aether configuration switch is required.

The root must be absent or contain only a matching pilot marker when first admitted. Every relative scope and artifact is resolved and checked beneath this root. A symlink escape is a terminal pilot failure.

## Product brief

Build a creative, polished, responsive Three.js Snake game with:

- a coherent original visual direction rather than a generic neon demo;
- smooth 3D motion, responsive camera, lighting, particles, spatial feedback, and readable HUD;
- deterministic grid-safe Snake mechanics with no 180-degree reversal;
- food spawning only on free cells;
- score, best score persistence, escalating difficulty, pause/resume, restart, game-over flow, sound toggle, and reduced-motion support;
- keyboard controls and usable touch/mobile controls;
- responsive desktop/mobile layout and accessible focus/labels;
- no console errors or unhandled promise rejections;
- production build and deterministic automated tests;
- README with run/build/test instructions.

The coordinator may accept local package-manager network access only for installing the declared Three.js/Vite/test dependencies. It may not deploy or contact runtime application services.

## Fixed task graph

1. `snake-spec` — Daedalus, role `design`, read/write product design artifact only.
2. `snake-build` — Hefesto, role `implement`, depends on `snake-spec`, writes the product.
3. `snake-verify` — Hefesto, role `verify`, depends on `snake-build`, runs tests/build and corrects bounded implementation defects.
4. `snake-review` — Athena, role `review`, depends on `snake-verify`, read-only independent product/security review.
5. `snake-closure` — Ictinus, role `completion`, depends on `snake-review`, read-only independent completion decision.

The coordinator may generate at most one correction task per failed implementation/review task. Total tasks including corrections: 8. Concurrency: 1 for the first pilot. Global retries: 3. Per-task retry: 1. Wall-clock budget: 45 minutes. No fourth independent review attempt for one stable review task.

## Structured result envelope

Every Daimon task must end with exactly one JSON object between markers:

```text
AETHER_PILOT_RESULT_V1
{...}
END_AETHER_PILOT_RESULT_V1
```

Required fields:

```json
{
  "pilot_id": "snake-r8",
  "task_id": "snake-build",
  "attempt": 1,
  "status": "completed|failed|correction_required|accepted",
  "changed_paths": ["relative/path"],
  "artifact_hashes": {"relative/path": "sha256"},
  "verification": [{"command": "npm test", "exit_code": 0}],
  "findings": [],
  "recommendation": "accept|correction_required|reject"
}
```

Free-form text and raw Olympus `completed` are advisory only. The coordinator independently checks containment, file existence, hashes, required artifacts, and allowed task semantics.

## State model

```text
PENDING → READY → INTENT_RECORDED → DISPATCHED → RUNNING
RUNNING → EVIDENCE_PENDING → REVIEWED → ACCEPTED
RUNNING/EVIDENCE_PENDING/REVIEWED → CORRECTION_REQUIRED → READY
Any non-recoverable violation → BLOCKED/FAILED
ACCEPTED tasks unlock dependencies
All accepted + independent closure → COMPLETE
```

Forbidden transition: technical `RUNNING → COMPLETE`.

A dispatch intent is committed before calling Olympus. Retries create a new immutable attempt; they never erase prior evidence. Unknown dispatch outcome blocks instead of blindly redispatching.

## Durable state

The local SQLite store records:

- immutable pilot manifest and hash;
- task definitions and hashes;
- state/attempt/session/assignee;
- dispatch intents and receipts;
- observations and structured evidence;
- artifact hashes and review findings;
- budget/retry use;
- final closure package.

SQLite uses WAL, schema versioning, integrity checks, unique task/attempt and session bindings, same-instance locking, and fail-closed transactions. It is pilot-local persistence, not production distributed identity.

## Pre-activation gates

Before running the real Snake pilot:

1. compiler/model/store/coordinator tests pass;
2. restart recovery and duplicate-dispatch tests pass;
3. malformed envelope, path escape, symlink escape, hash mismatch, self-review, stale generation, budget exhaustion, store lock/corruption, and illegal transition tests pass;
4. full coordination and repository suites pass;
5. Ruff, format, compile and diff checks pass;
6. Athena independently reviews R8 activation code and returns PASS within three total attempts;
7. the disposable root is created only after the security gate;
8. gateway/config/auth health baselines are captured before and after without mutation.

## Pilot success criteria

R8 succeeds only if:

- no Snake production task was manually delegated with `talk_to`;
- all real task sessions were opened by the R8 coordinator through Olympus;
- the product is built and independently reviewed;
- restart/recovery evidence is exercised during the pilot;
- build and automated tests pass;
- browser desktop/mobile checks show no console errors, overflow, dead controls, or broken core flow;
- no path outside the pilot root changed relative to the captured baseline;
- gateway/config/auth remain unchanged;
- final independent completion authority accepts the artifact;
- the closure package records task/session IDs, attempts, transitions, hashes, verification, findings, and residual risks.

## Decision after the pilot

- `KEEP HYBRID`: the architecture finished the product with bounded corrections and useful evidence.
- `REWORK`: the product finished but coordination required unsafe/manual intervention.
- `REJECT ACTIVATION`: duplicate work, scope escape, unbounded retry, false closure, lifecycle ownership breach, or inability to finish.

No result from this pilot authorizes general production activation, deployment, publication, R9, merge, tag, or release.