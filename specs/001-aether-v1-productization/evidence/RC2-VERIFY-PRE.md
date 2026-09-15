# RC2-VERIFY-PRE — independent verification of the reused pre-contract outcomes

**Unit.** RC2-VERIFY-PRE (Implementer, read-only) of the Aether `1.0.0-rc.2` objective.

**Authority.** Objective Contract `oc_742f9f4797494bf9@v1`, SHA-256
`f084eca7e703201c620408069df8f06b89cade82514ceb934c792f71bdda04fc`, plus the
Supervisor-owned breakdown `specs/001-aether-v1-productization/tasks-rc2.md` (unit entry
RC2-VERIFY-PRE). The clause under test is the contract's reuse rule: *reuse only
independently verified v1 implementation outcomes*.

**Method.** Every fact below was re-derived from primary sources: the live repository and
its Git objects, the GitHub API/CLI, the published release bytes, an HTTPS readback of the
existing public site, and one re-run of the disposable-board canary against a clean
checkout of the accepted maintained-fork revision. The rc.1 lane's returned prose was
treated as a claim to falsify, never as evidence. No source behavior was added or changed
and no acceptance is recorded here.

**Effects.** This unit made no remote or live effect: no push, PR, merge, tag, release or
asset write, no issue mutation, no workflow dispatch or deployment, no service restart or
activation, no runtime/board/state write. The only writes were this record, its local
commit on the unit branch, and scratch roots under a temporary directory (reported in §8).

## 0. Reading conventions

- Each measurement states the command that produced it and the observed output.
- **Sanitization.** Operator paths appear as `<aether-unit-worktree>`, `<fork-checkout>`,
  `<fork-worktree@rev>`, `<fork-dev-venv>`, `<unit-venv>`, `<scratch-root>` and
  `<live-board-db>`; process ids appear as `<pid …>`; board tasks as `<canary task A/B>` and
  `<successor task>`; the branch name of a reviewed PR, when it embeds an execution-card id,
  appears as `<unit-branch>`. Commit and object digests, SHA-256 asset digests, PR numbers,
  workflow-run ids and public URLs are published verbatim because the measurement is
  meaningless without them.
- **Raw evidence.** The unsanitized transcripts, canary verdict JSONs and runner scripts of
  the measurements below are not tracked in this repository: repository policy keeps machine
  paths, board data, logs and session state out of public artifacts, and this record is
  sanitized for the same reason. They are retained in a temporary scratch root
  (`<scratch-root>`, a directory under the system temporary area — not durable and not part
  of the repository), enumerated file by file with size, class and SHA-256 in the attached
  `RC2-VERIFY-PRE-retained-evidence-inventory.txt.gz`. §11 states exactly which files are
  attached to the owning card and which of them exist only in that temporary root.
- Where a value is a live-state value rather than an artifact identity (the live board
  digest), it is published only as the before/after equality the measurement requires.

## 1. Measured identities

| Identity | Value | Source |
| --- | --- | --- |
| Clean pre-contract Aether base (`origin/main`) | `5758b89dfb19a71719faa8d1821849f8d66acacb` | §2 |
| Contract-landing commit on the unit branch | `acb89ca85c02c41dca10009b2806428850a0f0bc` | §2 |
| Maintained-fork accepted pin (`aether-main` tip) | `7a4fdcd083409c31c09cfa3bfa345354e8576a7e` | §3 |
| Accepted fork revision's tree | `0253df7de573ea695206a5f3bf2407cb3e48e320` | §3 |
| rc.1 annotated tag object → commit | `cda1eccae588197251ca22e9a0fdffaf81c4d599` → `748aa24ce5684185f65aa88b0e85919627ff6538` | §7 |
| Disposable-board canary fixture digest | `25ce5c7610464467c6aae35dcca6b028fdbf3a520dd1f862c17322176d2559f2` | §6 |
| `hermes_cli/kanban_db.py` under test | `532fd5400a495c0f706e378d2e394b21b669a571da3a2ef197444920ef530573` | §6 |

## 2. Measurement 1 — AC-01 base: the clean pre-contract revision

```console
$ git fetch --tags origin
$ git rev-parse origin/main
5758b89dfb19a71719faa8d1821849f8d66acacb
$ git rev-parse main
acb89ca85c02c41dca10009b2806428850a0f0bc
$ git rev-parse HEAD
acb89ca85c02c41dca10009b2806428850a0f0bc
```

`origin/main` is exactly the declared clean pre-contract base after fetching; the local
`main`/unit HEAD carries only the contract-landing commit `acb89ca…` on top of it.

PR #455 is a merged, normal-review merge whose merge commit is that base:

```console
$ gh pr view 455 --json number,state,mergedAt,mergeCommit,headRefName,baseRefName,title
{"baseRefName":"main","headRefName":"<unit-branch>","mergeCommit":{"oid":"5758b89dfb19a71719faa8d1821849f8d66acacb"},"mergedAt":"2026-09-15T20:39:12Z","number":455,"state":"MERGED","title":"docs(hlp): integrate the maintained-fork terminal-worker reap record (#450)"}
```

Every check reported for that PR is green — three `observation-qualification` matrix
entries (3.11/3.12/3.13), three `policy` matrix entries (3.11/3.12/3.13) and
`pull-request-target`:

```console
$ gh pr checks 455
observation-qualification (3.11)	pass	19m56s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547578059
observation-qualification (3.12)	pass	8m15s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547577872
observation-qualification (3.13)	pass	8m38s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547578022
policy (3.11)	pass	30s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547578023
policy (3.12)	pass	33s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547577565
policy (3.13)	pass	33s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547577804
pull-request-target	pass	2s	https://github.com/DarkArty07/Aether-Agents/actions/runs/35018408245/job/104547577896
```

