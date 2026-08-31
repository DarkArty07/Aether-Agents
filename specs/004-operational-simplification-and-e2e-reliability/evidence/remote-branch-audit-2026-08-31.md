# Remote branch audit — 2026-08-31

**Status:** complete; remote branches were inspected and not deleted.

## Scope and reproducibility

This audit records the remote-tracking state in this repository at candidate checkpoint `d03db4cbbc6d129ce6065732fdc4212c044ddb0e`, with `origin/main` at `aba93d0ecdbebc44a22c2b9b71f31cb106efb9c4`. It excludes the symbolic `origin` ref and `origin/main`, leaving 16 non-main `origin/*` refs.

Run the following read-only commands from the repository root to reproduce the comparison. `git cherry origin/main <ref>` prints `+ <commit>` for a commit whose patch is not equivalent to `origin/main` and `- <commit>` for a patch-equivalent commit.

```bash
git for-each-ref --format='%(refname:short)' refs/remotes/origin | \
  grep -v -E '^origin$|^origin/main$' | \
  while IFS= read -r ref; do
    printf '\n## %s\n' "$ref"
    git cherry origin/main "$ref"
  done
```

No remote deletion, push, force-push, fetch, or other remote mutation was performed for this audit. The 16 remote-tracking refs listed below remain present. Each comparison has at least one `+` result and no `-` result, so none of these refs is authorized for deletion on patch-equivalence grounds.

## Results

| Ref | Tip | Unique non-equivalent commits | Patch-equivalent commits |
|---|---|---:|---:|
| `origin/bolt-combine-count-queries-6792233988890497898` | `47b5d0cd1d07c05400acaf9544ffbe328a2380c5` | 1 | 0 |
| `origin/bolt-combine-scalar-subqueries-15761689815295603012` | `0eb40e35213c06305da6336d67b45f162ad3d30c` | 1 | 0 |
| `origin/bolt/sqlite-query-optimization-10505412969633234736` | `5966464c271dce73340d707eb891f24eaba6bc32` | 1 | 0 |
| `origin/docs/orchestration-design-proposal` | `fa70c22cdc69950b75c7ee20ce5874660ae528bd` | 1 | 0 |
| `origin/feat/fedora-migration-restore` | `91e029c12962cac4daa5ecfad7ba85a2c91c0fcd` | 1 | 0 |
| `origin/feature/bolt-combine-count-queries-15425003224121403254` | `2aa09817fa93d214df4fd9d4368d55e861c5fdf3` | 1 | 0 |
| `origin/feature/bolt-combine-queries-1637703140851650341` | `64f6b240affe7758d8ab165afe69e6138c94e4ad` | 1 | 0 |
| `origin/feature/bolt-combine-queries-3539540605307090182` | `3298a9b93131bdb0daa5db78362f276e7abb5aa9` | 1 | 0 |
| `origin/feature/bolt-combine-sqlite-counts-15998035707348450995` | `f79e0d716f663261debd3586d238fface537b0bc` | 1 | 0 |
| `origin/feature/bolt-combine-sqlite-counts-8362612462196862373` | `291bc52d8f7dc2c0ed1cd53143a339e450a2425b` | 1 | 0 |
| `origin/feature/bolt-optimize-aggregate-queries-12385152594051889477` | `fcf16a5abea98e77fc1dd201f314a72515baa6d4` | 1 | 0 |
| `origin/feature/bolt-optimize-records-for-14241221337284364576` | `d200d549c591787a5f712fe166b6430339aef862` | 1 | 0 |
| `origin/feature/bolt-optimize-records-for-16612330796733782535` | `2bde59de70effafb889abccaa244d5644cbb1390` | 1 | 0 |
| `origin/feature/bolt-query-batching-6039672358429613201` | `be02bb27ee8e7434ca06eaef39ed1139b45f1c00` | 1 | 0 |
| `origin/feature/bolt-scalar-subqueries-5327821240369427554` | `3ee00eb48208b1c245b6cf0798efe3f130264abb` | 2 | 0 |
| `origin/feature/optimize-trace-store-9331286987442921046` | `c5dd3949be5ace9bf6bffbe620ed15b33da7f392` | 1 | 0 |

### `git cherry` output

```text
## origin/bolt-combine-count-queries-6792233988890497898
+ 47b5d0cd1d07c05400acaf9544ffbe328a2380c5

## origin/bolt-combine-scalar-subqueries-15761689815295603012
+ 0eb40e35213c06305da6336d67b45f162ad3d30c

## origin/bolt/sqlite-query-optimization-10505412969633234736
+ 5966464c271dce73340d707eb891f24eaba6bc32

## origin/docs/orchestration-design-proposal
+ fa70c22cdc69950b75c7ee20ce5874660ae528bd

## origin/feat/fedora-migration-restore
+ 91e029c12962cac4daa5ecfad7ba85a2c91c0fcd

## origin/feature/bolt-combine-count-queries-15425003224121403254
+ 2aa09817fa93d214df4fd9d4368d55e861c5fdf3

## origin/feature/bolt-combine-queries-1637703140851650341
+ 64f6b240affe7758d8ab165afe69e6138c94e4ad

## origin/feature/bolt-combine-queries-3539540605307090182
+ 3298a9b93131bdb0daa5db78362f276e7abb5aa9

## origin/feature/bolt-combine-sqlite-counts-15998035707348450995
+ f79e0d716f663261debd3586d238fface537b0bc

## origin/feature/bolt-combine-sqlite-counts-8362612462196862373
+ 291bc52d8f7dc2c0ed1cd53143a339e450a2425b

## origin/feature/bolt-optimize-aggregate-queries-12385152594051889477
+ fcf16a5abea98e77fc1dd201f314a72515baa6d4

## origin/feature/bolt-optimize-records-for-14241221337284364576
+ d200d549c591787a5f712fe166b6430339aef862

## origin/feature/bolt-optimize-records-for-16612330796733782535
+ 2bde59de70effafb889abccaa244d5644cbb1390

## origin/feature/bolt-query-batching-6039672358429613201
+ be02bb27ee8e7434ca06eaef39ed1139b45f1c00

## origin/feature/bolt-scalar-subqueries-5327821240369427554
+ c3231c920a3c3efe9f9484e608782111b868c695
+ 3ee00eb48208b1c245b6cf0798efe3f130264abb

## origin/feature/optimize-trace-store-9331286987442921046
+ c5dd3949be5ace9bf6bffbe620ed15b33da7f392
```

## Conclusion

All 16 non-main `origin/*` refs contain at least one commit with a unique, non-equivalent patch relative to `origin/main`; there are zero patch-equivalent commits in this audit. Retain every listed remote ref.
