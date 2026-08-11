# Production operating policy

The named local runtime is installed, but model-backed multi-agent production entry is not accepted.

- Hermes may complete deliberately single-owner work directly.
- A multi-agent Run requires exact project admission, a validated manifest and explicit worker/provider/model/effect/budget authority.
- `swarm_start` never implies dispatch.
- Unknown mutable outcomes are inspected or reconciled before any retry.
- Provider failure does not authorize Olympus, ACPManager, Harmonia, `talk_to`, private CLI mutation or a renamed fallback.
- Cancellation requires subsequent survivor verification; close must fail on unowned or live resources.
- Push, publication, deployment, credentials and spending remain independently authorized effects.

Until production entry passes, any claim that general model-backed operation is ready must be marked unaccepted.