## 3. Measurement 2 — AC-01 fork pin: the accepted revision is published

Fork PR #14 is merged and its merge commit is the accepted pin, and the fork remote's
branch ref resolves to the same object:

```console
$ gh pr view 14 --repo DarkArty07/aether-hermes --json number,state,mergedAt,mergeCommit,headRefName,baseRefName,title
{"baseRefName":"aether-main","headRefName":"fix/450-terminal-worker-reap-clean","mergeCommit":{"oid":"7a4fdcd083409c31c09cfa3bfa345354e8576a7e"},"mergedAt":"2026-09-15T20:02:41Z","number":14,"state":"MERGED","title":"fix(kanban): reap superseded workers before spawning successors (#450)"}

$ git ls-remote origin refs/heads/aether-main          # run inside the fork checkout
7a4fdcd083409c31c09cfa3bfa345354e8576a7e	refs/heads/aether-main
```

The merge is content-faithful to the fix branch: its parents are the rc.1 fork pin and
the fix commit, and its tree equals the fix commit's tree (no conflict resolution):

```console
$ git rev-list --parents -n 1 7a4fdcd083409c31c09cfa3bfa345354e8576a7e
7a4fdcd083409c31c09cfa3bfa345354e8576a7e 9031bae0e8b0ab40c4fd7ba50c644972ff512611 21628fc3790d825b8dc8082134f5cd382ec551f2
$ git rev-parse '7a4fdcd083409c31c09cfa3bfa345354e8576a7e^{tree}'
0253df7de573ea695206a5f3bf2407cb3e48e320
$ git rev-parse '21628fc3790d825b8dc8082134f5cd382ec551f2^{tree}'
0253df7de573ea695206a5f3bf2407cb3e48e320
```

**Published-commit proof, consumer side.** A fetch inside a clone that already holds the
object proves nothing, so the object was fetched into an empty scratch repository that
started with zero objects:

```console
$ cd <scratch-root>/consumer && git init -q -b scratch .
$ git count-objects -v
count: 0
size: 0
in-pack: 0
packs: 0
$ git fetch --no-tags https://github.com/DarkArty07/aether-hermes.git 7a4fdcd083409c31c09cfa3bfa345354e8576a7e
 * branch                7a4fdcd083409c31c09cfa3bfa345354e8576a7e -> FETCH_HEAD
$ git rev-parse FETCH_HEAD ; git cat-file -t FETCH_HEAD ; git rev-parse 'FETCH_HEAD^{commit}' ; git rev-parse 'FETCH_HEAD^{tree}'
7a4fdcd083409c31c09cfa3bfa345354e8576a7e
commit
7a4fdcd083409c31c09cfa3bfa345354e8576a7e
0253df7de573ea695206a5f3bf2407cb3e48e320
$ git for-each-ref          # empty: the object exists only as FETCH_HEAD
```

The server admitted a by-SHA fetch of `7a4fdcd…` and served its commit and tree, so the
pin is genuinely published on `aether-main`, not merely present in a local clone.

**Read-only observation (no action taken).** The fork checkout that sits on `aether-main`
is at `54eeb56dabefc98821d696656ed58c55dd777346`, which is an *ancestor* of the accepted
pin — that checkout is simply behind the branch tip, and this unit left it untouched:

```console
$ git -C <fork-checkout> rev-parse HEAD ; git -C <fork-checkout> rev-parse refs/heads/aether-main ; git -C <fork-checkout> rev-parse origin/aether-main
54eeb56dabefc98821d696656ed58c55dd777346
54eeb56dabefc98821d696656ed58c55dd777346
7a4fdcd083409c31c09cfa3bfa345354e8576a7e
$ git -C <fork-checkout> merge-base --is-ancestor 54eeb56dabefc98821d696656ed58c55dd777346 7a4fdcd083409c31c09cfa3bfa345354e8576a7e
exit=0
$ git -C <fork-checkout> log --oneline 7a4fdcd083409c31c09cfa3bfa345354e8576a7e..54eeb56dabefc98821d696656ed58c55dd777346
(no output)
```

The accepted revision therefore had to be materialized for the canary in a scratch
worktree (§6) rather than read from that checkout.

## 4. Measurement 3 — the merge chain into the base

```console
$ gh pr view 448 --json number,state,mergedAt,mergeCommit,headRefName,title
{"headRefName":"<unit-branch>","mergeCommit":{"oid":"cbe6002af648ada3b961b2aa210747bac25b59d4"},"mergedAt":"2026-09-15T15:25:01Z","number":448,"state":"MERGED","title":"fix(release): declare RELEASE_BUNDLE_DIR at step level so the release workflow is valid (#445)"}
$ gh pr view 449 --json number,state,mergedAt,mergeCommit,headRefName,title
{"headRefName":"<unit-branch>","mergeCommit":{"oid":"e81eed9fdbaa4c2423a7a2f9f15d7bf8079c8006"},"mergedAt":"2026-09-15T17:07:38Z","number":449,"state":"MERGED","title":"fix(docs): reconcile the public release status with the published v1.0.0-rc.1 prerelease (#239)"}
$ gh pr view 452 --json number,state,mergedAt,mergeCommit,headRefName,title
{"headRefName":"<unit-branch>","mergeCommit":{"oid":"a1d6c5df7cad65022a3562726c04b05cba1ed6b5"},"mergedAt":"2026-09-15T18:44:04Z","number":452,"state":"MERGED","title":"fix(website): derive the Pages content oracle from the canonical docs corpus (#446)"}
```

