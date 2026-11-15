"""P3-T12 analysis: compact descriptive summary of the characterization payload.

Reads ``p3_t12_network_characterization.json`` and writes
``p3_t12_analysis_summary.json`` plus plain-text tables. Every number is a
descriptive measurement of a deterministic run; there are no tests, p-values
or additive decompositions.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE = "P3-T12-analysis"
VERSION = "p3-t12-analysis-v1"
DEFAULT_INPUT = (
    PROJECT_ROOT / "experiments/phase_3c/results/p3_t12_network_characterization.json"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments/phase_3c/results/p3_t12_analysis_summary.json"

PARTITIONS = ("total", "reference", "outside_reference", "active", "outside_active")


def _time_to_fraction(item: dict, fraction: float) -> float | None:
    """First bin time at which cumulative active reaches ``fraction`` of final."""
    cumulative = item["recruitment"]["cumulative_active_fraction"]
    if not cumulative:
        return None
    target = cumulative[-1] * fraction
    edges = item["binned_activity"]["edges_ms"]
    for index, value in enumerate(cumulative):
        if value >= target:
            return round(float(edges[index + 1]), 4)
    return None


def _cascade_plateau(item: dict) -> dict:
    ratios = item["propagation"]["outside_active_cascade_ratio_by_bin"]
    occupied = [value for value in ratios if value > 0.0]
    tail = occupied[-max(1, len(ratios) // 5):] if occupied else []
    return {
        "first_bin_ratio": ratios[0] if ratios else None,
        "peak_ratio": max(ratios) if ratios else None,
        "plateau_median_ratio_last_20_percent": (
            round(float(statistics.median(tail)), 6) if tail else None
        ),
    }


def _final_second_per_100ms(item: dict) -> dict:
    bins = item["binned_activity"]["total"]
    window = bins[-100:]
    groups = [
        int(sum(window[start:start + 10]))
        for start in range(0, len(window), 10)
    ]
    return {
        "window_ms": len(window) * int(item["binned_activity"]["bin_ms"]),
        "spikes_per_100ms": groups,
    }


def summarize_condition(name: str, item: dict) -> dict:
    simulation = item["simulation"]
    diagnostics = simulation["diagnostics_stepwise"]
    distribution = item["firing_rate_distribution"]
    classification = item["ignition_classification"]
    partitions = item["partitions"]
    return {
        "duration_ms": item["duration_ms"],
        "n_steps": item["n_steps"],
        "frame_source": item["frame_source"],
        "n_active_features": item["n_active_features"],
        "removed_feature": item["removed_feature"],
        "ignition": {
            "regime": classification["activity_regime"],
            "status": classification["activity_regime_status"],
            "legacy_ignited": classification["legacy_activity_detection"]["value"],
            "first_spike_ms": partitions["total"]["first_spike_ms"],
            "first_outside_reference_ms": partitions["outside_reference"][
                "first_spike_ms"
            ],
            "first_outside_active_ms": partitions["outside_active"]["first_spike_ms"],
            "delay_active_to_outside_active_ms": (
                round(
                    float(partitions["outside_active"]["first_spike_ms"])
                    - float(partitions["active"]["first_spike_ms"]),
                    4,
                )
                if partitions["active"]["first_spike_ms"] is not None
                and partitions["outside_active"]["first_spike_ms"] is not None
                else None
            ),
        },
        "spikes_total": simulation["spikes_total"],
        "partitions": {
            key: {
                "n_neurons": partitions[key]["n_neurons"],
                "spikes": partitions[key]["spikes"],
                "active_neurons": partitions[key]["active_neurons"],
                "firing_rate_hz": partitions[key]["firing_rate_hz"],
                "first_spike_ms": partitions[key]["first_spike_ms"],
                "last_spike_ms": partitions[key]["last_spike_ms"],
            }
            for key in PARTITIONS
        },
        "active_fraction_of_graph": item["activity_by_partition"]["active_fraction"],
        "rates_hz": {
            "population_mean": simulation["activity"]["mean_rate_hz"],
            "population_peak": simulation["activity"]["population_rate_peak_hz"],
            "active_mean": distribution["active_neurons"]["mean_hz"],
            "active_percentiles": distribution["active_neurons"]["percentiles_hz"],
            "all_percentiles": distribution["all_neurons"]["percentiles_hz"],
            "top_one_percent_spike_share": distribution[
                "top_one_percent_spike_share"
            ],
        },
        "rails": {
            "min_membrane_mv": diagnostics["min_membrane_mv"],
            "max_membrane_mv": diagnostics["max_membrane_mv"],
            "at_floor_fraction": diagnostics["at_floor_fraction"],
            "near_threshold_fraction": diagnostics["near_threshold_fraction"],
            "refractory_fraction": diagnostics["refractory_fraction"],
            "finite_state": diagnostics["finite_state"],
        },
        "recruitment": {
            "checkpoints_ms": item["recruitment"]["checkpoints_fraction_to_time_ms"],
            "time_to_25_percent_of_final_ms": _time_to_fraction(item, 0.25),
            "time_to_50_percent_of_final_ms": _time_to_fraction(item, 0.50),
            "time_to_90_percent_of_final_ms": _time_to_fraction(item, 0.90),
            "peak_new_active_per_bin": max(
                item["recruitment"]["new_active_neurons_per_bin"], default=0
            ),
        },
        "persistence": {
            "bins": item["persistence"]["bins"],
            "fraction_bins_outside_active": item["persistence"][
                "fraction_bins_outside_active"
            ],
            "longest_outside_active_run_ms": item["persistence"][
                "longest_outside_active_run_ms"
            ],
            "longest_gap_ms_outside_active": item["persistence"]["longest_gap_ms"][
                "outside_active"
            ],
            "tail_window_ms": item["persistence"]["tail_window_ms"],
            "tail_mean_rate_hz": item["persistence"]["tail_mean_rate_hz"],
            "tail_active_neurons": item["persistence"]["tail_active_neurons"],
            "final_second": _final_second_per_100ms(item),
        },
        "propagation": {
            "transmissions_per_spike": item["propagation"].get(
                "transmissions_per_spike"
            ),
            **_cascade_plateau(item),
        },
        "topology": (
            {
                "definition": item["topology"]["definition"],
                "source_partition": item["topology"]["source_partition"],
                "buckets": item["topology"]["buckets"],
            }
            if item["topology"]
            else None
        ),
        "post_drive_window": item["post_drive_window"],
        "checks": item["condition_checks"],
        "checks_not_evaluated": item["condition_checks_not_evaluated"],
        "repeats_identical": item["reproducibility"]["identical"],
        "spike_capacity_exceeded": item["spike_capacity_exceeded"],
    }


def summarize(payload: dict) -> dict:
    return {
        "phase": PHASE,
        "version": VERSION,
        "source": {
            "path": "experiments/phase_3c/results/p3_t12_network_characterization.json",
            "verdict": payload["verdict"],
            "mode": payload["mode"],
            "generated_at_utc": payload["generated_at_utc"],
            "runtime_s": payload["runtime_s"],
        },
        "gates": {
            "equivalence": payload["equivalence"],
            "prefix_gate": payload["prefix_gate"],
            "invalidations": payload["invalidations"],
            "subprocess_reproducibility": {
                "identical": payload.get("subprocess_reproducibility", {}).get(
                    "identical"
                ),
                "conditions": {
                    name: {
                        "ran": value.get("ran"),
                        "identical": value.get("identical"),
                        "differences": value.get("differences"),
                    }
                    for name, value in payload.get("subprocess_reproducibility", {})
                    .get("conditions", {})
                    .items()
                },
            },
        },
        "classification": payload["classification"],
        "conditions": {
            name: summarize_condition(name, item)
            for name, item in payload["conditions"].items()
        },
    }


def print_tables(summary: dict) -> None:
    print("condition          regime            spikes        outside_R   active%  first  outR  at_floor%  refr%")
    for name, item in summary["conditions"].items():
        print(
            f"{name:18s} {item['ignition']['regime']:16s} "
            f"{item['spikes_total']:12d} "
            f"{item['partitions']['outside_reference']['spikes']:11d} "
            f"{100 * item['active_fraction_of_graph']:7.2f} "
            f"{str(item['ignition']['first_spike_ms']):>6s} "
            f"{str(item['ignition']['first_outside_reference_ms']):>6s} "
            f"{100 * item['rails']['at_floor_fraction']:9.2f} "
            f"{100 * item['rails']['refractory_fraction']:6.2f}"
        )
    print()
    print("condition          t25%   t50%   t90%   peak_new/bin  tail_hz  longest_run_ms  longest_gap_ms")
    for name, item in summary["conditions"].items():
        print(
            f"{name:18s} {str(item['recruitment']['time_to_25_percent_of_final_ms']):>6s} "
            f"{str(item['recruitment']['time_to_50_percent_of_final_ms']):>6s} "
            f"{str(item['recruitment']['time_to_90_percent_of_final_ms']):>6s} "
            f"{item['recruitment']['peak_new_active_per_bin']:12d} "
            f"{item['persistence']['tail_mean_rate_hz']:8.2f} "
            f"{item['persistence']['longest_outside_active_run_ms']:14.1f} "
            f"{item['persistence']['longest_gap_ms_outside_active']:14.1f}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P3-T12 descriptive analysis")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    source = Path(args.input)
    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise SystemExit(f"{output} exists; pass --overwrite")
    payload = json.loads(source.read_text(encoding="utf-8"))
    summary = summarize(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print_tables(summary)
    print(f"\nwrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
