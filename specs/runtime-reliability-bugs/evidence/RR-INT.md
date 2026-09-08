# RR-INT integrated evidence — runtime reliability (#267/#292/#294/#295/#301/#304)

**Objective Contract:** `oc_5c2dad1b37b20a80@v1`
**SHA-256:** `8d9af05c77d7833675a8f985742c471963f77cd30aa8cd993837a1fcf9eeda4e`
**Portable project:** `12027989-a08f-41cd-a82c-54ff1bfb6b03`
**Unit:** RR-INT (terminal Supervisor integration/closeout)
**Review lane:** same-card unit reviews already completed; this file is integrated evidence, not a substitute for those reviews.

## Source revisions

| Tree | Identity | SHA |
| --- | --- | --- |
| Aether `origin/main` at integration start | `DarkArty07/Aether-Agents` | `3ded6953ab9db44281a6c67fcdf93189546126a1` |
| Design/contract base | `0dd27e0eff060f143f80879845f0d76561633f56` | merged `--no-ff` |
| Decomposition `tasks.md` | `7a45aa4715bc6f5a2746a7289fc5a2bcbff6fe7e` | merged `--no-ff` |
| Fork `aether-main` | `DarkArty07/aether-hermes` | `c185ee3bb5b6d609241432fd123c16143f065987` |
| Exact Hermes baseline (Aether wrapper) | tag `v2026.8.18` | `e624e9fde561e1add9388384012b295fde669ade` |
| Immutable upstream citation | `NousResearch/hermes-agent` | `9fd44b4dfc44138b9e5d5689acb56c438364ff7b` |

Unit commits remain individually inspectable (no squash/amend/rebase):

| Unit | Review run | Disposition | Aether commit(s) | Fork commit(s) | Compatibility |
| --- | --- | --- | --- | --- | --- |
| RR-267 | t_ea6c98a6 run 18 approved | reproduced-and-fixed | `66bb4dd6638ab1da8e9a56fd9e63211906fafeb6`, `a67f3d78bad49cac3c8debf3b5ef118c14590f19` | n/a | patch |
| RR-304 | t_0e064c53 run 14 approved | reproduced-and-fixed | `6aa83af1ea768c1f908d1a70088d44506836716c` (evidence) | `169572a845f30bda0231cb97035bfce5fb9e981d` | patch |
| RR-295 | t_5894f87f run 16 approved | reproduced-and-fixed | `d06cbd265fd9932585279b5d23da1a25ea7145ff` (evidence) | `b58db22b4968e837a745a42cae5cb007f3819a8c` | patch |
| RR-AUX B292 | t_2858d06b run 12 approved | already-working-with-integrated-evidence | `5c38247e07352098cca4f0534cd4dc12bb388479` (evidence) | `2337bd2d9efbf0421ac121877936e92bb9486e70` (tests only) | none |
| RR-AUX B301 | same | reproduced-and-fixed | same evidence | `0f56400b1603c8195590a04da47424a0df40b145` | patch |
| RR-294 | t_174a8028 run 20 approved | reproduced-and-fixed | `99f6271631cb4a6f8cadbe351aed3723ece40fc6` (evidence) | `cf5ff5fe2f51116364a10a9941f58f280e7ff4c4` | patch |

Integration merge commits (Aether `fix/runtime-reliability-six-bugs`, fork `fix/runtime-reliability-six-bugs`) preserve those unit SHAs. Exact post-ledger Aether/fork HEADs and GitHub merge SHAs are filled after verification and closeout.

## Per-issue integrated matrix

Filled after sterile `lab_run` on the integrated candidates. Independent reviewer controls: poisoned-env isolation, read-only same-run proof, cross-destination authentication, review cancellation ownership.

| Requirement | Disposition | Integrated command result |
| --- | --- | --- |
| B267 | reproduced-and-fixed | pending |
| B304 | reproduced-and-fixed | pending |
| B295 | reproduced-and-fixed | pending |
| B301 | reproduced-and-fixed | pending |
| B292 | already-working-with-integrated-evidence | pending |
| B294 | reproduced-and-fixed | pending |

## GitHub / release / residue

Filled at closeout. Anticipated aggregate conclusions (not a publication):

- `release_impact = patch`
- `release_action = defer`
- `release_channel = none`

Fork Actions: inherited workflows exist in the tree but repository Actions are disabled (`enabled=false`). Report NOT RUN, not green.

No live activation, credentials, settings mutation, tags, or package publication.
