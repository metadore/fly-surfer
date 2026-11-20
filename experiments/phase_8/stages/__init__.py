"""Execution-stage orchestration for Phase 8 (REV4 §10).

PROTOCOL STATUS
    Every stage in this package is a *stage harness*, not a result. Recorded
    owner decisions D1 (REV4 §12 / U1-U18, 2026-11-20) and D2 (the G3 deviation
    is not applicable to the exact Pilot 1 grid only, 2026-11-20) are
    recognised, but the campaign design is unresolved
    (``design.n_seeds_selected`` is null) and the G3 graph set still carries a
    recorded §9.3 memory-gate deviation. Only Pilot 1 — condition A, seeds
    9001-9003, three episodes each, no randomized graph — may pass B7. Every
    other execute entry point calls the unchanged gate first and raises;
    planning, readiness and reporting helpers are read-only.

Stages
    ``pilot1``      10.3  A viability pilot plan and gated runner
    ``training``    10.5/10.9  training-plan orchestration and gated runner
    ``composition`` 10.10 production composition root for the campaign
    ``pilot2``      10.8  paired-dispersion pilot plan, readiness and evaluator
    ``information`` §5.4  descriptive/exploratory information adapter
    ``report``      10.12 final-report and freeze checks

The package contains the production Pilot 1 episode runner
(``pilot1_runner``), which builds condition A on the biological substrate and
drives the existing controlled environment. It is reachable only through the
stage gate, which applies the D2 exemption to the exact Pilot 1 grid and to
nothing else. The synthetic-fixture driver remains confined outside the real
results root and labels every artefact ``synthetic_fixture``.
"""

from __future__ import annotations

__all__: list[str] = []
