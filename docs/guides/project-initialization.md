# Project initialization

`aether init` makes an **existing Git repository root** an Aether Project. It is implemented and intentionally narrow.

## Preconditions

- Run at the repository root (or pass that root as `PATH`); a plain directory and a subdirectory of a repository are refused.
- One non-archived native Hermes Project must already have that exact resolved repository path as its `primary_path`.
- If several native Projects have that exact path, provide the desired ID with `--hermes-project ID`.

The command opens Hermes' Project registry read-only. It never creates, archives, or modifies a native Hermes Project, and it never chooses by display name, slug, current directory, or an approximate path.

```bash
# Discovery only: no marker or registry write.
aether init --dry-run

# Initialize the existing repository root.
aether init [PATH] [--name NAME] [--forge local|github] [--hermes-project ID]
```

## Result

On success, initialization:

1. writes or validates `.aether/project.toml` against the canonical project schema;
2. registers the portable project UUID against the repository path and exact native Hermes Project ID in local Aether state; and
3. ensures `.aether/project.toml` and finalized `.aether/objective-contracts/` paths are trackable while `.aether/drafts/` stays ignored.

It appends the canonical ignore-policy block only when necessary. It does not overwrite an invalid existing marker, silently merge a copied identity, or modify unrelated ignore rules. A moved repository can re-register a stale mapping only after identity validation; two live repositories with the same portable project identity are refused.

## Greenfield limit

The broader product design calls for greenfield and brownfield support, but this current implementation does **not** run `git init` in an empty directory. Create an existing Git repository and the exact-path native Hermes Project first, then run `aether init`. This distinction prevents documentation from presenting a planned greenfield product behavior as current.

For the parser surface, see [CLI reference](../reference/cli.md). For the identity's role in handoff, see [Objective Contracts](objective-contracts.md).
