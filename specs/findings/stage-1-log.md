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

**Why it changed.** Two of the four write no manifest. `fetch` writes
`runs/source_manifest.parquet` and `build-harmonized` writes
`runs/<id>/schema_manifest.json` (`cli.py:150`); `validate-config` and
`registry verify` write nothing. §16.1's "every command MUST write a
machine-readable manifest" is therefore unmet, and is open as `D-057`.

**Why it mattered.** This is a *ticked* stage's `Produces` line, and the sentence
after it reads "Later stages may assume …". A completed stage was granting later
stages permission to assume an artifact that does not exist. Found by the
2026-09-09 system review's §2.3 (unnumbered MUSTs) and re-verified at HEAD.

**Note for whoever closes `D-057`.** A "recorded decline" was considered and
rejected at `specs/deferred_items.md` (`D-057`'s body): the roadmap's own
`Produces` line foreclosed it by promising the manifests.
