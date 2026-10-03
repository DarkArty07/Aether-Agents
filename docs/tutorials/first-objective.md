# Tutorial: your first objective

This tutorial takes one small practice repository through both of Aether's routes. You
will:

1. create a practice repository and initialize it as an Aether project;
2. let Morfeo adopt the project;
3. complete a small change on the **direct route**;
4. plan a larger change with `/aether-plan`;
5. deliver it through the **pipeline** (Objective Contract → Supervisor → Implementers);
6. observe progress and receive the result.

Agents run on the models you configured, so wording, timing and cost vary from run to
run. The steps below describe what each role is instructed to do and how you can verify
it yourself; they are not a transcript.

## Before you start

- Aether is installed and `aether doctor` reports `ready` ([Installation](../installation.md)).
- Each role has a model, and Morfeo has the `file` and `kanban` toolsets
  ([Installation, step 5](../installation.md#5-configure-a-model-for-each-role)).
- The Hermes gateway service is running, so board cards are dispatched to workers:

  ```bash
  systemctl --user status hermes-gateway-morfeo.service
  ```

## 1. Create a practice repository

`aether init` works only at the root of an existing Git repository, so create one first:

```bash
mkdir -p ~/code/aether-tutorial && cd ~/code/aether-tutorial
git init
cat > greet.py <<'EOF'
def greet() -> str:
    return "Hello, World!"


if __name__ == "__main__":
    print(greet())
EOF
git add greet.py
git commit -m "Initial commit"
```

## 2. Initialize the project

```bash
aether init --dry-run   # shows what it would do, changes nothing
aether init
```

Initialization writes the portable marker `.aether/project.toml`, binds it to exactly one
native Hermes Project for this path, and adds an ignore block so drafts and local notes
stay out of Git. Commit the marker:

```bash
git add .aether/project.toml .gitignore
git commit -m "chore: initialize the Aether project"
```

To let the Supervisor close out through pull requests, push the repository to GitHub
first and initialize with `aether init --forge github`. Without a remote, work stays local.
See [Project initialization](../guides/project-initialization.md).

## 3. Start Morfeo and let it adopt the project

```bash
aether
```

`aether` resolves this project and opens Morfeo in the terminal UI. On first contact,
Morfeo inspects the repository and its existing instructions and confirms the project's
principles with you. If root `AGENTS.md` is missing, it writes concise operating guidance
that describes the actual project. Answer its questions; Morfeo does not invent product
intent you did not state.

Later, `aether --resume latest` continues the latest session of this project.

## 4. A small objective: the direct route

Ask for something small, inspectable and easy to revert:

> Add an optional `name` parameter to `greet()` that defaults to "World", and add a
> pytest test for both cases.

For work like this, Morfeo is instructed to act **directly**: edit, run the tests and
report what changed with evidence. No contract and no board card are created, because
decomposition and independent review would add nothing.

Verify it yourself:

```bash
git log --oneline -3
git diff HEAD~1 --stat
```

## 5. Plan a larger objective

When you want a route before any work starts, use the planning entry:

> /aether-plan Add a command-line interface with `--name` and `--format text|json`,
> documentation in a README, and tests for every option.

Morfeo writes one local plan at `.aether/plans/<objective-slug>.md` with the destination,
the route, continuity notes, closure evidence and stop conditions. Then it **stops**: no
contract, card or worker follows from planning alone. The generic `/plan` command is not
an Aether alias. See [Objective Plans](../guides/objective-plans.md).

## 6. Deliver it through the pipeline

Tell Morfeo to proceed:

> The plan looks right. Go ahead.

Work with several responsibilities, real design decisions or uncertainty goes through the
pipeline:

1. **Contract.** Morfeo resolves any missing material decision with you, then writes the
   Objective Contract: objective, scope, authority, deliverables, acceptance, testing
   standard, stop conditions and references. It finalizes an immutable version at
   `.aether/objective-contracts/<contract-id>/v1.md` and commits it.
2. **Handoff.** Morfeo creates one card for the Supervisor on the contract's own execution
   board. The card carries a short envelope (contract ID, version, digest, base commit),
   not the whole contract.
3. **Decomposition.** The Supervisor checks that the contract is executable and creates
   independently testable Implementer units with explicit acceptance.
4. **Implementation.** Each Implementer works in its own branch and worktree, commits
   locally, runs the relevant tests and records evidence.
5. **Review and integration.** The Supervisor reviews work it did not write, integrates
   in dependency order and runs the integrated checks. With a GitHub forge it closes out
   with a push, a pull request, the required checks and a green merge.

You do not have to stay in the session while this runs.

To run the Implementer units on Claude Code instead of Hermes, ask for it explicitly when
Morfeo writes the contract. See [the Claude Code tutorial](claude-code.md#part-b-claude-code-as-the-implementer).

## 7. Observe progress

From the project directory:

```bash
aether observe                 # the open contract's review brief
aether observe --watch         # refresh as it changes
aether observe <contract-id> --json
```

You can also ask Morfeo "How is the contract going?". It uses the compact
`aether_observe` tool (`status`, then `changes` or `diagnose` when needed) and checks
freshness and coverage before it answers. `STATE_BUSY` or `CATCHUP_INCOMPLETE` only mean
another writer is busy: retry shortly. See [Observation](../guides/observation.md).

## 8. Receive the result

When the Supervisor finishes, Morfeo reviews the terminal result against the contract
before it reports. The report states what changed, how it was verified, anything left
out, the remaining risks and the release conclusions (`release_impact`,
`release_action`, `release_channel`). Check the work yourself:

```bash
git log --oneline --graph -10
python -m pytest
```

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `missing required Morfeo toolsets: file, kanban` | Add the toolsets to Morfeo's profile ([Installation, step 5](../installation.md#5-configure-a-model-for-each-role)). |
| `ambiguous project identity` | Pass the project explicitly: `aether --project /path/to/project`. |
| Cards stay in the ready column | Start the gateway (`systemctl --user start hermes-gateway-morfeo.service`) and run `aether doctor`. |
| A tool call is denied as a protected effect | The edge policy blocked a credential, external or destructive operation. Do not work around it; see [Policy and recovery](../guides/policy-and-recovery.md). |

## Next steps

- [Use Aether with Claude Code](claude-code.md)
- [Give every role a map of your project](project-knowledge.md)
- [Lifecycle](../guides/lifecycle.md), [Execution](../guides/execution.md) and
  [Expected agent behavior](../guides/expected-behavior.md)
