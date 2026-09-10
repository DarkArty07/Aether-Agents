# Inspected evidence and author decisions

## Evidence snapshot

Aether: b1baad948bc21e956d291c8d40abb2add6033b3c, compared with the handoff source base
cc93451799ded171c38fea98188e02fd75b0fe74. Maintained Hermes:
266e412fb83ad32af92ed391db942f88993d76a2. Upstream guard comparison:
2ddeba9e17a1df5471802481e3efef20885a20b2. Selected public baseline:
e624e9fde561e1add9388384012b295fde669ade. Loaded editable HEAD alone did not describe
its patched file contents, so relevant file hashes were compared independently.

| Issue | Verified finding and limits | Durable original evidence |
|---|---|---|
| #373 | Exact native calls failed VIEW_MISMATCH; a same-Project native reselection restored memory search/save/read. Deterministic binding matrix reproduces non-Git cwd failing before explicit lookup. Session recovery is not code correction; graph identity resolution is not an available index. | https://github.com/DarkArty07/Aether-Agents/issues/373#issuecomment-5625781033 |
| #390 | Schema-valid tool_calls and error counters fail global forbidden-key validation. Real EventBuilder -> reducer -> ReadModel.record_summary fails for both while stop passes. Native observation returned AETHER-OBSERVE-STATE-UNREADABLE, not proven storage corruption. | https://github.com/DarkArty07/Aether-Agents/issues/390#issuecomment-5625781244 |
| #389 | Maintained and current-upstream guard both promote the Python heredoc log path to a script. Upstream also misses one direct Python lifecycle-source control retained by maintained. Dangerous commands were strings inspected by the guard, never executed. | https://github.com/DarkArty07/Aether-Agents/issues/389#issuecomment-5625871464 |
| #382 | Real SessionDB append recovers after short synthetic lock. Bounded FTS indexes 8203 content characters from a 4194304-byte fixture; no causal historical writer was recovered. Read-only live evidence does not justify database mutation. | https://github.com/DarkArty07/Aether-Agents/issues/382#issuecomment-5625871143 |
| #275 | Original 68-byte PNG survives real native handler and Codex adapter byte-exact. Native branch was forced only in the isolated fixture; the local HTTP400 was explicitly simulated. No real backend qualification or causal transport fix has been established. | https://github.com/DarkArty07/Aether-Agents/issues/275#issuecomment-5625870794 |

The focused Aether baseline returned 259 passed, 1 skipped. The skip was the native
Graphify fixture prerequisite, not a newly waived test. Initial targeted diagnosis was
3 failed/8 passed; extended real-storage diagnosis was 5 failed/9 passed. These RED
results prove existing defects, not implementation success. One intermediate probe
import typo was corrected and is not product evidence. Other offline tools/state
checks are recorded in the issue comments; do not aggregate overlapping suites into
an invented coverage percentage.

Upstream #100273 (https://github.com/NousResearch/hermes-agent/pull/100273) was closed
without merge at inspection. Its staged-compaction proposal documents a plausible
writer convoy but does not identify the cause of Aether #382 and is not an approved
patch. The current guard upstream is not a drop-in solution for #389.

## Accepted author decisions and rejected shortcuts

- Reuse the owner's five existing issue records and one batch Objective Contract.
  No new principle, classifier, watcher, bus or ceremonial decomposition layer.
- Apply the existing CONTRIBUTING testing standard, with source-causal regressions
  and native functional oracles required by the owner's demand for actual resolution.
  Ordinary locked isolated dependency setup is permitted; unavailable prerequisites
  remain explicit and cannot become passing results.
- TS-373 keeps exact-session identity and conflict rejection. A broad exception
  fallback would conflate absent context with contradictory/unreadable evidence.
- TS-390 keeps the existing histogram schema and adds namespace/type-aware validation;
  deleting global forbidden keys or converting failed summaries to empty is rejected.
- TS-389 separates reference discovery from direct lifecycle detection. A blanket
  heredoc or Python exemption is rejected based on the comparative negative controls.
- TS-275 and TS-382 have bounded executable research outcomes, not invented build
  feasibility. Their material repair proposals return to Morfeo autonomously, then
  receive canonical plan/contract revision as needed. Independent fixes continue.
- Scope remains Aether and the maintained Hermes repair source. Existing route probes
  do not grant authority for provider/router subscriptions or separate-product edits.
- A scoped safe adoption of reviewed fixes is required for runtime claims; dirty-tree
  replacement, forced restart, arbitrary release or unrelated cleanup is not.

## Remaining research record

Supervisor/Implementer append evidence for the two causal gates here, attributed to
exact source/candidate revision and real versus synthetic producer. Morfeo owns any
resulting material design decision in plan.md. Do not replace recorded unknowns with
plausible narratives or call a diagnostic outcome an issue fix.