All three carry the same seven green checks as #455 (`gh pr checks 448|449|452`: three
`observation-qualification`, three `policy` and `pull-request-target`, every conclusion
`pass`). The three #446 commits are ancestors of the base:

```console
$ git merge-base --is-ancestor ee5dc3d224ea3d11bda27f831e547e0e22d4178c 5758b89dfb19a71719faa8d1821849f8d66acacb ; echo exit=$?
exit=0     # rev-list --count ee5dc3d…  ..5758b89… = 93
$ git merge-base --is-ancestor 1ef647b77e2041b93829ed264071985345f67c7d 5758b89dfb19a71719faa8d1821849f8d66acacb ; echo exit=$?
exit=0     # rev-list --count 1ef647b…  ..5758b89… = 92
$ git merge-base --is-ancestor 0144dfee4c5ab21c60051cddb83716c121e4f5e2 5758b89dfb19a71719faa8d1821849f8d66acacb ; echo exit=$?
exit=0     # rev-list --count 0144dfe…  ..5758b89… = 91
```

## 5. Measurement 4 — AC-03: the automatic Pages deployment and the corrected live site

The deployment run exists, succeeded, is automatic (`push` to `main`, not a dispatch) and
ran at the #452 merge commit:

```console
$ gh run view 35009308894 --json conclusion,event,headSha,headBranch,workflowName,createdAt
{"conclusion":"success","createdAt":"2026-09-15T18:44:07Z","event":"push","headBranch":"main","headSha":"a1d6c5df7cad65022a3562726c04b05cba1ed6b5","workflowName":"Website Pages"}
$ gh run view 35009308894 --json jobs --jq '.jobs[] | {name, conclusion, status}'
{"conclusion":"success","name":"build","status":"completed"}
{"conclusion":"success","name":"deploy","status":"completed"}
```

Run history for that workflow shows no manual dispatch at all, so the observed success is
the automatic one:

```console
$ gh run list --workflow 'Website Pages' --event workflow_dispatch --limit 20 --json databaseId
[]
$ gh run list --workflow 'Website Pages' --limit 20 --json event --jq '.[].event' | sort | uniq -c
     12 push
```

**Live readback (HTTPS, no login, no dispatch, no configuration change):**

```console
$ curl -sS -o /dev/null -D - --max-time 60 https://darkarty07.github.io/Aether-Agents/
HTTP/2 200
server: GitHub.com
content-type: text/html; charset=utf-8
last-modified: Tue, 15 Sep 2026 18:45:31 GMT
strict-transport-security: max-age=31556952
cache-control: max-age=600
```

The corrected content oracle derives its expectation from the canonical `docs/` corpus
(`website/tests/content.test.mjs`: the search index must cover every tracked `docs/**`
markdown document exactly, in both directions). The deployed artifact satisfies that
expectation:

```console
$ curl -sS -w 'http_code=%{http_code} content_type=%{content_type} size_download=%{size_download}\n' \
    --max-time 60 https://darkarty07.github.io/Aether-Agents/docs/search.json
http_code=200 content_type=application/json; charset=utf-8 size_download=200913
$ python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print("entries:",len(d));print("slugs:",json.dumps(sorted(x["slug"] for x in d)))' <scratch-root>/logs/live-docs-search.json
entries: 17
slugs: ["authority", "getting-started", "guides/execution", "guides/lifecycle", "guides/objective-contracts", "guides/observation", "guides/policy-and-recovery", "guides/project-initialization", "guides/project-knowledge", "guides/telegram-monitor", "index", "product-boundary", "reference/capabilities", "reference/cli", "reference/limitations-and-troubleshooting", "reference/plugins-and-tools", "roles-and-authority"]
```

Cross-check against the corpus re-derived from Git, at both the deployed revision and the
current base (17 documents each, identical sets):

```console
$ git ls-tree -r --name-only a1d6c5df7cad65022a3562726c04b05cba1ed6b5 -- docs | grep '\.md$' | wc -l
17
$ git ls-tree -r --name-only 5758b89dfb19a71719faa8d1821849f8d66acacb -- docs | grep '\.md$' | wc -l
17
$ python3 -c "import json;live=sorted(d['slug'] for d in json.load(open('<scratch-root>/logs/live-docs-search.json')));a=[l.strip() for l in open('<scratch-root>/corpus-a1d6c5d.txt') if l.strip()];b=[l.strip() for l in open('<scratch-root>/corpus-base.txt') if l.strip()];print('live==a1d6c5d corpus:',live==a);print('live==5758b89 corpus:',live==b);print('a1d6c5d corpus==base corpus:',a==b)"
live==a1d6c5d corpus: True
live==5758b89 corpus: True
a1d6c5d corpus==base corpus: True
```

The rendered documentation page also identifies the revision it was built from, which the
oracle asserts for the manual:

```console
$ curl -sS -w 'url=%{url_effective} http_code=%{http_code} content_type=%{content_type} size_download=%{size_download}\n' \
    --max-time 60 https://darkarty07.github.io/Aether-Agents/docs/guides/execution/
url=https://darkarty07.github.io/Aether-Agents/docs/guides/execution/ http_code=200 content_type=text/html; charset=utf-8 size_download=18661
$ grep -o 'blob/[0-9a-f]\{40\}/' live-execution.html | sort -u
blob/a1d6c5df7cad65022a3562726c04b05cba1ed6b5/
```

