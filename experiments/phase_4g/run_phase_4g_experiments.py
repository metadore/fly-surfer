"""Phase 4G.5 — BANC propagation coupled to the unchanged Phase 4F decoder.

Conditions stimulate upstream BANC neurons selected from Phase 4E pathway
results, propagate through the signed structural graph, and pass the resulting
spikes to the unmodified Phase 4F motor decoder. Motor populations are never
stimulated. Decoder thresholds and populations are not changed.

Output: ``experiments/results/phase_4g/phase_4g_experiment.json``.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import OUT_DIR as BANC_DIR, BancConnectome, sha256_file  # noqa: E402
from brain.banc_simulation_adapter import BancActivityAdapter  # noqa: E402
from brain.banc_simulator import BancSimulator, BancStimulation  # noqa: E402
from brain.banc_synapse_policy import (  # noqa: E402
    CLASS_NAMES,
    VERIFIED_EXCITATORY,
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)
from motor.motor_decoder import DecoderConfig, MotorDecoder  # noqa: E402
from motor.populations import (  # noqa: E402
    PopulationOptions,
    build_populations,
)

POLICY_CONFIG = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
DECODER_CONFIG = PROJECT_ROOT / "configs" / "motor_decoder.yaml"
NODES_PATH = BANC_DIR / "banc_nodes.csv.gz"
OUTPUT_PATH = PROJECT_ROOT / "experiments" / "results" / "phase_4g" / "phase_4g_experiment.json"

N_CANDIDATES = 64
PRIMARY_THRESHOLD = 5
SEED = 20261108
DT_MS = 0.5
DURATION_MS = 300.0
STIM_START_MS = 50.0
STIM_END_MS = 250.0
STIM_CURRENT_PA = 300.0
DECODE_START_MS = 50.0
DECODE_END_MS = 300.0


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def spike_hash(recorder) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(recorder.spike_times_ms).tobytes())
    digest.update(np.ascontiguousarray(recorder.spike_neuron_indices).tobytes())
    return digest.hexdigest()


def decision_hash(records: list[dict]) -> str:
    return sha256_bytes(json.dumps(records, sort_keys=True).encode("utf-8"))


def load_policy_parts(config: dict) -> tuple[SignPolicy, WeightPolicy]:
    sign = SignPolicy.from_config(config["transmitter_sign_policy"])
    weight = WeightPolicy.from_config(config["weight_policy"]["primary"])
    return sign, weight


def load_world(
    threshold: int,
    nodes: pd.DataFrame,
    policy_config: dict,
    *,
    sign_policy: SignPolicy | None = None,
    weight_policy: WeightPolicy | None = None,
):
    graph = BancConnectome.load(BANC_DIR / f"banc_graph_t{threshold}.npz")
    default_sign, default_weight = load_policy_parts(policy_config)
    policy = build_synapse_policy(
        graph,
        nodes,
        sign_policy or default_sign,
        weight_policy or default_weight,
    )
    return graph, policy


def motor_synapse_vector(graph, eligible: np.ndarray, motor_mask: np.ndarray) -> np.ndarray:
    src = np.asarray(graph.edge_src, dtype=np.int64)
    dst = np.asarray(graph.edge_dst, dtype=np.int64)
    weight = np.asarray(graph.edge_weight, dtype=np.int64)
    mask = eligible[src] & motor_mask[dst]
    return np.bincount(src[mask], weights=weight[mask], minlength=graph.n_nodes)


def rank_by_motor_synapses(
    graph, eligible: np.ndarray, motor_mask: np.ndarray, count: int
) -> np.ndarray:
    scores = motor_synapse_vector(graph, eligible, motor_mask)
    indices = np.flatnonzero(eligible)
    order = indices[np.lexsort((indices, -scores[indices]))]
    return np.sort(order[:count].astype(np.int64))


def candidate_record(
    graph,
    nodes: pd.DataFrame,
    policy,
    populations,
    indices: np.ndarray,
    *,
    label: str,
    rule: str,
    seed: int | None,
) -> dict:
    src = np.asarray(graph.edge_src, dtype=np.int64)
    dst = np.asarray(graph.edge_dst, dtype=np.int64)
    weight = np.asarray(graph.edge_weight, dtype=np.int64)
    selected = np.zeros(graph.n_nodes, dtype=bool)
    selected[indices] = True
    motor = np.asarray(populations.motor_mask, dtype=bool)
    edges = selected[src] & motor[dst]
    codes = policy.neuron_codes[indices]
    sign_counts = Counter(CLASS_NAMES[int(code)] for code in codes)
    block = {
        "label": label,
        "rule": rule,
        "seed": seed,
        "size": int(indices.size),
        "banc_888_ids": [int(value) for value in graph.root_ids[indices]],
        "node_indices": [int(value) for value in indices],
        "verified_sign_classes": dict(sorted(sign_counts.items())),
        "motor_neurons_in_selection": int(np.count_nonzero(selected & motor)),
        "edges_to_motor": int(edges.sum()),
        "synapses_to_motor": int(weight[edges].sum()),
        "out_edges_total": int(np.diff(graph.out_indptr)[indices].sum()),
        "motor_target_coverage": {
            action: int(
                np.count_nonzero(
                    edges & np.asarray(populations.mask(action), dtype=bool)[dst]
                )
            )
            for action in ("LEFT", "RIGHT", "JUMP")
        },
    }
    if indices.size:
        subset = nodes.iloc[indices]
        for column in ("super_class", "side", "body_part_effector"):
            values = subset[column].fillna("unknown").astype(str).value_counts()
            block[f"{column}_composition"] = {
                str(key): int(value) for key, value in values.items()
            }
    return block


def build_candidates(
    graph,
    nodes: pd.DataFrame,
    policy,
    populations,
    seed: int,
) -> dict[str, dict]:
    codes = policy.neuron_codes
    motor = np.asarray(populations.motor_mask, dtype=bool)
    exc = (codes == VERIFIED_EXCITATORY) & ~motor
    super_class = nodes["super_class"].fillna("").astype(str)

    descending = super_class.eq("descending").to_numpy() & exc
    vnc = super_class.eq("ventral_nerve_cord_intrinsic").to_numpy() & exc

    b_idx = rank_by_motor_synapses(graph, descending, motor, N_CANDIDATES)
    c_idx = rank_by_motor_synapses(graph, vnc, motor, N_CANDIDATES)

    reserved = np.zeros(graph.n_nodes, dtype=bool)
    reserved[b_idx] = True
    reserved[c_idx] = True

    rng = np.random.default_rng(seed)
    pool_d = np.flatnonzero(exc & ~reserved)
    d_idx = np.sort(rng.choice(pool_d, size=N_CANDIDATES, replace=False).astype(np.int64))

    pool_e = np.flatnonzero(descending & ~reserved)
    e_idx = np.sort(rng.choice(pool_e, size=N_CANDIDATES, replace=False).astype(np.int64))

    for name, indices in (
        ("B", b_idx),
        ("C", c_idx),
        ("D", d_idx),
        ("E", e_idx),
    ):
        if indices.size != N_CANDIDATES:
            raise RuntimeError(f"candidate group {name} has {indices.size} neurons")
        if np.any(motor[indices]):
            raise RuntimeError(f"candidate group {name} contains motor neurons")
        if np.any(codes[indices] != VERIFIED_EXCITATORY):
            raise RuntimeError(f"candidate group {name} is not uniformly excitatory")

    records = {
        "B_descending_candidate": candidate_record(
            graph,
            nodes,
            policy,
            populations,
            b_idx,
            label="B",
            rule=(
                "Top verified-excitatory descending neurons ranked by total "
                "synapses onto motor neurons at threshold 5 (Phase 4E direct "
                "descending pathway)."
            ),
            seed=None,
        ),
        "C_vnc_intrinsic_candidate": candidate_record(
            graph,
            nodes,
            policy,
            populations,
            c_idx,
            label="C",
            rule=(
                "Top verified-excitatory ventral-nerve-cord intrinsic neurons "
                "ranked by total direct synapses onto motor neurons at "
                "threshold 5 (Phase 4E two-hop intermediate population)."
            ),
            seed=None,
        ),
        "D_random_matched": candidate_record(
            graph,
            nodes,
            policy,
            populations,
            d_idx,
            label="D",
            rule=(
                "Random verified-excitatory non-motor neurons, matched in size, "
                "excluding groups B and C."
            ),
            seed=seed,
        ),
        "E_shuffled_assignment": candidate_record(
            graph,
            nodes,
            policy,
            populations,
            e_idx,
            label="E",
            rule=(
                "Shuffled assignment: random verified-excitatory descending "
                "neurons, matched in size, excluding the connectivity-ranked "
                "group B."
            ),
            seed=seed,
        ),
    }
    return {
        "indices": {"B": b_idx, "C": c_idx, "D": d_idx, "E": e_idx},
        "records": records,
    }


def run_simulation(
    graph,
    policy,
    indices: np.ndarray | None,
    *,
    current_pa: float = STIM_CURRENT_PA,
    background_pa: float = 0.0,
    noise_pa: float = 0.0,
    duration_ms: float = DURATION_MS,
    dt_ms: float = DT_MS,
    seed: int = SEED,
    label: str = "",
):
    stimulation = None
    if indices is not None and len(indices):
        stimulation = BancStimulation(
            np.asarray(indices, dtype=np.int64),
            float(current_pa),
            STIM_START_MS,
            STIM_END_MS,
            label=label,
        )
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        seed=seed,
        background_current_pa=background_pa,
        noise_std_pa=noise_pa,
        stimulation=stimulation,
    )
    return simulator, simulator.run(duration_ms=duration_ms)


def decode_result(
    result,
    populations,
    decoder_config: DecoderConfig,
    *,
    condition: str,
    threshold: int,
    seed: int,
    indices: np.ndarray | None,
    decode_start: float = DECODE_START_MS,
    decode_end: float = DECODE_END_MS,
) -> dict:
    adapter = BancActivityAdapter(
        result.recorder, populations, graph_threshold=threshold
    )
    decoder = MotorDecoder(populations, decoder_config)
    decisions = adapter.decode(decoder, decode_start, decode_end)
    window_records = []
    for decision in decisions:
        record = decision.as_dict()
        record["condition"] = condition
        record["threshold"] = int(threshold)
        record["seed"] = int(seed)
        window_records.append(record)

    activity = adapter.population_activity(decode_start, decode_end)
    states = Counter(record["decoded_state"] for record in window_records)
    max_scores = {
        action: max(
            (record["scores"][action] for record in window_records), default=0.0
        )
        for action in ("LEFT", "RIGHT", "JUMP")
    }
    max_raw_scores = {
        action: max(
            (record["raw_scores"][action] for record in window_records), default=0.0
        )
        for action in ("LEFT", "RIGHT", "JUMP")
    }

    indices = (
        np.empty(0, dtype=np.int64)
        if indices is None
        else np.asarray(indices, dtype=np.int64)
    )
    spike_indices = result.recorder.spike_neuron_indices
    stimulated = np.isin(spike_indices, indices) if indices.size else np.zeros(
        len(spike_indices), dtype=bool
    )
    motor_mask = np.asarray(populations.motor_mask, dtype=bool)
    motor_spikes = motor_mask[spike_indices] if len(spike_indices) else np.empty(0, bool)

    return {
        "spike_hash": spike_hash(result.recorder),
        "decision_hash": decision_hash(window_records),
        "window_records": window_records,
        "decoder_state_counts": dict(sorted(states.items())),
        "neutral_windows": int(states.get("NEUTRAL", 0)),
        "max_scores": max_scores,
        "max_raw_scores": max_raw_scores,
        "population_activity": activity,
        "activity": {
            "n_spikes": int(len(spike_indices)),
            "active_neurons": int(np.unique(spike_indices).size),
            "stimulated_spikes": int(stimulated.sum()),
            "non_stimulated_spikes": int((~stimulated).sum()),
            "non_stimulated_active_neurons": int(
                np.unique(spike_indices[~stimulated]).size
            ),
            "motor_spikes": int(motor_spikes.sum()),
            "motor_active_neurons": int(np.unique(spike_indices[motor_spikes]).size),
        },
        "summary": result.summary,
    }


def compact_run(record: dict) -> dict:
    activity = dict(record["activity"])
    return {
        "spike_hash": record["spike_hash"],
        "decision_hash": record["decision_hash"],
        "decoded_states": record["decoder_state_counts"],
        "neutral_windows": record["neutral_windows"],
        "max_scores": record["max_scores"],
        "max_raw_scores": record["max_raw_scores"],
        "activity": activity,
        "population_activity": record["population_activity"],
    }


def variability(entries: list[dict], key: str) -> dict:
    values = [entry[key] for entry in entries]
    return {
        "values": values,
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    policy_config = yaml.safe_load(POLICY_CONFIG.read_text(encoding="utf-8"))
    decoder_payload = yaml.safe_load(DECODER_CONFIG.read_text(encoding="utf-8"))
    populations_options = PopulationOptions(**decoder_payload["populations"])
    decoder_config = DecoderConfig.from_config(decoder_payload["decoder"])
    experiment_config = decoder_payload["experiment"]
    if int(experiment_config["duration_ms"]) != int(DURATION_MS):
        raise RuntimeError("runner and Phase 4F config disagree on duration")
    if float(experiment_config["drive_start_ms"]) != STIM_START_MS:
        raise RuntimeError("runner and Phase 4F config disagree on drive start")
    if float(experiment_config["drive_end_ms"]) != STIM_END_MS:
        raise RuntimeError("runner and Phase 4F config disagree on drive end")
    if float(experiment_config["decode_start_ms"]) != DECODE_START_MS:
        raise RuntimeError("runner and Phase 4F config disagree on decode start")
    if float(experiment_config["decode_end_ms"]) != DECODE_END_MS:
        raise RuntimeError("runner and Phase 4F config disagree on decode end")

    nodes = pd.read_csv(NODES_PATH)
    t5_started = time.perf_counter()
    graph, policy = load_world(PRIMARY_THRESHOLD, nodes, policy_config)
    populations = build_populations(
        nodes,
        n_neurons=graph.n_nodes,
        threshold=graph.threshold,
        options=populations_options,
    )
    t5_load_s = time.perf_counter() - t5_started

    candidates = build_candidates(graph, nodes, policy, populations, SEED)
    indices = candidates["indices"]

    conditions = {
        "A_no_stimulation": {
            "label": "A",
            "description": "No stimulation, no background, no noise.",
            "indices": None,
            "background_pa": 0.0,
            "noise_pa": 0.0,
        },
        "B_descending_candidate": {
            "label": "B",
            "description": "64 connectivity-ranked verified-excitatory descending neurons.",
            "indices": indices["B"],
            "background_pa": 0.0,
            "noise_pa": 0.0,
        },
        "C_vnc_intrinsic_candidate": {
            "label": "C",
            "description": "64 connectivity-ranked verified-excitatory VNC intrinsic neurons.",
            "indices": indices["C"],
            "background_pa": 0.0,
            "noise_pa": 0.0,
        },
        "D_random_matched": {
            "label": "D",
            "description": "64 random verified-excitatory non-motor neurons.",
            "indices": indices["D"],
            "background_pa": 0.0,
            "noise_pa": 0.0,
        },
        "E_shuffled_assignment": {
            "label": "E",
            "description": "64 random verified-excitatory descending neurons (shuffled assignment).",
            "indices": indices["E"],
            "background_pa": 0.0,
            "noise_pa": 0.0,
        },
        "F_background_noise": {
            "label": "F",
            "description": "No stimulation; declared background 50 pA and 50 pA Gaussian noise.",
            "indices": None,
            "background_pa": 50.0,
            "noise_pa": 50.0,
        },
    }

    condition_results: dict[str, dict] = {}
    determinism: dict[str, dict] = {}
    repeats: dict[str, dict] = {}

    for name, spec in conditions.items():
        label = spec["label"]
        print(f"running condition {name}", flush=True)
        _, result = run_simulation(
            graph,
            policy,
            spec["indices"],
            background_pa=spec["background_pa"],
            noise_pa=spec["noise_pa"],
            label=f"phase4g5:{label}",
        )
        primary = decode_result(
            result,
            populations,
            decoder_config,
            condition=name,
            threshold=PRIMARY_THRESHOLD,
            seed=SEED,
            indices=spec["indices"],
        )
        condition_results[name] = {
            "description": spec["description"],
            "stimulated_neurons": 0 if spec["indices"] is None else int(len(spec["indices"])),
            "current_pa": None if spec["indices"] is None else STIM_CURRENT_PA,
            "background_pa": spec["background_pa"],
            "noise_pa": spec["noise_pa"],
            **primary,
        }

        _, repeat_result = run_simulation(
            graph,
            policy,
            spec["indices"],
            background_pa=spec["background_pa"],
            noise_pa=spec["noise_pa"],
            label=f"phase4g5:{label}",
        )
        repeat = decode_result(
            repeat_result,
            populations,
            decoder_config,
            condition=name,
            threshold=PRIMARY_THRESHOLD,
            seed=SEED,
            indices=spec["indices"],
        )
        determinism[name] = {
            "spike_hash_run1": primary["spike_hash"],
            "spike_hash_run2": repeat["spike_hash"],
            "spike_match": primary["spike_hash"] == repeat["spike_hash"],
            "decision_hash_run1": primary["decision_hash"],
            "decision_hash_run2": repeat["decision_hash"],
            "decision_match": primary["decision_hash"] == repeat["decision_hash"],
        }
        repeats[name] = compact_run(repeat)

    all_deterministic = all(
        entry["spike_match"] and entry["decision_match"]
        for entry in determinism.values()
    )

    # Sensitivity suite on condition C, the strongest propagating candidate.
    # All decoder thresholds and population definitions stay unchanged.
    sensitivity: dict[str, list[dict]] = {
        "threshold": [],
        "intensity": [],
        "weight_transform": [],
        "unknown_edge_policy": [],
        "predicted_fallback": [],
        "seed": [],
        "decoder_window": [],
    }
    base_c = condition_results["C_vnc_intrinsic_candidate"]

    def sensitivity_entry(name: str, **metadata) -> dict:
        return {"variant": name, **metadata}

    # Threshold: candidate identities are fixed; graph and policy are rebuilt.
    for threshold in (1, 10):
        print(f"sensitivity threshold {threshold}", flush=True)
        alt_graph, alt_policy = load_world(threshold, nodes, policy_config)
        alt_indices = np.array(
            [alt_graph.node_index(value) for value in graph.root_ids[indices["C"]]],
            dtype=np.int64,
        )
        _, alt_result = run_simulation(
            alt_graph,
            alt_policy,
            alt_indices,
            label=f"phase4g5:threshold{threshold}",
        )
        alt = decode_result(
            alt_result,
            populations,
            decoder_config,
            condition="C_vnc_intrinsic_candidate",
            threshold=threshold,
            seed=SEED,
            indices=alt_indices,
        )
        sensitivity["threshold"].append(
            sensitivity_entry(
                f"threshold_{threshold}",
                threshold=threshold,
                **compact_run(alt),
            )
        )
        del alt_graph, alt_policy, alt_result, alt
        gc.collect()

    # Intensity
    for current in (100.0, 600.0):
        print(f"sensitivity intensity {current:g} pA", flush=True)
        _, alt_result = run_simulation(
            graph,
            policy,
            indices["C"],
            current_pa=current,
            label=f"phase4g5:{current:g}pA",
        )
        alt = decode_result(
            alt_result,
            populations,
            decoder_config,
            condition="C_vnc_intrinsic_candidate",
            threshold=PRIMARY_THRESHOLD,
            seed=SEED,
            indices=indices["C"],
        )
        sensitivity["intensity"].append(
            sensitivity_entry(f"current_{current:g}pA", current_pa=current, **compact_run(alt))
        )

    # Weight transforms
    for entry in policy_config["weight_policy"]["sensitivity"]:
        name = str(entry["name"])
        print(f"sensitivity transform {name}", flush=True)
        weight_policy = WeightPolicy.from_config(entry["parameters"])
        alt_graph = graph
        alt_policy = build_synapse_policy(
            graph,
            nodes,
            SignPolicy.from_config(policy_config["transmitter_sign_policy"]),
            weight_policy,
        )
        _, alt_result = run_simulation(
            alt_graph, alt_policy, indices["C"], label=f"phase4g5:{name}"
        )
        alt = decode_result(
            alt_result,
            populations,
            decoder_config,
            condition="C_vnc_intrinsic_candidate",
            threshold=PRIMARY_THRESHOLD,
            seed=SEED,
            indices=indices["C"],
        )
        sensitivity["weight_transform"].append(
            sensitivity_entry(
                name,
                weight_policy=weight_policy.describe(),
                **compact_run(alt),
            )
        )
        del alt_policy, alt_result, alt
        gc.collect()

    # Unknown-edge policy: exclusion versus retained zero weight.
    print("sensitivity unknown edge policy", flush=True)
    zero_sign = SignPolicy.from_config(
        {**policy_config["transmitter_sign_policy"], "unknown_edge_policy": "zero"}
    )
    zero_policy = build_synapse_policy(graph, nodes, zero_sign, WeightPolicy.from_config(
        policy_config["weight_policy"]["primary"]
    ))
    _, zero_result = run_simulation(
        graph, zero_policy, indices["C"], label="phase4g5:unknown_zero"
    )
    zero = decode_result(
        zero_result,
        populations,
        decoder_config,
        condition="C_vnc_intrinsic_candidate",
        threshold=PRIMARY_THRESHOLD,
        seed=SEED,
        indices=indices["C"],
    )
    sensitivity["unknown_edge_policy"].append(
        sensitivity_entry(
            "unknown_edges_zero",
            unknown_edge_policy="zero",
            identical_to_primary=zero["spike_hash"] == base_c["spike_hash"],
            **compact_run(zero),
        )
    )

    # Predicted fallback
    print("sensitivity predicted fallback", flush=True)
    fallback_sign = SignPolicy.from_config(
        {**policy_config["transmitter_sign_policy"], "predicted_fallback": True}
    )
    fallback_policy = build_synapse_policy(
        graph,
        nodes,
        fallback_sign,
        WeightPolicy.from_config(policy_config["weight_policy"]["primary"]),
    )
    _, fallback_result = run_simulation(
        graph, fallback_policy, indices["C"], label="phase4g5:predicted_fallback"
    )
    fallback = decode_result(
        fallback_result,
        populations,
        decoder_config,
        condition="C_vnc_intrinsic_candidate",
        threshold=PRIMARY_THRESHOLD,
        seed=SEED,
        indices=indices["C"],
    )
    sensitivity["predicted_fallback"].append(
        sensitivity_entry(
            "predicted_fallback_on",
            declared_policy=fallback_policy.coverage["declared_policy"],
            **compact_run(fallback),
        )
    )

    # Seed: conditions A-E have no stochastic term, so seed sensitivity is run
    # on the noise-only control F where a seed actually matters.
    for seed in (1, 2):
        print(f"sensitivity seed {seed}", flush=True)
        _, seed_result = run_simulation(
            graph,
            policy,
            None,
            background_pa=50.0,
            noise_pa=50.0,
            seed=seed,
            label=f"phase4g5:seed{seed}",
        )
        seed_run = decode_result(
            seed_result,
            populations,
            decoder_config,
            condition="F_background_noise",
            threshold=PRIMARY_THRESHOLD,
            seed=seed,
            indices=None,
        )
        sensitivity["seed"].append(
            sensitivity_entry(f"seed_{seed}", seed=seed, **compact_run(seed_run))
        )
    sensitivity["seed"].insert(
        0,
        sensitivity_entry(
            "seed_20261108",
            seed=SEED,
            note="same run as condition F primary",
            **compact_run(condition_results["F_background_noise"]),
        ),
    )

    # Decoder window sensitivity, reusing the condition C recording.
    _, c_result = run_simulation(graph, policy, indices["C"], label="phase4g5:window")
    for window in (25.0, 100.0):
        print(f"sensitivity decoder window {window:g} ms", flush=True)
        alt_config = replace(decoder_config, window_ms=window, step_ms=window)
        alt = decode_result(
            c_result,
            populations,
            alt_config,
            condition="C_vnc_intrinsic_candidate",
            threshold=PRIMARY_THRESHOLD,
            seed=SEED,
            indices=indices["C"],
        )
        sensitivity["decoder_window"].append(
            sensitivity_entry(
                f"window_{window:g}ms",
                decoder_config={
                    "window_ms": float(window),
                    "step_ms": float(window),
                    **{
                        key: value
                        for key, value in decoder_config.__dict__.items()
                        if key not in ("window_ms", "step_ms")
                    },
                },
                **compact_run(alt),
            )
        )

    seed_entries = sensitivity["seed"]
    seed_variability = {
        "n_spikes": variability(
            [{"v": entry["activity"]["n_spikes"]} for entry in seed_entries], "v"
        ),
        "active_neurons": variability(
            [{"v": entry["activity"]["active_neurons"]} for entry in seed_entries], "v"
        ),
        "max_scores": {
            action: {
                "values": [entry["max_scores"][action] for entry in seed_entries],
            }
            for action in ("LEFT", "RIGHT", "JUMP")
        },
        "decoded_states": [entry["decoded_states"] for entry in seed_entries],
    }

    unknown_equivalence = (
        sensitivity["unknown_edge_policy"][0]["identical_to_primary"]
    )

    signal_overview = {}
    for name, record in condition_results.items():
        signal_overview[name] = {
            "spikes": record["activity"]["n_spikes"],
            "motor_spikes": record["activity"]["motor_spikes"],
            "motor_active_neurons": record["activity"]["motor_active_neurons"],
            "decoded_states": record["decoder_state_counts"],
            "population_active_fractions": {
                action: record["population_activity"]["populations"][action][
                    "active_fraction"
                ]
                for action in ("LEFT", "RIGHT", "JUMP")
            },
        }

    execution_pass = bool(all_deterministic and unknown_equivalence)
    payload = {
        "phase": "4G.5",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "inputs": {
            "graph_threshold_1_sha256": sha256_file(BANC_DIR / "banc_graph_t1.npz"),
            "graph_threshold_5_sha256": sha256_file(BANC_DIR / "banc_graph_t5.npz"),
            "graph_threshold_10_sha256": sha256_file(BANC_DIR / "banc_graph_t10.npz"),
            "node_table_sha256": sha256_file(NODES_PATH),
            "policy_config_sha256": sha256_file(POLICY_CONFIG),
            "decoder_config_sha256": sha256_file(DECODER_CONFIG),
            "load_threshold_5_s": round(t5_load_s, 3),
        },
        "design": {
            "purpose": (
                "Couple BANC structural propagation to the unchanged Phase 4F "
                "decoder and compare connectivity-selected upstream stimulation "
                "against matched controls."
            ),
            "fixed_parameters": {
                "threshold": PRIMARY_THRESHOLD,
                "duration_ms": DURATION_MS,
                "dt_ms": DT_MS,
                "seed": SEED,
                "stimulus_current_pa": STIM_CURRENT_PA,
                "stimulus_start_ms": STIM_START_MS,
                "stimulus_end_ms": STIM_END_MS,
                "decode_start_ms": DECODE_START_MS,
                "decode_end_ms": DECODE_END_MS,
                "candidate_size": N_CANDIDATES,
                "neuron_model": "unchanged Phase 2 LIFParameters defaults",
                "synapse_model": "unchanged exponential currents, 5 ms / 8 ms",
                "weight_policy": policy_config["weight_policy"]["primary"],
                "decoder": decoder_config.__dict__,
            },
            "motor_populations": populations.report(),
            "decoder": MotorDecoder(populations, decoder_config).describe(),
            "candidate_rules": {
                "B": candidates["records"]["B_descending_candidate"]["rule"],
                "C": candidates["records"]["C_vnc_intrinsic_candidate"]["rule"],
                "D": candidates["records"]["D_random_matched"]["rule"],
                "E": candidates["records"]["E_shuffled_assignment"]["rule"],
            },
            "non_claims": [
                "LEFT, RIGHT and JUMP are decoder labels from published annotations, not identified motor commands.",
                "Stimulated neurons are upstream candidates; motor pools are not stimulated.",
                "A decoded action is not evidence of biological motor control.",
                "Structural connectivity and synapse counts are not conductance or physiological connectivity.",
            ],
        },
        "candidates": candidates["records"],
        "conditions": condition_results,
        "signal_overview": signal_overview,
        "determinism": determinism,
        "repeats": repeats,
        "sensitivity": sensitivity,
        "sensitivity_summary": {
            "seed": seed_variability,
            "unknown_edge_policy_equivalence": bool(unknown_equivalence),
            "threshold_variants": len(sensitivity["threshold"]),
            "intensity_variants": len(sensitivity["intensity"]),
            "weight_transform_variants": len(sensitivity["weight_transform"]),
            "decoder_window_variants": len(sensitivity["decoder_window"]),
        },
        "all_conditions_deterministic": bool(all_deterministic),
        "verdict": "PASS" if execution_pass else "FAIL",
        "limitations": [
            "Only verified-transmitter neurons can carry current under the primary policy; most BANC neurons and edges are excluded.",
            "Candidate groups are 64 neurons selected by structural ranking, not by any physiological criterion.",
            "The primary weight transform, cap and scale are declared calibrations, not measured conductances.",
            "One graph threshold (5) is primary; threshold 1 and 10 are sensitivity variants only.",
            "Conditions A-E have no stochastic term, so their seed sensitivity is trivially exact; only the noise-only control F varies with seed.",
        ],
        "runtime_s": round(time.perf_counter() - started, 3),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "conditions": len(condition_results),
                "deterministic": all_deterministic,
                "unknown_equivalence": unknown_equivalence,
                "signal_overview": {
                    key: {
                        "spikes": value["spikes"],
                        "motor_spikes": value["motor_spikes"],
                        "states": value["decoded_states"],
                    }
                    for key, value in signal_overview.items()
                },
                "verdict": payload["verdict"],
                "runtime_s": payload["runtime_s"],
                "output": str(args.output.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0 if execution_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
