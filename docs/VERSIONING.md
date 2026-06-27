# Versioning

The scheme is **`v[phase].[segment].[task]`** — `v{p}.{s}.{t}`.

It looks like semver but isn't: the three numbers map to the three units of work
in [`WORKFLOW.md`](WORKFLOW.md), not to API breakage.

| Position | Name | Meaning | Example |
|----------|------|---------|---------|
| `p` | **Phase** | A release-sized version of the tracker. | `v1` |
| `s` | **Segment** | A feature area inside a phase. Resets to `1` each phase. | `v1.1` |
| `t` | **Task** | One focused change inside a segment. Resets to `1` each segment. | `v1.1.4` |

## Release tags vs. work IDs

- **`v{p}.0.0` is a release tag** on `main` after a phase merges. `v1.0.0` = main
  after the foundation phase ships.
- **`v{p}.{s}.{t}` (non-zero s/t) is a work-item ID** — it lives in the phase plan
  and in commit trailers like `[v1.1.4]`. Not a git tag.

## Branch naming

| Branch | Off of | Purpose | Lifetime |
|--------|--------|---------|----------|
| `main` | — | Always-shippable. Reviewed phase merges only. | permanent |
| `v{p}` | `main` | Integration branch for a whole phase. | until phase merges |
| `v{p}.{s}` | `v{p}` | Work branch for one segment. | until segment merges |

No `claude`, `anthropic`, or model-name tokens in branch names.

## Merge style

- **Segment → phase:** `--no-ff` so each segment is a visible, revertible unit.
- **Phase → main:** `--no-ff`, then `git tag v{p}.0.0`.

## Frozen baseline

There is no pre-existing app, so **`v1` is the first real phase** (the foundation).
`v1.0.0` will be the first tag on `main`.

## Quick reference

```
main ──●──────────────────────────●(tag v1.0.0)──▶
        \                        /
   v1    ●──────●──────●────────●   (phase integration)
          \    / \    /
   v1.1    ●──●   \  /   segments branch off v1, merge back
   v1.2            ●●
```
