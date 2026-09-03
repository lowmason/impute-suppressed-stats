# Deferred items

Unticked items are the deferred-work backlog; `/deferred` owns triage.
Live roadmap stages (`specs/*-roadmap.md`) are out of scope here — the
roadmap is its own backlog.

## logging-employment-spec-roadmap derivation — 2026-09-03

- [ ] **SRC-OTH-005 — BEA detailed state-industry employment bridge.**
      `specs/logging-employment-spec.md` §8.5 SRC-OTH-005 requires BEA detailed
      employment to be treated as optional historical input and bridged
      explicitly (§5.3, §11.11 BEA row). Deferred rather than staged because
      BEA discontinued the detailed state industry employment tables
      `SAEMP25` and `SAEMP27` on 2024-09-27, so there is no current table to
      bridge; the concept also differs from the estimand (BEA counts
      full- and part-time jobs including self-employment, against §3.2's
      private QCEW-covered wage-and-salary jobs), which §2.2's BEA row
      already forbids forcing into agreement. The spec ships
      `bea.enabled: false` in Appendix A and Rollout D6 records the scope
      decision. Revisit only if BEA republishes detailed state-industry
      employment, or if an archived vintage is wanted as a §13.9 sensitivity
      arm — in which case the bridge needs the §8.6 fields and explicit
      source-vintage metadata, not a column rename.
