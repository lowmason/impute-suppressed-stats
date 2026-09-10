# Stage 1 — log

Dated corrections and measurements for Stage 1's roadmap block. The block itself
states the current contract only; this file holds what it used to say and why
that changed (roadmap `## Stages`, stage-block rules 1 and 2).

## 2026-09-10 — `Produces` claimed a manifest from all four commands

**Superseded reading** (roadmap Stage 1 `Produces`, from derivation 2026-09-03
until `1be5bbf`):

> CLI `validate-config`, `registry verify`, `fetch --source {qcew,qcew_size,cbp}`,
> and `build-harmonized`, each writing a machine-readable manifest and idempotent
> for identical inputs.

**Why it changed.** THREE of the four write no manifest. Only `fetch` writes one
(`runs/source_manifest.parquet`, via `merge_source_manifest` at `fetching.py:190`).
`validate-config`, `registry verify` and `build-harmonized` write nothing.

> CORRECTED 2026-09-10, same day. The first version of this entry said `build-harmonized`
> writes `runs/<id>/schema_manifest.json` at `cli.py:150`. That line is inside
> `build_constraints_command`, not `build_harmonized_command`. `build_harmonized_command`
> (`cli.py:78-92`) computes output hashes and only echoes them; its `manifest_path` argument
> is an INPUT, read at `build.py:120` to disambiguate stored snapshots. `D-059` had already
> recorded this correctly and the correction contradicted it while citing its sibling `D-057`. §16.1's "every command MUST write a
machine-readable manifest" is therefore unmet, and is open as `D-057`.

**Why it mattered.** This is a *ticked* stage's `Produces` line, and the sentence
after it reads "Later stages may assume …". A completed stage was granting later
stages permission to assume an artifact that does not exist. Found by the
2026-09-09 system review's §2.3 (unnumbered MUSTs) and re-verified at HEAD.

**Note for whoever closes `D-057`.** A "recorded decline" was considered and
rejected at `specs/deferred_items.md` (`D-057`'s body): the roadmap's own
`Produces` line foreclosed it by promising the manifests.
