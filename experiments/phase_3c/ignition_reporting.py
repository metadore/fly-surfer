"""P3-T3.1: provisional ignition reporting for ablation results.

The legacy ``ignition.ignited`` field written by ``feature_ablation`` is an
activity-detection flag: it is true whenever at least one spike occurs outside
the fixed reference set R. That flag cannot distinguish a handful of late
outside-R spikes from population-scale recurrent ignition.

This module adds a separate, strictly additive classification. It never edits
the raw P3-T3 payload or any historical field. The three tiers are:

* ``none`` -- zero spikes outside R (definitional, not a threshold).
* ``sparse`` -- any outside-R spikes that are not population-scale by the
  provisional criterion below.
* ``population_scale`` -- population-scale recurrent ignition by the
  provisional criterion below.

The population-scale criterion is relational and post-hoc because no
preregistered absolute ignition threshold exists. It compares measured
quantities inside one condition:

1. the outside-R partition recruits more neurons than the entire fixed
   reference set R (``outside_reference.active_neurons > n_reference_neurons``);
2. the outside-R partition fires at a rate at least equal to the reference
   partition's rate (``outside_reference.firing_rate_hz >= reference.firing_rate_hz``).

Both must hold. The classification is labelled ``provisional`` and the raw
measurements are always reported so consumers can apply their own criterion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = (
    PROJECT_ROOT / "experiments" / "phase_3c" / "results" / "p3_t3_ablation.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "phase_3c"
    / "results"
    / "p3_t3_1_ignition_classification.json"
)

PHASE = "P3-T3.1"
VERSION = "p3-t3.1-ignition-reporting-v1"

REGIME_NONE = "none"
REGIME_SPARSE = "sparse"
REGIME_POPULATION = "population_scale"

LEGACY_FIELD = "ignition.ignited"
LEGACY_MEANING = (
    "legacy activity detection: true if at least one spike occurred outside "
    "the fixed reference set R; not a population-scale ignition criterion"
)

POPULATION_CRITERION = (
    "provisional relational criterion: outside-R active neurons exceed the "
    "size of the entire fixed reference set R AND the outside-R firing rate "
    "is at least the reference-partition firing rate. No preregistered "
    "absolute threshold exists, so this label is provisional, not a "
    "preregistered definition."
)


def _partition_measurements(condition: dict) -> dict:
    partitions = condition["partitions"]
    outside = partitions["outside_reference"]
    reference = partitions["reference"]
    total = partitions["total"]
    activity = condition["simulation"]["activity"]
    n_neurons = int(activity["n_neurons"])
    outside_spikes = int(outside["spikes"])
    outside_active = int(outside["active_neurons"])
    bins = list(outside.get("bins") or [])
    first = outside.get("first_spike_ms")
    last = outside.get("last_spike_ms")
    return {
        "outside_reference_spikes": outside_spikes,
        "outside_reference_active_neurons": outside_active,
        "outside_reference_rate_hz": float(outside["firing_rate_hz"]),
        "outside_reference_spike_fraction_of_total": (
            outside_spikes / int(total["spikes"]) if int(total["spikes"]) else 0.0
        ),
        "outside_reference_active_fraction_of_graph": (
            outside_active / n_neurons if n_neurons else 0.0
        ),
        "outside_reference_spikes_per_active_neuron": (
            outside_spikes / outside_active if outside_active else 0.0
        ),
        "outside_reference_first_spike_ms": first,
        "outside_reference_last_spike_ms": last,
        "outside_reference_span_ms": (
            float(last) - float(first) if first is not None and last is not None else 0.0
        ),
        "outside_reference_bins_occupied": sum(1 for value in bins if value > 0),
        "outside_reference_n_bins": len(bins),
        "reference_active_neurons": int(reference["active_neurons"]),
        "reference_rate_hz": float(reference["firing_rate_hz"]),
        "n_reference_neurons": int(condition["n_reference_neurons"]),
        "n_graph_neurons": n_neurons,
        "population_rate_peak_hz": float(activity["population_rate_peak_hz"]),
        "total_spikes": int(total["spikes"]),
    }


def classify_condition(condition: dict) -> dict:
    """Return the additive P3-T3.1 classification for one condition.

    The input mapping is read only; no key is added or modified.
    """
    measurements = _partition_measurements(condition)
    outside_spikes = measurements["outside_reference_spikes"]
    recruitment = (
        measurements["outside_reference_active_neurons"]
        > measurements["n_reference_neurons"]
    )
    rate_match = (
        measurements["outside_reference_rate_hz"]
        >= measurements["reference_rate_hz"]
    )
    if outside_spikes == 0:
        regime = REGIME_NONE
        status = "definitional"
    else:
        regime = (
            REGIME_POPULATION if recruitment and rate_match else REGIME_SPARSE
        )
        status = "provisional"
    legacy = condition.get("ignition", {})
    legacy_value = legacy.get("ignited")
    return {
        "condition": condition.get("condition"),
        "removed_feature": condition.get("removed_feature"),
        "activity_detected_outside_reference": outside_spikes > 0,
        "activity_regime": regime,
        "activity_regime_status": status,
        "population_scale_basis": {
            "outside_active_exceeds_reference_population": recruitment,
            "outside_rate_at_least_reference_rate": rate_match,
        },
        "population_scale_criterion": POPULATION_CRITERION,
        "legacy_activity_detection": {
            "field": LEGACY_FIELD,
            "value": legacy_value,
            "meaning": LEGACY_MEANING,
            "consistent_with_measurement": (
                legacy_value is not None
                and bool(legacy_value) == (outside_spikes > 0)
            ),
        },
        "measurements": measurements,
    }


def build_classification_report(source_path: Path = DEFAULT_SOURCE) -> dict:
    raw = source_path.read_bytes()
    payload = json.loads(raw)
    conditions = payload["conditions"]
    classified = {
        name: classify_condition(condition)
        for name, condition in conditions.items()
    }
    counts = {REGIME_NONE: 0, REGIME_SPARSE: 0, REGIME_POPULATION: 0}
    for item in classified.values():
        counts[item["activity_regime"]] += 1
    return {
        "phase": PHASE,
        "version": VERSION,
        "description": (
            "Additive provisional ignition classification for the archived "
            "P3-T3 leave-one-feature-out ablation. The source payload is "
            "read only and its bytes are hashed here."
        ),
        "source": {
            "path": str(source_path.relative_to(PROJECT_ROOT)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "phase": payload.get("phase"),
            "version": payload.get("version"),
            "verdict": payload.get("verdict"),
            "generated_at_utc": payload.get("generated_at_utc"),
            "unmodified": True,
        },
        "classification": {
            "tiers": [REGIME_NONE, REGIME_SPARSE, REGIME_POPULATION],
            "population_scale_criterion": POPULATION_CRITERION,
            "status": (
                "provisional: no preregistered absolute ignition threshold "
                "exists in the Phase 3 protocol"
            ),
        },
        "legacy_field_note": (
            "The historical field ignition.ignited is preserved unchanged in "
            "the source payload. It means 'at least one outside-R spike' "
            "(activity detection) and must not be read as population-scale "
            "ignition."
        ),
        "counts": counts,
        "conditions": classified,
        "limitations": [
            "The population-scale tier is a provisional post-hoc criterion, "
            "not a preregistered definition.",
            "The criterion uses only measured quantities and the fixed size of "
            "R; no absolute spike-count or rate threshold is asserted.",
            "A 'sparse' label covers all outside-R activity below the "
            "population-scale criterion and does not imply the activity is "
            "biologically negligible or uninfluential.",
            "The classification does not identify a mechanism, does not "
            "establish sensory routing and does not make any behavioural or "
            "perception claim.",
        ],
    }


def write_report(payload: dict, output: Path, *, overwrite: bool = False) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(
            f"{output} already exists; pass --overwrite to replace it"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="P3-T3.1 additive provisional ignition classification."
    )
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    report = build_classification_report(Path(args.source))
    write_report(report, Path(args.output), overwrite=args.overwrite)
    counts = report["counts"]
    print(
        f"wrote {args.output} | none={counts[REGIME_NONE]} "
        f"sparse={counts[REGIME_SPARSE]} "
        f"population_scale={counts[REGIME_POPULATION]}"
    )
    for name, item in report["conditions"].items():
        print(
            f"  {name:22s} regime={item['activity_regime']:16s} "
            f"outR_spikes={item['measurements']['outside_reference_spikes']:>9d} "
            f"outR_active={item['measurements']['outside_reference_active_neurons']:>6d} "
            f"legacy_ignited={item['legacy_activity_detection']['value']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