Quoted excerpt produced by the corrected oracle's own corpus check — the search-index
entry for `guides/project-knowledge`, taken from the live index:

> … with two tools: project_knowledge and work_memory. Morfeo, Supervisor and Implementer
> receive the same action schemas. The Graphify engine is an external, isolated component,
> not a fork of Hermes and not an MCP requirement. This build provides local structural
> indexing, bounded graph exploration, optio…

(description: *Graphify, mapa técnico compartido y experiencias por rol.*; the oracle's
`'Graphify'` substring assertion on this slug holds in the live index.)

## 6. Measurement 5 — AC-04: disposable-board canary re-run

**Usage read first.** `--case {coexist,current} --scratch SCRATCH [--json-out JSON_OUT]`;
the fixture repoints `HERMES_HOME`, `HERMES_KANBAN_DB`, `HERMES_KANBAN_WORKSPACES_ROOT`
and `HERMES_KANBAN_BOARD` into `--scratch` before any DB access and asserts the resolved
DB path is inside it.

**Tree under test.** A detached scratch worktree was created from the existing fork
checkout at the accepted revision — the checkout sitting on `aether-main` was not moved:

```console
$ git -C <fork-checkout> worktree add --detach <scratch-root>/fork-worktree 7a4fdcd083409c31c09cfa3bfa345354e8576a7e
$ git -C <scratch-root>/fork-worktree rev-parse HEAD
7a4fdcd083409c31c09cfa3bfa345354e8576a7e
$ git -C <scratch-root>/fork-worktree status --porcelain
(clean)
$ git -C <fork-checkout> rev-parse HEAD          # unchanged, still on aether-main
54eeb56dabefc98821d696656ed58c55dd777346
```

**Interpreter class.** Every `<interpreter>` marker in this section denotes the same
interpreter class: `<fork-dev-venv>`, the fork checkout's own provisioned development
virtualenv (Python 3.11.15, `psutil` 7.2.2, `pytest` 9.1.1), reached from the fork checkout
and never from this unit's worktree. The class is named rather than quoted because the
fork's `tests/conftest.py` autouse live-system guard needs `psutil` to prove that a child
PID is inside the test process subtree, so a different interpreter changes the outcome — the
labelled counter-run below records that effect in full. Interpreter identities: attached
`m5c-interpreters.txt`.

The canary imports the real board surface, so the record states which module it exercised.
Ran from inside the checkout under test, `hermes_cli` resolves to that tree, and the file
bytes equal the Git object at the accepted revision:

```console
$ cd <fork-worktree@7a4fdcd> && PYTHONPATH=<fork-worktree@7a4fdcd> <interpreter> -c \
    "import hermes_cli, hermes_cli.kanban_db as kb; print(hermes_cli.__file__); print(kb.__file__); print(hasattr(kb.DispatchResult(), 'superseded_reaped'))"
<fork-worktree@7a4fdcd>/hermes_cli/__init__.py
<fork-worktree@7a4fdcd>/hermes_cli/kanban_db.py
True
$ sha256sum <fork-worktree@7a4fdcd>/hermes_cli/kanban_db.py
532fd5400a495c0f706e378d2e394b21b669a571da3a2ef197444920ef530573  kanban_db.py
$ git -C <fork-checkout> show 7a4fdcd083409c31c09cfa3bfa345354e8576a7e:hermes_cli/kanban_db.py | sha256sum
532fd5400a495c0f706e378d2e394b21b669a571da3a2ef197444920ef530573  -
```

**Lane 1 — `coexist`: a terminal non-current worker is reaped before a successor can
mutate its workspace.**

```console
$ CANARY_LIVE_BOARD_DB=<live-board-db> PYTHONPATH=<fork-worktree@7a4fdcd> <interpreter> \
    <aether-unit-worktree>/specs/001-aether-v1-productization/fixtures/qualify_superseded_worker_reap_450.py \
    --case coexist --scratch <scratch-root>/scratch-coexist --json-out <scratch-root>/logs/canary-coexist.json
board db      : <scratch-root>/scratch-coexist/home/kanban/boards/canary-450/kanban.db
kanban_db     : <fork-worktree@7a4fdcd>/hermes_cli/kanban_db.py
live board    : <live-board-db> (untouched)
case          : coexist
task A       : run=2 pid=<pid A2> event=block_loop_detected run_status=blocked task_status=triage
identity     : tasks.worker_pid=None task_runs.worker_pid=None (cleared by the terminal transition)
task B       : run=3 pid=<pid B1> run_status=blocked task_status=blocked
successor    : spawned=['<successor task>']
stale at spawn: {"<pid A1>": false, "<pid A2>": false, "<pid B1>": false}
reap         : [{"task_id": "<canary task A>", "run_id": 1, "run_outcome": "blocked", "task_status": "triage", "prev_pid": <pid A1>, "recorded_start_time": <t>, "termination_attempted": true, "terminated": true, "sigkill": false},
                {"task_id": "<canary task A>", "run_id": 2, "run_outcome": "blocked", "task_status": "triage", "prev_pid": <pid A2>, "recorded_start_time": <t>, "termination_attempted": true, "terminated": true, "sigkill": false},
                {"task_id": "<successor task>", "run_id": 3, "run_outcome": "blocked", "task_status": "ready", "prev_pid": <pid B1>, "recorded_start_time": <t>, "termination_attempted": true, "terminated": true, "sigkill": false}]
hold         : []
event kinds  : A=['created', 'claimed', 'spawned', 'blocked', 'unblocked', 'claimed', 'spawned', 'block_loop_detected', 'superseded_worker_termination', 'superseded_worker_termination'] B=['created', 'claimed', 'spawned', 'blocked', 'unblocked', 'superseded_worker_termination', 'claimed', 'spawned']
stale after  : alive={"<pid A1>": false, "<pid A2>": false, "<pid B1>": false} exit_codes={"<pid A1>": -15, "<pid A2>": -15, "<pid B1>": -15} workspace_writes_after_successor={"<pid A1>": 0, "<pid A2>": 0, "<pid B1>": 0}
verdict       : pass
EXIT=0
```

