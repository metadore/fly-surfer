"""Phase 4H.4 analysis: reconcile the 27-run matrix, aggregate all conditions
and measure downstream propagation with hash-verified replays.

The executed result file stores whole-population endpoints and the
stimulated/non-stimulated split. It does not store per-neuron membrane
potentials or synaptic currents, so this script replays every executed run with
a read-only wrapper around ``LIFPopulation.step``. Each replay is accepted only
if its spike and decision hashes equal the stored record; a mismatch aborts the
analysis rather than producing inconsistent diagnostics.

The replay wrapper changes no Phase 4G code, no graph artifact and no stored
result. It accumulates per-neuron maxima in memory and writes a new diagnostics
checkpoint. Classification (stimulated, first hop, second hop, descending,
motor) is anatomical and structural; activity in those groups is measured
separately.

Writes:
  experiments/results/phase_4h/sensory_roundtrip.diagnostics.v2.checkpoint.jsonl
  reports/PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json

Usage:
  python -m experiments.phase_4h.analyse_sensory_roundtrip
  python -m experiments.phase_4h.analyse_sensory_roundtrip --no-replay
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_sensory_adapter import (  # noqa: E402
    BancSensoryMapping,
    ConstantChargeDrive,
    event_metadata_digest,
    shuffle_feature_identities,
    temporally_shuffle_events,
)
from brain.banc_simulation_adapter import BancActivityAdapter  # noqa: E402
from brain.banc_simulator import BancSimulator  # noqa: E402
from experiments.phase_4h import common  # noqa: E402
from experiments.phase_4h import run_sensory_roundtrip as runner  # noqa: E402
from motor.motor_decoder import MotorDecoder  # noqa: E402
from sensory.population_encoder import build_encoders  # noqa: E402

RESULT = common.RESULTS / "sensory_roundtrip.json"
CHECKPOINT = common.RESULTS / "sensory_roundtrip.checkpoint.jsonl"
DIAGNOSTICS_CHECKPOINT = (
    common.RESULTS / "sensory_roundtrip.diagnostics.v2.checkpoint.jsonl"
)
OUTPUT = PROJECT_ROOT / "reports" / "PHASE_4H4_SENSORY_TO_BANC_ROUND_TRIP.json"

CONDITIONS = runner.CONDITIONS
REPEATS = runner.REPEATS
STREAMS = runner.STREAMS
REPEAT_LABELS = tuple(f"{name}_repeat" for name in REPEATS)

EXPECTED_KEYS = tuple(
    (stream, condition) for stream in STREAMS for condition in CONDITIONS
) + tuple(
    (stream, f"{condition}_repeat") for stream in STREAMS for condition in REPEATS
)

PRIMARY_ENDPOINTS = (
    "total_spikes",
    "stimulated_spikes",
    "non_stimulated_spikes",
    "motor_spikes",
    "event_locked_downstream_spikes",
    "alignment_best_r",
    "decoded_state_counts",
)

EXPLORATORY_ENDPOINTS = (
    "active_neurons",
    "first_hop_spikes",
    "second_hop_spikes",
    "descending_spikes",
    "ascending_spikes",
    "event_locked_stimulated_spikes",
    "event_locked_stimulated_latency_median_ms",
    "first_hop_receiving_neurons",
    "first_hop_max_synaptic_current_pa",
    "first_hop_max_membrane_mv",
    "first_hop_closest_deficit_mv",
    "non_stimulated_non_motor_closest_deficit_mv",
    "motor_closest_deficit_mv",
)

COMPARISONS = (
    ("B_actual", "A_no_events"),
    ("B_actual", "C_temporal_shuffle"),
    ("B_actual", "D_feature_identity_shuffle"),
    ("B_actual", "E_random_matched_mapping"),
    ("B_actual", "F_constant_matched_charge"),
    ("B_actual", "G_background_noise"),
)

GROUP_ORDER = (
    "stimulated",
    "first_hop",
    "second_hop",
    "descending",
    "ascending",
    "motor",
    "non_stimulated_non_motor",
    "non_stimulated",
    "sensory",
    "vnc_intrinsic",
    "central_brain_intrinsic",
    "optic_lobe_intrinsic",
    "visual_projection",
    "unannotated",
    "left_action",
    "right_action",
    "jump_action",
)


# -- loading and reconciliation ---------------------------------------------


def load_result(path: Path = RESULT) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"missing 4H.4 result file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def expected_seed(stream: str, condition: str) -> int:
    base = condition.replace("_repeat", "")
    return common.SEED_ROOT + 400000 + 100 * STREAMS.index(stream) + CONDITIONS.index(
        base
    )


def reconcile(
    runs: list[dict],
    checkpoint_records: list[dict] | None = None,
    *,
    expected_keys: tuple[tuple[str, str], ...] = EXPECTED_KEYS,
) -> dict:
    """Compare the stored run list with the preregistered 27-run matrix."""
    by_key: dict[tuple[str, str], dict] = {}
    duplicates = []
    unexpected = []
    for record in runs:
        key = (record.get("stream"), record.get("condition"))
        if key in by_key:
            duplicates.append(list(key))
        by_key[key] = record
        if key not in expected_keys:
            unexpected.append(list(key))
    missing = [list(key) for key in expected_keys if key not in by_key]

    seed_mismatches = []
    metadata_mismatches = []
    duration_mismatches = []
    for key in expected_keys:
        record = by_key.get(key)
        if record is None:
            continue
        want = expected_seed(*key)
        if int(record["seed"]) != want:
            seed_mismatches.append(
                {"key": list(key), "stored": int(record["seed"]), "expected": want}
            )
        if key[1] in ("C_temporal_shuffle", "D_feature_identity_shuffle"):
            if record.get("events_metadata_sha256") in (None, ""):
                metadata_mismatches.append(
                    {"key": list(key), "reason": "missing event metadata hash"}
                )
        if abs(float(record.get("duration_ms", -1.0)) - 3300.5) > 1e-6:
            duration_mismatches.append(
                {"key": list(key), "duration_ms": record.get("duration_ms")}
            )

    repeat_checks = {}
    for stream in STREAMS:
        for base in REPEATS:
            if (stream, f"{base}_repeat") not in expected_keys:
                continue
            first = by_key.get((stream, base))
            repeat = by_key.get((stream, f"{base}_repeat"))
            repeat_checks[f"{stream}:{base}"] = {
                "complete": first is not None and repeat is not None,
                "seed_equal": bool(
                    first is not None
                    and repeat is not None
                    and int(first["seed"]) == int(repeat["seed"])
                ),
                "spike_hash_equal": bool(
                    first is not None
                    and repeat is not None
                    and first["hashes"]["spike_sha256"]
                    == repeat["hashes"]["spike_sha256"]
                ),
                "decision_hash_equal": bool(
                    first is not None
                    and repeat is not None
                    and first["hashes"]["decision_sha256"]
                    == repeat["hashes"]["decision_sha256"]
                ),
                "drive_hash_equal": bool(
                    first is not None
                    and repeat is not None
                    and first["hashes"]["drive_sha256"]
                    == repeat["hashes"]["drive_sha256"]
                ),
                "metrics_equal": bool(
                    first is not None
                    and repeat is not None
                    and first["metrics"]["n_spikes"] == repeat["metrics"]["n_spikes"]
                    and first["metrics"]["motor"]["spikes"]
                    == repeat["metrics"]["motor"]["spikes"]
                ),
            }

    checkpoint_summary = None
    if checkpoint_records is not None:
        counts: dict[tuple[str, str], int] = {}
        for record in checkpoint_records:
            key = (record.get("stream"), record.get("condition"))
            counts[key] = counts.get(key, 0) + 1
        checkpoint_summary = {
            "records": len(checkpoint_records),
            "unique_keys": len(counts),
            "duplicate_keys": [
                list(key) for key, count in counts.items() if count > 1
            ],
            "missing_from_checkpoint": [
                list(key) for key in expected_keys if key not in counts
            ],
            "unexpected_in_checkpoint": [
                list(key) for key in counts if key not in expected_keys
            ],
        }

    complete = (
        not missing
        and not duplicates
        and not unexpected
        and not seed_mismatches
        and not metadata_mismatches
        and not duration_mismatches
        and all(item["complete"] for item in repeat_checks.values())
    )
    return {
        "expected_runs": len(expected_keys),
        "stored_runs": len(runs),
        "unique_runs": len(by_key),
        "missing": missing,
        "duplicates": duplicates,
        "unexpected": unexpected,
        "seed_mismatches": seed_mismatches,
        "event_metadata_mismatches": metadata_mismatches,
        "duration_mismatches": duration_mismatches,
        "repeat_checks": repeat_checks,
        "checkpoint": checkpoint_summary,
        "complete": bool(complete),
    }


# -- configuration verification ---------------------------------------------


def signed_outgoing(
    indices: np.ndarray, graph, exc_weight: np.ndarray, inh_weight: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    indices = np.asarray(indices, dtype=np.int64)
    if indices.size == 0:
        empty = np.empty(0, dtype=np.int64)
        return empty, np.empty(0, dtype=bool)
    starts = np.asarray(graph.out_indptr, dtype=np.int64)[indices]
    ends = np.asarray(graph.out_indptr, dtype=np.int64)[indices + 1]
    counts = ends - starts
    prefix = np.cumsum(counts) - counts
    edge_index = np.repeat(starts - prefix, counts) + np.arange(
        int(counts.sum()), dtype=np.int64
    )
    signed = (exc_weight[edge_index] > 0) | (inh_weight[edge_index] > 0)
    return edge_index, signed


def verify_configuration(world, mapping, config: dict, result: dict) -> dict:
    nodes = world.nodes
    graph = world.graph
    exc = np.asarray(world.policy.edge_exc_weight, dtype=np.float64)
    inh = np.asarray(world.policy.edge_inh_weight, dtype=np.float64)
    dst = np.asarray(graph.edge_dst, dtype=np.int64)
    stimulated = np.asarray(mapping.stimulated_indices(), dtype=np.int64)
    edge_index, signed = signed_outgoing(stimulated, graph, exc, inh)
    signed_targets = np.unique(dst[edge_index[signed]])
    motor = np.asarray(world.populations.motor_mask, dtype=bool)

    graph_sha = common.sha256_file(common.GRAPH_T5)
    nodes_sha = common.sha256_file(common.NODES_PATH)
    policy_sha = common.sha256_file(common.POLICY_CONFIG)
    decoder_sha = common.sha256_file(common.DECODER_CONFIG)
    neuron_sha = common.sha256_file(common.NEURON_CONFIG)
    mapping_sha = common.sha256_file(runner.MAPPING_CONFIG)
    protocol_sha = common.sha256_file(
        PROJECT_ROOT / "reports" / "PHASE_4H_EXPERIMENTAL_PROTOCOL.md"
    )

    checks = []

    def check(name, expected, observed, pass_value=None):
        passed = bool(pass_value) if pass_value is not None else expected == observed
        checks.append(
            {
                "check": name,
                "expected": expected,
                "observed": observed,
                "pass": passed,
            }
        )
        return passed

    check("protocol_sha256", protocol_sha, result.get("protocol_sha256"))
    check(
        "graph_artifact_sha256",
        graph_sha,
        result.get("world", {}).get("graph", {}).get("sha256"),
    )
    check(
        "node_table_sha256",
        nodes_sha,
        result.get("world", {}).get("node_table", {}).get("sha256"),
    )
    check(
        "policy_config_sha256",
        policy_sha,
        world.signature["inputs"]["policy_config_sha256"],
    )
    check(
        "decoder_config_sha256",
        decoder_sha,
        world.signature["inputs"]["decoder_config_sha256"],
    )
    check(
        "neuron_config_sha256",
        neuron_sha,
        world.signature["inputs"]["neuron_config_sha256"],
    )
    check("mapping_config_sha256", mapping_sha, result.get("config", {}).get("sha256"))
    check("world_signature_sha256", world.signature["config_sha256"], result["world"].get("config_sha256"))
    check("graph_threshold", 5, int(graph.threshold))
    check("n_nodes", 172433, int(graph.n_nodes))
    check("n_edges", 1535710, int(graph.n_edges))
    check("n_synapses", 18552546, int(graph.n_synapses))
    check("stimulated_neurons", 232, int(stimulated.size))
    check("motor_overlap", 0, int(motor[stimulated].sum()))
    check("signed_outgoing_edges", 662, int(signed.sum()))
    check("signed_outgoing_targets", 608, int(signed_targets.size))
    check("signed_outgoing_inhibitory_weight_pa", 0.0, float(inh[edge_index[signed]].sum()))
    check("signed_outgoing_targets_motor", 0, int(motor[signed_targets].sum()))
    feature_currents = {
        feature: float(payload.get("current_pa", 0.0))
        for feature, payload in config["features"].items()
    }
    check(
        "feature_currents_200_pa",
        {name: 200.0 for name in feature_currents},
        feature_currents,
    )
    check("pulse_decay_ms", 150.0, float(config["drive"]["decay_ms"]))
    check("drive_dt_ms", 0.5, float(config["drive"]["dt_ms"]))
    check("drive_duration_ms", 3300.5, float(config["drive"]["duration_ms"]))
    check("background_g_pa", 50.0, float(config["drive"]["background_pa_condition_g"]))
    check("noise_g_pa", 50.0, float(config["drive"]["noise_std_pa_condition_g"]))
    check("mapping_seed", 20261109, int(config["mapping"]["seed"]))
    check(
        "sign_policy_verified_only",
        "verified-only",
        result.get("world", {}).get("policy", {}).get("coverage", {}).get("declared_policy"),
    )
    check(
        "predicted_fallback",
        False,
        bool(
            result.get("world", {})
            .get("policy", {})
            .get("sign_policy", {})
            .get("predicted_fallback")
        ),
    )
    weight_policy = result.get("world", {}).get("policy", {}).get("weight_policy", {})
    check("weight_transform", "power", weight_policy.get("transform"))
    check("weight_exponent", 0.75, float(weight_policy.get("exponent", -1)))
    check("weight_scale_pa", 5.0, float(weight_policy.get("scale_pa", -1)))
    check("weight_cap_pa", 300.0, float(weight_policy.get("cap_pa", -1)))
    decoder = result.get("world", {}).get("decoder", {}).get("config", {})
    check("decoder_window_ms", 50.0, float(decoder.get("window_ms", -1)))
    check("decoder_step_ms", 50.0, float(decoder.get("step_ms", -1)))
    check("decoder_activation", 0.2, float(decoder.get("activation_threshold", -1)))
    check("decoder_release", 0.1, float(decoder.get("release_threshold", -1)))
    check("decoder_min_spikes", 5, int(decoder.get("min_spikes", -1)))
    check("decoder_min_active", 3, int(decoder.get("min_active_neurons", -1)))
    check("decoder_priority", ["LEFT", "RIGHT", "JUMP"], decoder.get("priority"))
    neuron = result.get("world", {}).get("neuron", {})
    check("neuron_threshold_mv", -50.0, float(neuron.get("threshold_mv", 0.0)))
    check("neuron_resting_mv", -65.0, float(neuron.get("resting_potential_mv", 0.0)))
    check("neuron_capacitance_pf", 200.0, float(neuron.get("capacitance_pf", 0.0)))
    check("neuron_leak_ns", 10.0, float(neuron.get("leak_conductance_ns", 0.0)))

    populations = result.get("mapping", {}).get("annotation", {}).get("populations", {})
    observed_sizes = {
        name: int(payload.get("selected_size", -1))
        for name, payload in populations.items()
    }
    expected_sizes = {
        "train_lane": 48,
        "obstacle_lane": 48,
        "train_present": 24,
        "train_distance": 32,
        "obstacle_present": 24,
        "obstacle_distance": 32,
        "obstacle_type": 24,
    }
    check("mapped_population_sizes", expected_sizes, observed_sizes)
    check("mapped_population_total", 232, int(sum(observed_sizes.values())))
    check(
        "mapping_motor_neurons_excluded",
        805,
        int(
            result.get("mapping", {})
            .get("annotation", {})
            .get("motor_neurons_excluded", -1)
        ),
    )
    check(
        "mapping_motor_overlap",
        0,
        int(result.get("mapping", {}).get("annotation", {}).get("motor_overlap", -1)),
    )
    check(
        "mapping_action_overlap",
        0,
        int(result.get("mapping", {}).get("annotation", {}).get("action_overlap", -1)),
    )

    return {
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": int(sum(1 for item in checks if not item["pass"])),
        "pass": all(item["pass"] for item in checks),
        "hashes": {
            "protocol_sha256": protocol_sha,
            "graph_sha256": graph_sha,
            "nodes_sha256": nodes_sha,
            "policy_config_sha256": policy_sha,
            "decoder_config_sha256": decoder_sha,
            "neuron_config_sha256": neuron_sha,
            "mapping_config_sha256": mapping_sha,
            "world_signature_sha256": world.signature["config_sha256"],
            "mapping_selection_sha256": result.get("mapping", {})
            .get("annotation", {})
            .get("selection_sha256"),
        },
        "wiring": {
            "stimulated_neurons": int(stimulated.size),
            "outgoing_edges_all": int(
                np.diff(graph.out_indptr)[stimulated].sum()
            ),
            "outgoing_signed_edges": int(signed.sum()),
            "signed_targets": int(signed_targets.size),
            "signed_excitatory_weight_pa": round(
                float(exc[edge_index[signed]].sum()), 6
            ),
            "signed_inhibitory_weight_pa": round(
                float(inh[edge_index[signed]].sum()), 6
            ),
            "signed_targets_motor": int(motor[signed_targets].sum()),
        },
    }


# -- condition tables --------------------------------------------------------


def record_condition_row(record: dict) -> dict:
    metrics = record["metrics"]
    return {
        "stream": record["stream"],
        "condition": record["condition"],
        "events_used": record["events_used"],
        "pulses_used": record["pulses_used"],
        "seed": int(record["seed"]),
        "duration_ms": float(record["duration_ms"]),
        "total_spikes": int(metrics["n_spikes"]),
        "stimulated_spikes": int(metrics["stimulated_spikes"]),
        "non_stimulated_spikes": int(metrics["non_stimulated_spikes"]),
        "active_neurons": int(metrics["active_neurons"]),
        "stimulated_active_neurons": int(metrics["stimulated_active_neurons"]),
        "non_stimulated_active_neurons": int(metrics["non_stimulated_active_neurons"]),
        "motor_spikes": int(metrics["motor"]["spikes"]),
        "motor_active_neurons": int(metrics["motor"]["active_neurons"]),
        "descending_spikes": None,
        "first_hop_spikes": None,
        "second_hop_spikes": None,
        "decoded_state_counts": metrics["decoded_state_counts"],
        "n_windows": int(metrics["n_windows"]),
        "jump_windows": int(metrics["jump_windows"]),
        "left_windows": int(metrics["left_windows"]),
        "right_windows": int(metrics["right_windows"]),
        "event_locked_downstream_spikes": int(
            record["event_locked"].get("total_spikes_in_window", 0)
        ),
        "events_with_zero_downstream_spikes": record["event_locked"].get(
            "events_with_zero_spikes"
        ),
        "events_total": record["event_locked"].get("n_events"),
        "alignment_best_r": (
            None
            if record["alignment"].get("best") is None
            else record["alignment"]["best"]["pearson_r"]
        ),
        "spike_time_min_ms": metrics.get("spike_time_min_ms"),
        "spike_time_max_ms": metrics.get("spike_time_max_ms"),
        "spike_sha256": record["hashes"]["spike_sha256"],
        "decision_sha256": record["hashes"]["decision_sha256"],
        "drive_sha256": record["hashes"]["drive_sha256"],
        "wall_time_s": record.get("wall_time_s"),
    }


def condition_tables(runs: list[dict]) -> dict:
    table: dict[str, dict[str, dict]] = {}
    for record in runs:
        if record["condition"].endswith("_repeat"):
            continue
        table.setdefault(record["stream"], {})[record["condition"]] = record_condition_row(
            record
        )
    return table


# -- replay diagnostics ------------------------------------------------------


def class_masks(world) -> dict[str, np.ndarray]:
    nodes = world.nodes
    sc = nodes["super_class"].fillna("").astype(str).to_numpy()
    motor = np.asarray(world.populations.motor_mask, dtype=bool)

    def mask_for(value: str) -> np.ndarray:
        return sc == value

    masks = {
        "motor": motor,
        "descending": mask_for("descending"),
        "ascending": mask_for("ascending"),
        "sensory": mask_for("sensory"),
        "vnc_intrinsic": mask_for("ventral_nerve_cord_intrinsic"),
        "central_brain_intrinsic": mask_for("central_brain_intrinsic"),
        "optic_lobe_intrinsic": mask_for("optic_lobe_intrinsic"),
        "visual_projection": mask_for("visual_projection"),
        "unannotated": sc == "",
    }
    for action in ("LEFT", "RIGHT", "JUMP"):
        masks[f"{action.lower()}_action"] = np.asarray(
            world.populations.mask(action), dtype=bool
        )
    return masks


def group_stats(
    mask: np.ndarray,
    spike_counts: np.ndarray,
    max_v: np.ndarray,
    max_syn: np.ndarray,
    threshold_mv: float,
    rest_mv: float,
    *,
    closest_lookup=None,
) -> dict:
    mask = np.asarray(mask, dtype=bool)
    n = int(mask.sum())
    if n == 0:
        return {"n": 0}
    spikes = spike_counts[mask]
    active = spikes > 0
    active_neurons = int(active.sum())
    total_spikes = int(spikes.sum())
    v = max_v[mask]
    current = max_syn[mask]
    receiving = current > 1e-9
    nonspiking = ~active
    deficits = threshold_mv - v[nonspiking]
    if deficits.size:
        closest = float(np.min(deficits))
        closest_index = int(np.flatnonzero(mask)[np.flatnonzero(nonspiking)[np.argmin(deficits)]])
    else:
        closest = 0.0
        closest_index = None
    payload = {
        "n": n,
        "spikes": total_spikes,
        "active_neurons": active_neurons,
        "active_fraction": round(active_neurons / n, 6),
        "receiving_neurons": int(receiving.sum()),
        "max_synaptic_current_pa": round(float(current.max()), 6),
        "p95_synaptic_current_pa": round(float(np.percentile(current, 95)), 6),
        "median_synaptic_current_pa": round(float(np.median(current)), 6),
        "max_membrane_mv": round(float(v.max()), 6),
        "max_depolarization_mv": round(float(v.max() - rest_mv), 6),
        "closest_deficit_mv": round(closest, 6),
        "n_within_1mv": int(np.count_nonzero(deficits <= 1.0)),
        "n_within_2mv": int(np.count_nonzero(deficits <= 2.0)),
        "n_within_5mv": int(np.count_nonzero(deficits <= 5.0)),
        "n_within_10mv": int(np.count_nonzero(deficits <= 10.0)),
        "threshold_crossings": total_spikes,
    }
    if closest_lookup is not None and closest_index is not None:
        payload["closest_neuron"] = closest_lookup(closest_index)
    return payload


def event_locked_stimulated(events, spike_times: np.ndarray, window_ms: float = 50.0) -> dict:
    times = np.sort(np.asarray(spike_times, dtype=np.float64))
    if not events:
        return {
            "n_events": 0,
            "window_ms": window_ms,
            "spikes_in_window": {"n": 0},
            "total_spikes_in_window": 0,
            "events_with_zero_spikes": 0,
            "latency_ms": {"n": 0},
            "n_events_without_spike": 0,
        }
    counts = []
    latencies = []
    for event in events:
        start = float(event["time_ms"])
        stop = start + window_ms
        counts.append(
            int(np.count_nonzero((times >= start) & (times < stop)))
        )
        position = int(np.searchsorted(times, start, side="left"))
        latencies.append(
            None
            if position >= times.size
            else float(times[position] - start)
        )
    present = [value for value in latencies if value is not None]
    return {
        "n_events": len(events),
        "window_ms": window_ms,
        "spikes_in_window": common.summary_stats(counts),
        "total_spikes_in_window": int(sum(counts)),
        "events_with_zero_spikes": int(sum(1 for value in counts if value == 0)),
        "latency_ms": common.summary_stats(present) if present else {"n": 0},
        "n_events_without_spike": len(events) - len(present),
        "mean_spikes_per_event": round(float(np.mean(counts)), 6),
    }


def replay_diagnostics(
    record: dict,
    world,
    real_mapping,
    random_mapping,
    encoders,
    drive: dict,
    current_pa: dict,
    stream: dict,
    class_mask: dict,
) -> dict:
    condition = record["condition"]
    base = condition.replace("_repeat", "")
    events = stream["events"]
    mapping = real_mapping
    events_used = []
    schedule = None
    background = float(record["background_pa"])
    noise = float(record["noise_std_pa"])
    duration_ms = float(record["duration_ms"])
    dt_ms = float(record["dt_ms"])
    if base == "B_actual":
        events_used = events
        schedule = runner.build_schedule(
            real_mapping,
            encoders,
            events_used,
            duration_ms=duration_ms,
            drive=drive,
            current_pa=current_pa,
        )
    elif base == "C_temporal_shuffle":
        events_used = temporally_shuffle_events(events, seed=int(record["seed"]))
        schedule = runner.build_schedule(
            real_mapping,
            encoders,
            events_used,
            duration_ms=duration_ms,
            drive=drive,
            current_pa=current_pa,
        )
    elif base == "D_feature_identity_shuffle":
        events_used = shuffle_feature_identities(events, seed=int(record["seed"]))
        schedule = runner.build_schedule(
            real_mapping,
            encoders,
            events_used,
            duration_ms=duration_ms,
            drive=drive,
            current_pa=current_pa,
        )
    elif base == "E_random_matched_mapping":
        mapping = random_mapping
        events_used = events
        schedule = runner.build_schedule(
            random_mapping,
            encoders,
            events_used,
            duration_ms=duration_ms,
            drive=drive,
            current_pa=current_pa,
        )
    elif base == "F_constant_matched_charge":
        reference = runner.build_schedule(
            real_mapping,
            encoders,
            events,
            duration_ms=duration_ms,
            drive=drive,
            current_pa=current_pa,
        )
        schedule = ConstantChargeDrive(
            real_mapping.stimulated_indices(),
            reference.total_charge_pa_ms(),
            duration_ms=duration_ms,
            dt_ms=dt_ms,
        )
    elif base == "A_no_events":
        events_used = []
    elif base == "G_background_noise":
        events_used = []
    else:
        raise ValueError(f"unknown condition {condition!r}")

    if event_metadata_digest(events_used) != record["events_metadata_sha256"]:
        raise RuntimeError(
            f"event metadata mismatch for {record['stream']} {condition}"
        )

    if schedule is not None:
        drive_hash = schedule.signature_sha256()
        if drive_hash != record["hashes"]["drive_sha256"]:
            raise RuntimeError(
                f"drive hash mismatch for {record['stream']} {condition}: "
                f"{drive_hash} != {record['hashes']['drive_sha256']}"
            )

    stimulated = np.asarray(mapping.stimulated_indices(), dtype=np.int64)
    exc = np.asarray(world.policy.edge_exc_weight, dtype=np.float64)
    inh = np.asarray(world.policy.edge_inh_weight, dtype=np.float64)
    dst = np.asarray(world.graph.edge_dst, dtype=np.int64)
    edge_index, signed = signed_outgoing(stimulated, world.graph, exc, inh)
    first_hop_all = np.unique(dst[edge_index[signed]])
    first_hop = np.setdiff1d(first_hop_all, stimulated)
    first_edge_index, first_signed = signed_outgoing(
        first_hop, world.graph, exc, inh
    )
    second_hop_all = np.unique(dst[first_edge_index[first_signed]])
    second_hop = np.setdiff1d(
        second_hop_all, np.union1d(stimulated, first_hop)
    )

    sim = BancSimulator(
        world.graph,
        world.policy,
        neuron_params=world.neuron_params,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        seed=int(record["seed"]),
        background_current_pa=background,
        noise_std_pa=noise,
        stimulation=None,
        input_schedule=schedule,
        max_recorded_spikes=runner.MAX_RECORDED_SPIKES,
    )
    n = world.n_nodes
    threshold_mv = float(world.neuron_params.threshold_mv)
    rest_mv = float(world.neuron_params.resting_potential_mv)
    max_v = np.full(n, -np.inf, dtype=np.float64)
    max_syn = np.full(n, -np.inf, dtype=np.float32)
    max_input_all = -np.inf
    max_input_stim = -np.inf

    original_step = sim.neurons.step

    def step(current):
        nonlocal max_input_all, max_input_stim
        max_input_all = max(max_input_all, float(np.max(current)))
        if stimulated.size:
            max_input_stim = max(
                max_input_stim, float(np.max(current[stimulated]))
            )
        spikes = original_step(current)
        np.maximum(max_v, sim.neurons._V, out=max_v)
        if spikes.size:
            max_v[spikes] = threshold_mv
        np.maximum(max_syn, sim.synapses.synaptic_current_pa, out=max_syn)
        return spikes

    sim.neurons.step = step
    started = time.perf_counter()
    result = sim.run()
    wall_time_s = round(time.perf_counter() - started, 3)

    spike_hash = common.spike_hash(result.recorder)
    if spike_hash != record["hashes"]["spike_sha256"]:
        raise RuntimeError(
            f"replay spike hash mismatch for {record['stream']} {condition}: "
            f"{spike_hash} != {record['hashes']['spike_sha256']}"
        )
    adapter = BancActivityAdapter(
        result.recorder,
        world.populations,
        graph_threshold=world.graph.threshold,
    )
    decoder = MotorDecoder(world.populations, world.decoder_config)
    decisions = adapter.decode(decoder, 0.0, duration_ms)
    decision_payload = [decision.as_dict() for decision in decisions]
    decision_hash = common.digest_json(decision_payload)
    if decision_hash != record["hashes"]["decision_sha256"]:
        raise RuntimeError(
            f"replay decision hash mismatch for {record['stream']} {condition}"
        )

    times = np.asarray(result.recorder.spike_times_ms, dtype=np.float64)
    indices = np.asarray(result.recorder.spike_neuron_indices, dtype=np.int64)
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    stimulated_mask = np.zeros(n, dtype=bool)
    stimulated_mask[stimulated] = True
    motor_mask = class_mask["motor"]

    desc = lambda idx: {
        "index": int(idx),
        "root_id": int(world.graph.root_ids[idx]),
        "super_class": str(world.nodes.iloc[idx]["super_class"]),
        "side": str(world.nodes.iloc[idx]["side"]),
        "cell_function": str(world.nodes.iloc[idx]["cell_function"]),
    }

    groups = {
        "stimulated": stimulated_mask,
        "first_hop": _mask(first_hop, n),
        "second_hop": _mask(second_hop, n),
        "non_stimulated": ~stimulated_mask,
        "non_stimulated_non_motor": (~stimulated_mask) & (~motor_mask),
    }
    for name, mask in class_mask.items():
        groups[name] = mask

    group_payload = {
        name: group_stats(
            groups[name],
            counts,
            max_v,
            max_syn,
            threshold_mv,
            rest_mv,
            closest_lookup=desc,
        )
        for name in GROUP_ORDER
        if name in groups
    }

    all_classes = sorted(
        {
            str(value)
            for value in world.nodes["super_class"].fillna("").astype(str).unique()
        }
    )
    class_payload = {}
    for value in all_classes:
        mask = np.asarray(
            world.nodes["super_class"].fillna("").astype(str).to_numpy() == value,
            dtype=bool,
        )
        if not mask.any():
            continue
        stats = group_stats(
            mask, counts, max_v, max_syn, threshold_mv, rest_mv
        )
        class_payload[value or "unannotated"] = stats

    stim_times = np.sort(times[stimulated_mask[indices]])
    downstream_times = np.sort(times[~stimulated_mask[indices]])
    event_locked_stim = event_locked_stimulated(events_used, stim_times)
    alignment_stim = runner.alignment(events_used, stim_times, duration_ms)
    alignment_downstream = runner.alignment(events_used, downstream_times, duration_ms)

    stim_spike_counts = np.bincount(indices, minlength=n).astype(np.int64)
    signed_outdeg = np.zeros(n, dtype=np.int64)
    if stimulated.size:
        starts = np.asarray(world.graph.out_indptr)[stimulated]
        ends = np.asarray(world.graph.out_indptr)[stimulated + 1]
        counts_per = ends - starts
        signed_outdeg[stimulated] = np.bincount(
            np.repeat(np.arange(stimulated.size), counts_per),
            weights=signed.astype(np.int64),
            minlength=int(stimulated.size),
        ).astype(np.int64)
    total_transmissions = int(
        result.summary.get("synaptic_transmission", {}).get(
            "spike_transmissions", 0
        )
    )
    signed_transmissions = int(
        np.dot(stim_spike_counts[stimulated], signed_outdeg[stimulated])
    )
    unsigned_transmissions = max(0, total_transmissions - signed_transmissions)

    return {
        "stream": record["stream"],
        "condition": condition,
        "base_condition": base,
        "seed": int(record["seed"]),
        "duration_ms": duration_ms,
        "replay": {
            "spike_hash_match": True,
            "decision_hash_match": True,
            "drive_hash_match": True,
            "wall_time_s": wall_time_s,
        },
        "drive": {
            "kind": None if schedule is None else schedule.describe().get("kind"),
            "total_charge_pa_ms": (
                None
                if schedule is None
                else round(
                    float(
                        schedule.injected_charge_pa_ms()
                        if hasattr(schedule, "injected_charge_pa_ms")
                        else schedule.total_charge_pa_ms()
                    ),
                    6,
                )
            ),
            "background_pa": background,
            "noise_std_pa": noise,
            "max_input_current_all_pa": round(float(max_input_all), 6),
            "max_input_current_stimulated_pa": (
                None if not np.isfinite(max_input_stim) else round(float(max_input_stim), 6)
            ),
        },
        "activity": {
            "n_spikes": int(counts.sum()),
            "stimulated_spikes": int(counts[stimulated_mask].sum()),
            "non_stimulated_spikes": int(counts[~stimulated_mask].sum()),
            "motor_spikes": int(counts[motor_mask].sum()),
            "spike_time_min_ms": float(times.min()) if times.size else None,
            "spike_time_max_ms": float(times.max()) if times.size else None,
        },
        "structure": {
            "stimulated_neurons": int(stimulated.size),
            "signed_outgoing_edges": int(signed.sum()),
            "first_hop_targets_all": int(first_hop_all.size),
            "first_hop_downstream_targets": int(first_hop.size),
            "first_hop_excluded_stimulated": int(
                np.intersect1d(first_hop_all, stimulated).size
            ),
            "first_hop_signed_outgoing_edges": int(first_signed.sum()),
            "second_hop_targets_all": int(second_hop_all.size),
            "second_hop_downstream_targets": int(second_hop.size),
            "first_hop_descending": int(
                class_mask["descending"][first_hop].sum()
            ),
            "second_hop_descending": int(
                class_mask["descending"][second_hop].sum()
            ),
            "second_hop_motor": int(motor_mask[second_hop].sum()),
            "first_hop_targets_motor": int(motor_mask[first_hop].sum()),
        },
        "transmission": {
            "total_spike_edge_transmissions": total_transmissions,
            "signed_transmissions": signed_transmissions,
            "unsigned_transmissions": unsigned_transmissions,
            "signed_share": (
                None
                if total_transmissions == 0
                else round(signed_transmissions / total_transmissions, 6)
            ),
        },
        "threshold": {
            "threshold_mv": threshold_mv,
            "resting_mv": rest_mv,
            "rheobase_pa": round(
                (threshold_mv - rest_mv) * float(world.neuron_params.leak_conductance_ns),
                6,
            ),
        },
        "groups": group_payload,
        "classes": class_payload,
        "event_locked_stimulated": event_locked_stim,
        "alignment_stimulated": alignment_stim,
        "alignment_downstream": alignment_downstream,
    }


def _mask(indices: np.ndarray, n: int) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    mask[np.asarray(indices, dtype=np.int64)] = True
    return mask


# -- statistics --------------------------------------------------------------


def endpoint_values(row: dict, diagnostic: dict | None) -> dict:
    payload = {
        "total_spikes": int(row["total_spikes"]),
        "stimulated_spikes": int(row["stimulated_spikes"]),
        "non_stimulated_spikes": int(row["non_stimulated_spikes"]),
        "motor_spikes": int(row["motor_spikes"]),
        "active_neurons": int(row["active_neurons"]),
        "event_locked_downstream_spikes": int(
            row["event_locked_downstream_spikes"]
        ),
        "alignment_best_r": row["alignment_best_r"],
        "decoded_state_counts": row["decoded_state_counts"],
    }
    if diagnostic is not None:
        groups = diagnostic["groups"]
        payload.update(
            {
                "first_hop_spikes": groups.get("first_hop", {}).get("spikes"),
                "second_hop_spikes": groups.get("second_hop", {}).get("spikes"),
                "descending_spikes": groups.get("descending", {}).get("spikes"),
                "ascending_spikes": groups.get("ascending", {}).get("spikes"),
                "event_locked_stimulated_spikes": diagnostic[
                    "event_locked_stimulated"
                ].get("total_spikes_in_window"),
                "event_locked_stimulated_latency_median_ms": diagnostic[
                    "event_locked_stimulated"
                ].get("latency_ms", {}).get("median"),
                "first_hop_receiving_neurons": groups.get("first_hop", {}).get(
                    "receiving_neurons"
                ),
                "first_hop_max_synaptic_current_pa": groups.get("first_hop", {}).get(
                    "max_synaptic_current_pa"
                ),
                "first_hop_max_membrane_mv": groups.get("first_hop", {}).get(
                    "max_membrane_mv"
                ),
                "first_hop_closest_deficit_mv": groups.get("first_hop", {}).get(
                    "closest_deficit_mv"
                ),
                "non_stimulated_non_motor_closest_deficit_mv": groups.get(
                    "non_stimulated_non_motor", {}
                ).get("closest_deficit_mv"),
                "motor_closest_deficit_mv": groups.get("motor", {}).get(
                    "closest_deficit_mv"
                ),
            }
        )
    return payload


def numeric_summary(values: list[float]) -> dict:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return {"n": 0}
    return common.summary_stats(clean)


def compare_pair(
    b_by_stream: dict,
    x_by_stream: dict,
    endpoint: str,
    *,
    preregistered_primary: bool,
) -> dict:
    per_stream = {}
    b_values = []
    x_values = []
    diffs = []
    for stream in STREAMS:
        b = b_by_stream.get(stream, {}).get(endpoint)
        x = x_by_stream.get(stream, {}).get(endpoint)
        if b is None or x is None:
            per_stream[stream] = {"b": b, "x": x, "difference": None}
            continue
        b = float(b)
        x = float(x)
        b_values.append(b)
        x_values.append(x)
        difference = b - x
        diffs.append(difference)
        per_stream[stream] = {
            "b": round(b, 6),
            "x": round(x, 6),
            "difference": round(difference, 6),
            "ratio": None if x == 0 else round(b / x, 6),
            "relative_difference_pct": None
            if x == 0
            else round(100.0 * difference / x, 6),
        }
    b_stats = numeric_summary(b_values)
    x_stats = numeric_summary(x_values)
    diff_stats = numeric_summary(diffs)
    if b_stats.get("n", 0) > 1 and x_stats.get("n", 0) > 1:
        sd_b = b_stats["sd"]
        sd_x = x_stats["sd"]
        zero_variance = sd_b == 0 or sd_x == 0
        hedges = (
            None
            if sd_x == 0
            else float((b_stats["mean"] - x_stats["mean"]) / sd_x)
        )
    else:
        zero_variance = True
        hedges = None
    signs = {1 if value > 0 else (-1 if value < 0 else 0) for value in diffs}
    return {
        "endpoint": endpoint,
        "preregistered_primary": preregistered_primary,
        "n_streams": len(b_values),
        "n_independent_recordings": 1,
        "per_stream": per_stream,
        "b_summary": b_stats,
        "x_summary": x_stats,
        "difference_summary": diff_stats,
        "hedges_g_b_minus_x": hedges,
        "zero_variance": bool(zero_variance),
        "degenerate": bool(zero_variance or all(value == 0 for value in diffs)),
        "sign_pattern": (
            "all_positive"
            if signs == {1}
            else "all_negative"
            if signs == {-1}
            else "mixed"
            if 1 in signs and -1 in signs
            else "all_zero"
        ),
        "inference": "descriptive; n=3 non-independent streams, no p-value or CI",
    }


def statistical_comparisons(
    condition_rows: dict, diagnostics: dict, n_events: dict | None = None
) -> dict:
    values: dict[str, dict[str, dict]] = {}
    for stream, block in condition_rows.items():
        for condition, row in block.items():
            key = f"{stream}:{condition}"
            diagnostic = diagnostics.get(key)
            values.setdefault(condition, {})[stream] = endpoint_values(row, diagnostic)
    output = {}
    for b_condition, x_condition in COMPARISONS:
        pair_label = f"{b_condition}_vs_{x_condition}"
        endpoints = {}
        for endpoint in PRIMARY_ENDPOINTS:
            if endpoint == "decoded_state_counts":
                b_states = {
                    stream: values[b_condition][stream]["decoded_state_counts"]
                    for stream in STREAMS
                    if stream in values.get(b_condition, {})
                }
                x_states = {
                    stream: values[x_condition][stream]["decoded_state_counts"]
                    for stream in STREAMS
                    if stream in values.get(x_condition, {})
                }
                identical = all(
                    b_states.get(stream) == x_states.get(stream)
                    for stream in STREAMS
                )
                endpoints[endpoint] = {
                    "endpoint": endpoint,
                    "preregistered_primary": True,
                    "b_values": b_states,
                    "x_values": x_states,
                    "identical_across_streams": bool(identical),
                    "note": "decoder state counts; no numeric effect size",
                }
                continue
            endpoints[endpoint] = compare_pair(
                values[b_condition],
                values[x_condition],
                endpoint,
                preregistered_primary=True,
            )
        for endpoint in EXPLORATORY_ENDPOINTS:
            endpoints[endpoint] = compare_pair(
                values[b_condition],
                values[x_condition],
                endpoint,
                preregistered_primary=False,
            )
        output[pair_label] = {
            "b_condition": b_condition,
            "x_condition": x_condition,
            "question": {
                "B_actual_vs_A_no_events": "sensory-event effect",
                "B_actual_vs_C_temporal_shuffle": "temporal-order sensitivity",
                "B_actual_vs_D_feature_identity_shuffle": "feature-identity sensitivity",
                "B_actual_vs_E_random_matched_mapping": "mapping specificity",
                "B_actual_vs_F_constant_matched_charge": (
                    "temporal distribution versus matched charge"
                ),
                "B_actual_vs_G_background_noise": (
                    "sensory response versus background/noise"
                ),
            }[pair_label],
            "endpoints": endpoints,
        }
    return {
        "replication_unit": "one simulation run (stream, condition)",
        "n_runs": 27,
        "n_streams": 3,
        "n_independent_recordings": 1,
        "n_independent_events": (
            n_events
            if n_events is not None
            else {stream: len(runner.load_stream(stream)["events"]) for stream in STREAMS}
        ),
        "n_stimulated_neurons": 232,
        "n_graph_neurons": 172433,
        "n_motor_neurons": 805,
        "n_descending_neurons": 1316,
        "inference": (
            "descriptive only. The three streams are non-overlapping segments of "
            "one recording group, not independent sequences. No confirmatory "
            "p-value, confidence interval or effect-size inference is claimed. "
            "Neuron-level and event-level values are descriptive, not replicates."
        ),
        "pairs": output,
    }


# -- assembly ----------------------------------------------------------------


def build_payload(
    result: dict,
    runs: list[dict],
    checkpoint_records: list[dict],
    *,
    diagnostics: dict[str, dict] | None = None,
    runtime: dict | None = None,
) -> dict:
    reconciliation = reconcile(runs, checkpoint_records)
    rows = condition_tables(runs)
    comparisons = statistical_comparisons(
        rows,
        diagnostics or {},
        n_events={
            stream: int(payload.get("n_events", 0))
            for stream, payload in result.get("streams", {}).items()
        },
    )
    return {
        "phase": "4H.4",
        "title": "Sensory-to-BANC round-trip completion and analysis",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol_sha256": result.get("protocol_sha256"),
        "source_result": str(RESULT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "execution": {
            "reconciliation": reconciliation,
            "runtime": result.get("runtime"),
            "determinism": result.get("determinism"),
            "integrity": result.get("integrity"),
        },
        "condition_results": rows,
        "statistical_comparisons": comparisons,
        "diagnostics": diagnostics or {},
        "runtime": runtime,
        "limitations": result.get("limitations", []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-replay", action="store_true")
    parser.add_argument("--force-replay", action="store_true")
    parser.add_argument("--streams", default=",".join(STREAMS))
    parser.add_argument(
        "--conditions", default=",".join(CONDITIONS + REPEAT_LABELS)
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--diagnostics-checkpoint", type=Path, default=DIAGNOSTICS_CHECKPOINT
    )
    args = parser.parse_args(argv)

    clock = time.perf_counter()
    result = load_result()
    runs = result["runs"]
    checkpoint_records = load_jsonl(CHECKPOINT)
    reconciliation = reconcile(runs, checkpoint_records)
    print(
        f"matrix: expected={reconciliation['expected_runs']} "
        f"stored={reconciliation['stored_runs']} unique={reconciliation['unique_runs']} "
        f"complete={reconciliation['complete']}"
    )
    if not reconciliation["complete"]:
        print(json.dumps(reconciliation, indent=1))
        raise SystemExit("run matrix is incomplete; refusing to analyse")

    config = common.load_yaml(runner.MAPPING_CONFIG)
    encoders = build_encoders(config["features"])
    current_pa = {
        feature: float(payload.get("current_pa", 0.0))
        for feature, payload in config["features"].items()
    }
    drive = config["drive"]
    dt_ms = float(drive["dt_ms"])
    world = common.load_world()
    real_mapping = BancSensoryMapping(
        world.nodes,
        world.graph,
        config["mapping"],
        motor_mask=world.populations.motor_mask,
        action_masks={
            name: np.asarray(mask, dtype=bool)
            for name, mask in world.populations.masks.items()
        },
    )
    random_config = json.loads(json.dumps(config["mapping"]))
    random_config["seed"] = int(config["mapping"]["seed"]) + 450000
    random_mapping = BancSensoryMapping(
        world.nodes,
        world.graph,
        random_config,
        motor_mask=world.populations.motor_mask,
        action_masks={
            name: np.asarray(mask, dtype=bool)
            for name, mask in world.populations.masks.items()
        },
        randomise_pools=True,
    )
    verification = verify_configuration(world, real_mapping, config, result)
    print(
        f"configuration: {verification['n_checks']} checks, "
        f"{verification['n_failed']} failed"
    )
    if not verification["pass"]:
        print(json.dumps(verification, indent=1))
        raise SystemExit("configuration verification failed")

    diagnostics: dict[str, dict] = {}
    if not args.no_replay:
        streams_filter = {
            item.strip() for item in args.streams.split(",") if item.strip()
        }
        conditions_filter = {
            item.strip() for item in args.conditions.split(",") if item.strip()
        }
        unknown_streams = streams_filter - set(STREAMS)
        unknown_conditions = conditions_filter - set(CONDITIONS + REPEAT_LABELS)
        if unknown_streams or unknown_conditions:
            raise SystemExit(
                f"unknown streams {sorted(unknown_streams)} or conditions "
                f"{sorted(unknown_conditions)}"
            )
        existing = load_jsonl(Path(args.diagnostics_checkpoint))
        for item in existing:
            diagnostics[f"{item['stream']}:{item['condition']}"] = item
        class_mask = class_masks(world)
        streams = {name: runner.load_stream(name) for name in STREAMS}
        replay_clock = time.perf_counter()
        selected = [
            record
            for record in runs
            if record["stream"] in streams_filter
            and record["condition"] in conditions_filter
        ]
        selected.sort(
            key=lambda item: (
                STREAMS.index(item["stream"]),
                CONDITIONS.index(item["condition"].replace("_repeat", "")),
                item["condition"].endswith("_repeat"),
            )
        )
        for record in selected:
            key = f"{record['stream']}:{record['condition']}"
            if key in diagnostics and not args.force_replay:
                print(f"  skip replay {key} (checkpoint)")
                continue
            diagnostic = replay_diagnostics(
                record,
                world,
                real_mapping,
                random_mapping,
                encoders,
                drive,
                current_pa,
                streams[record["stream"]],
                class_mask,
            )
            diagnostics[key] = diagnostic
            common.jsonl_append(Path(args.diagnostics_checkpoint), diagnostic)
            print(
                f"  replay {key} spikes={diagnostic['activity']['n_spikes']} "
                f"nonstim={diagnostic['activity']['non_stimulated_spikes']} "
                f"motor={diagnostic['activity']['motor_spikes']} "
                f"({diagnostic['replay']['wall_time_s']} s)"
            )
        replay_wall_time = round(time.perf_counter() - replay_clock, 3)
    else:
        replay_wall_time = 0.0

    runtime = {
        "analysis_wall_time_s": round(time.perf_counter() - clock, 3),
        "replay_wall_time_s": replay_wall_time,
        "n_replays": len(diagnostics),
    }
    payload = build_payload(
        result,
        runs,
        checkpoint_records,
        diagnostics=diagnostics,
        runtime=runtime,
    )
    payload["configuration_verification"] = verification
    payload["execution"]["matrix"] = reconciliation

    common.write_json(Path(args.output), payload)
    print(
        f"wrote {args.output} | replays={len(diagnostics)} | "
        f"{runtime['analysis_wall_time_s']} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