The incident's own shape is reproduced first (the run ended by the board, not by the
worker: `block_loop_detected`, run `blocked`, card `triage`, both `worker_pid` columns
cleared) — and then all three superseded processes are reaped before the successor is
spawned: none is alive at spawn, each is reported `terminated`, each produced a durable
`superseded_worker_termination` event, and none wrote into the workspace after the
successor started (0 writes versus the pre-fix coexistence of the rc.1 lane).

**Lane 2 — `current`: a long-running current worker stays alive across ticks regardless of
elapsed time.**

```console
$ ... --case current --scratch <scratch-root>/scratch-current --json-out <scratch-root>/logs/canary-current.json
case          : current
current run  : id=1 pid=<pid C> (no terminal transition)
tick 1       : elapsed=0.002s reaped=[] held=[] worker_alive=True
tick 2       : elapsed=6.005s reaped=[] held=[] worker_alive=True
tick 3       : elapsed=12.008s reaped=[] held=[] worker_alive=True
tick 4       : elapsed=18.011s reaped=[] held=[] worker_alive=True
worker alive : True after 18.012s and 4 ticks
event kinds  : ['created', 'claimed', 'spawned']
verdict       : pass
EXIT=0
```

No tick treated the current run as a reap or spawn-gate candidate, no termination event was
emitted, and the worker was still alive at the end. (This lane's verdict is structural —
process liveness and empty candidate sets — so it carries no timing threshold and no gate
number is claimed from it.)

**The revision's own regression module also passes** on the same tree (extra, not required
by the card's measurement set). Because the quoted `<interpreter>` decides this outcome (see
the interpreter-class note above), the run was re-executed with its transcript retained and
the class named inline — attached log `m5c-forkvenv-pytest.txt`:

```console
$ cd <fork-worktree@7a4fdcd>
$ PYTHONPATH=<fork-worktree@7a4fdcd> <fork-dev-venv>/bin/python -m pytest tests/hermes_cli/test_kanban_superseded_worker_reap_450.py -q
...........                                                              [100%]
11 passed in 9.02s
EXIT=0
```

(An earlier inline invocation of the same command, before the transcript was retained,
recorded `11 passed in 8.60s`; that earlier value is the one carried in the raw digest. The
two agree on the verdict.)

**Counter-run — the unit-venv artifact is not a regression.** The same module executed by
*this unit worktree's own* virtualenv (`<unit-venv>`: Python 3.13.15, **no `psutil`**,
`pytest` 9.1.1) reports `3 failed, 8 passed`, and each failure is the fork's live-system
guard refusing the reap's signal:

```console
$ cd <fork-worktree@7a4fdcd>
$ PYTHONPATH=<fork-worktree@7a4fdcd> <unit-venv>/bin/python -m pytest tests/hermes_cli/test_kanban_superseded_worker_reap_450.py -q
FF.......F.                                                              [100%]
...
E       RuntimeError: tests/conftest.py live-system guard: blocked os.kill(<pid>, 15) — PID is outside the test process subtree. ...
FAILED tests/hermes_cli/test_kanban_superseded_worker_reap_450.py::test_out_of_band_block_leaves_no_identity_then_reap_terminates_worker
FAILED tests/hermes_cli/test_kanban_superseded_worker_reap_450.py::test_dispatch_tick_reaps_before_it_spawns_the_successor
FAILED tests/hermes_cli/test_kanban_superseded_worker_reap_450.py::test_reap_is_idempotent
3 failed, 8 passed in 7.59s
EXIT=1
```

(The traceback bodies are elided above; the attached transcript carries them verbatim.)
Without `psutil` the guard cannot establish that a worker child PID is inside the test
process subtree, so it blocks `os.kill(<pid>, 15)` and the reap never runs — an artifact of
the unit venv's dependency set, not a defect in the revision under test. A later reader must
not misread it as a regression: under `<fork-dev-venv>` exactly the same module is
`11 passed`. Full transcript attached gzipped as `m5c-unitvenv-pytest.txt.gz` (gunzip →
`11238` bytes, sha256 `4e36c6161a518239c4928c006c8533bd992774d50fe2f959f150b9e4656722fc`).

**Private-root refusal guard.** Exercised in isolation — no board was opened, and both
refusals fire before any DB access:

```console
$ <interpreter> <scratch-root>/m5b_guard.py
kanban_db under test : <fork-worktree@7a4fdcd>/hermes_cli/kanban_db.py
scratch root         : <scratch-root>/guard-scratch
live board (guard)   : <live-board-db>
guard 1 (scratch db == live board): REFUSED -> refusing to run: scratch DB resolved to the live board
guard 2 (db outside scratch)      : REFUSED -> refusing to run: DB <scratch-root>/outside/kanban.db is outside <scratch-root>/guard-scratch
guard 3 (db inside scratch)       : board db      : <scratch-root>/guard-scratch/home/kanban/boards/canary-450/kanban.db
kanban_db     : <fork-worktree@7a4fdcd>/hermes_cli/kanban_db.py
admitted (as designed)
```

**The live/shared board was untouched.** Snapshots taken immediately before and after the
two canary runs are identical in file digest and in row counts:

```console
$ sha256sum <live-board-db>
e2a29b588062b00c73b285e9e11e31676c7e9d6a8987d2affcf977620e8c4448  <live-board-db>        # before
e2a29b588062b00c73b285e9e11e31676c7e9d6a8987d2affcf977620e8c4448  <live-board-db>        # after
$ sqlite3 'file:<live-board-db>?mode=ro&immutable=1' "SELECT ...counts..."
tasks=10  task_runs=5  task_events=77  task_comments=9      # before
tasks=10  task_runs=5  task_events=77  task_comments=9      # after
```

The canary's own rows landed in the disposable boards instead (read back from the scratch
board files: `coexist` → tasks=2, task_runs=4, task_events=18; `current` → tasks=1,
task_runs=1, task_events=3), and each run printed its scratch DB path with the live board
marked untouched.

## 7. Measurement 6 — AC-05: rc.1 is immutable, published and rejected

**Tag object and target.** The annotated tag dereferences to the recorded commit, locally
after `git fetch --tags` and on the remote via the GitHub API:

```console
$ git for-each-ref refs/tags/v1.0.0-rc.1 --format='%(refname) %(objecttype) %(objectname) %(*objecttype) %(*objectname)'
refs/tags/v1.0.0-rc.1 tag cda1eccae588197251ca22e9a0fdffaf81c4d599 commit 748aa24ce5684185f65aa88b0e85919627ff6538
$ gh api repos/DarkArty07/Aether-Agents/git/ref/tags/v1.0.0-rc.1
{"ref":"refs/tags/v1.0.0-rc.1","object":{"sha":"cda1eccae588197251ca22e9a0fdffaf81c4d599","type":"tag"}}
$ git cat-file -p cda1eccae588197251ca22e9a0fdffaf81c4d599
object 748aa24ce5684185f65aa88b0e85919627ff6538
type commit
tag v1.0.0-rc.1
tagger DarkArty07 <DarkArty07@users.noreply.github.com> 1789478194 -0600

Aether 1.0.0-rc.1
…
Runtime source: maintained fork DarkArty07/aether-hermes, branch aether-main,
commit 9031bae0e8b0ab40c4fd7ba50c644972ff512611, materialized source-tree digest 495e5f4b8d9ecc293b5ea956ef693d8bc0cd78b3f6ac03475a6cfefb4b40ef31.
…
This is a qualified pre-stable milestone. It is not acceptance of stable 1.0.0,
does not publish to PyPI, and leaves the WSL2 and stable-release gates open.
```

**Release properties and assets.** `prerelease=true`, `draft=false`, target `main`,
published 2026-09-15T13:24:54Z, exactly eight assets. Every asset was downloaded with
`gh release download` and re-hashed; the recomputed digests equal both the release's own
advertised `sha256:` digests and the closeout digests recorded in
`specs/001-aether-v1-productization/evidence/LC-CLOSE.md` §6:

| Asset | Bytes | Download re-hash (verified) | LC-CLOSE §6 prefix |
| --- | --- | --- | --- |
| `aether_agents-1.0.0rc1-py3-none-any.whl` | 674845 | `19c6cf5248c05485ec883cfea5ee29c7b1fbbdf7b8f352d085b29b3bfced354a` | `19c6cf52…` |
| `aether_agents-1.0.0rc1.tar.gz` | 1044899 | `f8eac2a4a00dee85b9cd53b0761c087524303e06285deec210f310f58673fcb5` | `f8eac2a4…` |
| `aether-hermes-source-9031bae0e8b0ab40c4fd7ba50c644972ff512611.tar.gz` | 65899009 | `61b7ee62045f8a80d0d6aeaff46a86e1f83687e220c6d9b7504652619f709db6` | `61b7ee62…` |
| `aether-agents-1.0.0rc1-release-lock.json` | 2356 | `0ac3b355651164bb9d54b28b5bb0761135ed10e3202b6f1457fcde610575f653` | `0ac3b355…` |
| `aether-agents-1.0.0rc1-provenance.json` | 2624 | `0a76c5d87f392073472e5c5710cfb441981c8a263e4aeac0dc1501a32e2c5382` | `0a76c5d8…` |
| `aether-agents-1.0.0rc1-package-members.json` | 2453752 | `578257b0c005fcf90de0882fecd1efb4163d141ee682fa2e2cf8fa3a10087ddf` | `578257b0…` |
| `aether-agents-1.0.0rc1-clean-install.json` | 14917 | `249affb58f864162bdda55c6b1420dfc021708cf4f8f76e67f51f3abf147da9e` | `249affb5…` |
| `SHA256SUMS` | 767 | `0c12d8757dc0bf655efe5b392cfa2f696605add49f88b3e071c482369f896589` | `0c12d875…` |

```console
$ gh release download v1.0.0-rc.1 --repo DarkArty07/Aether-Agents --dir <scratch-root>/rc1-assets
$ cd <scratch-root>/rc1-assets && sha256sum ./*
19c6cf5248c05485ec883cfea5ee29c7b1fbbdf7b8f352d085b29b3bfced354a  ./aether_agents-1.0.0rc1-py3-none-any.whl
f8eac2a4a00dee85b9cd53b0761c087524303e06285deec210f310f58673fcb5  ./aether_agents-1.0.0rc1.tar.gz
61b7ee62045f8a80d0d6aeaff46a86e1f83687e220c6d9b7504652619f709db6  ./aether-hermes-source-9031bae0e8b0ab40c4fd7ba50c644972ff512611.tar.gz
0ac3b355651164bb9d54b28b5bb0761135ed10e3202b6f1457fcde610575f653  ./aether-agents-1.0.0rc1-release-lock.json
0a76c5d87f392073472e5c5710cfb441981c8a263e4aeac0dc1501a32e2c5382  ./aether-agents-1.0.0rc1-provenance.json
578257b0c005fcf90de0882fecd1efb4163d141ee682fa2e2cf8fa3a10087ddf  ./aether-agents-1.0.0rc1-package-members.json
249affb58f864162bdda55c6b1420dfc021708cf4f8f76e67f51f3abf147da9e  ./aether-agents-1.0.0rc1-clean-install.json
0c12d8757dc0bf655efe5b392cfa2f696605add49f88b3e071c482369f896589  ./SHA256SUMS
```

Every one of the eight equals the digest GitHub itself advertises for the asset
(`gh release view v1.0.0-rc.1 --json assets`), so the served bytes are the recorded bytes.

**The rejection warning is present and prominent** — the release body opens with it, as a
GitHub alert callout, before any changelog:

> [!WARNING]
> **Published, but NOT accepted — not eligible for activation.**
> … the exact published bytes contain a stale public statement … Those embedded bytes
> cannot be corrected without replacing published assets or rewriting the tag, both of
> which are forbidden … `v1.0.0-rc.1` is therefore **not accepted and must not be
> activated**, and this release must not be cited as evidence of owner-objective
> acceptance. A new versioned release candidate (`v1.0.0-rc.2`) is the versioned remedy,
> pending.

Nothing on rc.1 was written: the lane only read the tag ref, the tag object, the release
metadata, the body and the assets.

## 8. Preservation and non-effect evidence

| Preserved surface | Observation |
| --- | --- |
| Owner's primary checkout and its uncommitted paths | not opened, not read, not modified by this unit |
| Live runtime release and mutable state | not opened, not read, not modified; no service, unit, gateway, launcher or Desktop effect |
| `home/`, credentials, provider/model/router configuration | not read, not modified |
| Fork checkout on `aether-main` | HEAD still `54eeb56…`; only a *detached scratch worktree* was added from it and removed afterwards |
| Live/shared board | file digest and row counts identical before/after the canary (§6); no card, run, event or comment written by this unit |
| Websites, docs corpus and the Pages workflow | not modified; the public site was only fetched over HTTPS |
| rc.1 tag, release and assets | read-only; no write, replacement, `--clobber`, tag move or `--force` |
| Unrelated worktrees, branches, services, boards | untouched |

Commands run by this unit are read-only with respect to those surfaces: `git fetch`,
`git ls-remote`, `git rev-parse`/`git cat-file`/`git merge-base`/`git for-each-ref`,
`git show`, `git worktree add/remove` (scratch), `gh pr view|checks`, `gh run view|list`,
`gh release view|download`, `gh api` GET, `curl` GET, `sqlite3` read-only, `sha256sum`,
`pytest` (in the scratch tree). The scratch root under a temporary directory holds the
retained runner scripts, the transcripts and the machine-readable values digest, all
enumerated in the attached inventory and summarized in §11; its disposable parts — the
consumer clone, the canary scratch boards, the downloaded rc.1 assets and the detached fork
worktree — were removed after use; the fork worktree was then re-created detached at the same
accepted revision for the §6 module re-run, so the unit leaves no objective residue.

`git diff --check` is clean, and
`uv run --frozen python scripts/check_public_artifacts.py --root .` reports no violations
after this record is tracked (see the card handoff for the captured output).

## 9. Coverage of the assigned obligations

| Card measurement | Contract reference | Check actually run | Result |
| --- | --- | --- | --- |
| 1. Base revision and its review/check/merge evidence | AC-01 | §2 | `origin/main` = `5758b89…`; PR #455 MERGED with that merge commit; 7/7 checks `pass` |
| 2. Fork pin published, proven consumer-side | AC-01 | §3 | PR #14 MERGED → `7a4fdcd…`; remote branch ref = that commit; empty-repo by-SHA fetch succeeds |
| 3. Merge chain and #446 ancestry | AC-03 (merge half) | §4 | #448/#449/#452/#455 MERGED, checks green; three #446 commits are ancestors of the base |
| 4. Automatic Pages deployment and live site | AC-03 | §5 | run `35009308894` `success`, `event=push`, `a1d6c5d…`; live site 200 + 17-entry index equal to the canonical corpus at the deployed revision and at the base; page carries the `a1d6c5d…` revision link |
| 5. Canary re-run on the accepted fork revision | AC-04 | §6 | both lanes `pass` on a clean checkout of `7a4fdcd…`; refusal guard exercised; live board byte-identical before/after |
| 6. rc.1 tag/target/asset bytes/rejection warning | AC-05 | §7 | tag object `cda1ecc…` → `748aa24…` (local and remote); prerelease, not draft, 8 assets, all 8 re-hashes equal the advertised and closeout digests; warning present and prominent |

## 10. Not verified, with reasons

1. **Continuous non-mutation of rc.1.** The measurement establishes that the tag object,
   release properties and the eight asset bytes *are now* what the publication-time records
   say they are (release-advertised digests, `LC-CLOSE.md` §6). It cannot prove that no
   intervening write ever occurred: GitHub exposes no history for tags/releases/assets, and
   this unit exercised no write credential. The claim is snapshot agreement, not an audit
   trail.
2. **Edge/CDN stability of the live site.** The readback proves the content served for the
   requested URLs at the recorded instant derives from the deployed revision; it says
   nothing about other edge locations or later times (the response carries
   `cache-control: max-age=600`).
3. **The live site at every route.** The oracle's corpus equality and the revision link
   were checked on the index route and one documentation route plus the search index; not
   every rendered page was fetched.
4. **Fork-side test suite beyond the reap module.** The revision's own
   `test_kanban_superseded_worker_reap_450.py` passes under `<fork-dev-venv>` (11 tests, §6);
   under this unit worktree's own `<unit-venv>` the same module reports `3 failed, 8 passed`
   for the guard/dependency reason recorded in §6, which is an interpreter artifact and not a
   regression. The wider fork suite was not re-run here — it is not part of this unit's
   measurement set, and the v1 lane's whole-suite numbers remain that lane's evidence, not
   this record's.
5. **Machine load during the canary.** No load figure was captured for the canary window;
   its verdicts are structural (process liveness, reap membership, candidate sets), so no
   gate number is derived from it either way.
6. **Observations left for their owners (no action taken).** The fork checkout sitting on
   `aether-main` is behind the accepted pin (§3); the later activation unit needs a clean
   checkout at the accepted revision, which this record neither performs nor blocks.
7. **Out of scope by contract.** Stable `1.0.0`, PyPI publication and WSL2/macOS/Windows
   qualification were not measured or implied by anything above.

## 11. Reproduction notes

- The record's branch base is the contract-landing commit on top of `5758b89…`
  (`origin/main`); all Git evidence above requires a `git fetch --tags` first.
- The canary is invoked from inside a clean checkout of the accepted revision with
  `PYTHONPATH` pointing at that checkout, `CANARY_LIVE_BOARD_DB` set to the live board path
  (used only for the guard), an explicit `--scratch` root and `--json-out` capture; the
  fixture's own `--help` documents the usage.
- The §6 fork-module runs are reproduced from inside the scratch checkout with `PYTHONPATH`
  pointing at it: `<fork-dev-venv>/bin/python -m pytest
  tests/hermes_cli/test_kanban_superseded_worker_reap_450.py -q` → `11 passed`; the same
  command with `<unit-venv>/bin/python` → `3 failed, 8 passed` (the live-system guard
  artifact described in §6, not a regression).
- **Where the raw evidence lives.** No unsanitized value is tracked in this repository —
  repository policy keeps machine paths, board data, logs and session state out of public
  artifacts — so the raw set is retained in the temporary scratch root `<scratch-root>`
  (not durable, not part of the repository) and attached to the owning card as far as that
  surface allows. Attached:

  | Attachment | bytes | sha256 | backs |
  | --- | --- | --- | --- |
  | `RC2-VERIFY-PRE-raw-digest.txt` | 1137 | `03bd9a2f47913169636cc2f783ee062efd31e972c450b6de8b98ecfd86c870b4` | machine-readable values digest behind §1 |
  | `m5c-forkvenv-pytest.txt` | 271 | `e4ec1361d2793e2793dc13fdd4d2506c8ec83f769eb8e922a5a45562139b5fb0` | §6 fork-module run under `<fork-dev-venv>` (`11 passed`) |
  | `m5c-unitvenv-pytest.txt.gz` | 2193 | `6582efbc28e5280670fb9920d9f203ebc5e8dce0076ee52439fc0410bac7cdb0` | §6 counter-run under `<unit-venv>` (gunzip → 11238 B, `4e36c6161a518239c4928c006c8533bd992774d50fe2f959f150b9e4656722fc`) |
  | `m5c-interpreters.txt` | 564 | `f57e64b152a73f40cd8cdff827b80a97909df2a43ceb8aa17729796b7694f76f` | the two interpreter classes named in §6 |
  | `m5_canary.sh` | 2297 | `176d1367f1f03d3ead733d56b962bcf1adfef16c578c45e828e675439ab23ef7` | §6 canary orchestration, including the live-board before/after snapshots |
  | `m5b_guard.py` | 1655 | `e7ed49ed9bcf06facb8a3ffe9b4bd6403bf3b51c199b44f4d287cd2ba46cb8b1` | §6 private-root refusal guard |
  | `RC2-VERIFY-PRE-retained-evidence-inventory.txt.gz` | 3446 | `80501175972b159c8efe95607f9b7a599d9cff9319714af37c501e3cf269d344` | file-by-file inventory of the whole retained set (gunzip → 8989 B, `ca734f155fe56379cda84187b1863e7f37a8fb1fc1fd2c5c4229abcb0da85517`) |

- **Temporary-only (not attached), beyond the two §6 module logs above:** the remaining
  per-measurement transcripts (`logs/m1-*`, `logs/m2-*`, `logs/m3-*`, `logs/m4-*`,
  `logs/m5.txt`, `logs/m6.txt`, the two canary verdict JSONs, the live-board before/after
  snapshots, the downloaded-asset digest list, the live-site payloads), the remaining runner
  scripts (`capture.sh`, `cleanup.sh`, `commit_and_check.sh`, `m2_consumer_fetch.sh`,
  `m4_site.sh`, `m4b_oracle.sh`, `m5c_pytest_reexport.sh`, `m7_inventory.sh`), the corpus
  lists and the values digest. Each one's size and SHA-256 is in the attached inventory; the
  transcripts are reproducible from the commands quoted in the section that used them, and
  they are temporary rather than durable evidence.
