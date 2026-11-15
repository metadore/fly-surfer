"""BANC activity to structured motor output, with a no-stimulus control.

The runner reuses the existing BANC graph artifact, transmitter/weight policy,
LIF simulator, Phase 4F populations and decoder. It adds only the Phase 4
recording and game-action interface.

The default probe stimulates 64 VNC intrinsic verified-excitatory non-motor
neurons ranked by signed synapse count onto motor neurons. That probe is a
structural experiment, not a biological command: no motor neuron is stimulated
directly and no spike is injected. A second condition runs the same graph with
no stimulation to show the baseline is silent.

Example::

    python experiments/phase_4/run_motor_output_pipeline.py

The output file is deterministic apart from timestamps and wall-clock fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import BancConnectome, sha256_file  # noqa: E402
from brain.banc_simulator import BancSimulator, BancStimulation  # noqa: E402
from brain.banc_synapse_policy import (  # noqa: E402
    VERIFIED_EXCITATORY,
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)
from brain.neuron_model import LIFParameters  # noqa: E402
from motor.action_decoder import (  # noqa: E402
    UNMAPPED,
    GameActionDecoder,
)
from motor.activity_recorder import MotorActivityRecorder  # noqa: E402
from motor.motor_decoder import DecoderConfig  # noqa: E402
from motor.populations import (  # noqa: E402
    PopulationOptions,
    build_populations,
)

BANC_DIR = PROJECT_ROOT / "datasets" / "processed" / "banc_v888"
NODES_PATH = BANC_DIR / "banc_nodes.csv.gz"
POLICY_CONFIG = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
DECODER_CONFIG = PROJECT_ROOT / "configs" / "motor_decoder.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
PHASE_4G_RESULT = (
    PROJECT_ROOT / "experiments" / "results" / "phase_4g" / "phase_4g_experiment.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "phase_4" / "motor_output_demo.json"
)

THRESHOLD = 5
DT_MS = 0.5
DURATION_MS = 300.0
SEED = 20261108
STIM_START_MS = 50.0
STIM_END_MS = 250.0
STIM_CURRENT_PA = 300.0
STIM_COUNT = 64
DECODE_START_MS = 50.0
DECODE_END_MS = 300.0
MAX_RECORDED_SPIKES = 5_000_000
MOTOR_ANNOTATIONS = (
    "banc_888_id",
    "super_class",
    "cell_class",
    "side",
    "body_part_effector",
    "peripheral_target_type",
    "neurotransmitter_verified",
    "proofread",
)


def activity_hash(recorder) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(recorder.spike_times_ms).tobytes())
    digest.update(np.ascontiguousarray(recorder.spike_neuron_indices).tobytes())
    return digest.hexdigest()


def digest_json(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_setup(threshold: int = THRESHOLD) -> dict:
    graph_path = BANC_DIR / f"banc_graph_t{int(threshold)}.npz"
    policy_payload = load_yaml(POLICY_CONFIG)
    decoder_payload = load_yaml(DECODER_CONFIG)
    neuron_payload = load_yaml(NEURON_CONFIG)

    graph = BancConnectome.load(graph_path)
    nodes = pd.read_csv(NODES_PATH)
    if len(nodes) != graph.n_nodes:
        raise RuntimeError("node table and graph node counts differ")
    if not np.array_equal(
        nodes["banc_888_id"].to_numpy().astype(np.int64),
        np.asarray(graph.root_ids, dtype=np.int64),
    ):
        raise RuntimeError("node table order does not match graph root_ids")

    sign_policy = SignPolicy.from_config(policy_payload["transmitter_sign_policy"])
    weight_policy = WeightPolicy.from_config(
        policy_payload["weight_policy"]["primary"]
    )
    policy = build_synapse_policy(graph, nodes, sign_policy, weight_policy)
    populations = build_populations(
        nodes,
        n_neurons=graph.n_nodes,
        threshold=graph.threshold,
        options=PopulationOptions(**decoder_payload["populations"]),
    )
    populations.provenance.update(
        {
            "nodes_path": str(NODES_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "graph_path": str(graph_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "graph_nodes": int(graph.n_nodes),
            "graph_edges": int(graph.n_edges),
        }
    )
    decoder_config = DecoderConfig.from_config(decoder_payload["decoder"])
    neuron_params = LIFParameters.from_config(neuron_payload["neuron"])
    return {
        "graph_path": graph_path,
        "graph": graph,
        "nodes": nodes,
        "sign_policy": sign_policy,
        "weight_policy": weight_policy,
        "policy": policy,
        "populations": populations,
        "decoder_config": decoder_config,
        "neuron_params": neuron_params,
    }


def motor_synapse_scores(graph, populations, policy) -> np.ndarray:
    """Signed synapse count from every node onto the 805 motor neurons."""
    motor = np.asarray(populations.motor_mask, dtype=bool)
    src = np.asarray(graph.edge_src, dtype=np.int64)
    dst = np.asarray(graph.edge_dst, dtype=np.int64)
    weight = np.asarray(graph.edge_weight, dtype=np.int64)
    motor_edges = motor[dst]
    return np.bincount(
        src[motor_edges], weights=weight[motor_edges], minlength=graph.n_nodes
    )


def select_probe_indices(
    graph,
    nodes: pd.DataFrame,
    policy,
    populations,
    *,
    count: int,
    selection: str,
    seed: int,
) -> tuple[np.ndarray, dict]:
    motor = np.asarray(populations.motor_mask, dtype=bool)
    n = int(graph.n_nodes)
    if count < 1 or count > n:
        raise ValueError(f"stimulus count must be in [1, {n}]")
    super_class = nodes["super_class"].fillna("").astype(str)
    non_motor = ~motor
    scores = motor_synapse_scores(graph, populations, policy)
    metadata: dict = {
        "selection": selection,
        "requested_count": int(count),
        "rule": None,
        "pool_size": None,
        "tie_break": "ascending graph node index",
    }

    if selection == "vnc_intrinsic_ranked":
        excitatory = (np.asarray(policy.neuron_codes) == VERIFIED_EXCITATORY) & non_motor
        pool = super_class.eq("ventral_nerve_cord_intrinsic").to_numpy(dtype=bool)
        pool = np.flatnonzero(pool & excitatory)
        metadata.update(
            {
                "rule": (
                    "top-N by integer signed synapse count onto motor neurons; "
                    "super_class == ventral_nerve_cord_intrinsic; verified "
                    "excitatory sign; motor neurons excluded"
                ),
                "pool_size": int(pool.size),
            }
        )
        if pool.size < count:
            raise ValueError(f"pool has {pool.size} neurons; requested {count}")
        order = pool[np.lexsort((pool, -scores[pool]))]
        chosen = np.sort(order[:count].astype(np.int64))
    elif selection == "vnc_intrinsic_random":
        excitatory = (np.asarray(policy.neuron_codes) == VERIFIED_EXCITATORY) & non_motor
        pool = super_class.eq("ventral_nerve_cord_intrinsic").to_numpy(dtype=bool)
        pool = np.flatnonzero(pool & excitatory)
        metadata.update(
            {
                "rule": "random draw from the same VNC intrinsic pool; unknown-sign excluded",
                "pool_size": int(pool.size),
                "seed": int(seed),
            }
        )
        if pool.size < count:
            raise ValueError(f"pool has {pool.size} neurons; requested {count}")
        chosen = np.sort(
            np.random.default_rng(seed).choice(pool, size=count, replace=False)
        ).astype(np.int64)
    elif selection == "highest_out_degree":
        degrees = np.diff(np.asarray(graph.out_indptr))
        pool = np.flatnonzero(non_motor)
        order = pool[np.lexsort((pool, -degrees[pool]))]
        metadata.update(
            {
                "rule": "top-N out-degree excluding motor neurons",
                "pool_size": int(pool.size),
            }
        )
        if pool.size < count:
            raise ValueError(f"pool has {pool.size} neurons; requested {count}")
        chosen = np.sort(order[:count].astype(np.int64))
    elif selection == "random_non_motor":
        pool = np.flatnonzero(non_motor)
        metadata.update(
            {
                "rule": "uniform random draw across non-motor nodes",
                "pool_size": int(pool.size),
                "seed": int(seed),
            }
        )
        if pool.size < count:
            raise ValueError(f"pool has {pool.size} neurons; requested {count}")
        chosen = np.sort(
            np.random.default_rng(seed).choice(pool, size=count, replace=False)
        ).astype(np.int64)
    else:
        raise ValueError(
            "selection must be vnc_intrinsic_ranked, vnc_intrinsic_random, "
            "highest_out_degree or random_non_motor"
        )

    if np.any(motor[chosen]):
        raise RuntimeError("probe selection contains a motor neuron")
    metadata["node_indices"] = [int(value) for value in chosen]
    metadata["root_ids"] = [int(value) for value in graph.root_ids[chosen]]
    metadata["indices_sha256"] = hashlib.sha256(
        np.ascontiguousarray(chosen).tobytes()
    ).hexdigest()
    return chosen, metadata


def verify_phase4g_reference(graph, indices: np.ndarray) -> dict | None:
    if not PHASE_4G_RESULT.is_file():
        return None
    payload = json.loads(PHASE_4G_RESULT.read_text(encoding="utf-8"))
    block = payload["conditions"]["C_vnc_intrinsic_candidate"]["summary"]["stimulation"]
    expected = [int(value) for value in block["root_ids"]]
    actual = [int(value) for value in graph.root_ids[indices]]
    if expected != actual:
        raise RuntimeError(
            "recomputed Phase 4G condition C probe does not match the recorded "
            "candidate list; the runner will not claim reproducibility"
        )
    return {
        "reference": str(PHASE_4G_RESULT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "matches_recorded_root_ids": True,
    }


def _state_counts(outputs) -> dict:
    counts: dict[str, int] = {}
    for output in outputs:
        counts[output.state] = counts.get(output.state, 0) + 1
    return dict(sorted(counts.items()))


def _compact_output(output) -> dict:
    return output.as_dict()


def run_condition(
    setup: dict,
    indices: np.ndarray,
    *,
    label: str,
    description: str,
    duration_ms: float,
    dt_ms: float,
    seed: int,
    current_pa: float,
) -> dict:
    graph = setup["graph"]
    populations = setup["populations"]
    started = time.perf_counter()
    decode_end = min(DECODE_END_MS, float(duration_ms))
    decode_start = min(DECODE_START_MS, max(0.0, decode_end - float(dt_ms)))
    if decode_end <= decode_start:
        raise ValueError("simulation duration is too short to decode a window")

    stimulated = np.unique(np.asarray(indices, dtype=np.int64))
    if stimulated.size:
        if np.any(populations.motor_mask[stimulated]):
            raise ValueError("stimulation must never target motor neurons")
        stimulation = BancStimulation(
            stimulated,
            float(current_pa),
            STIM_START_MS,
            STIM_END_MS,
            label=label,
        )
    else:
        stimulation = None

    simulator = BancSimulator(
        graph,
        setup["policy"],
        neuron_params=setup["neuron_params"],
        dt_ms=float(dt_ms),
        duration_ms=float(duration_ms),
        seed=int(seed),
        stimulation=stimulation,
        max_recorded_spikes=MAX_RECORDED_SPIKES,
    )
    result = simulator.run()
    recorder = MotorActivityRecorder(
        result.recorder,
        populations,
        setup["nodes"],
        graph=graph,
        stimulated_indices=stimulated,
    )
    decoder = GameActionDecoder(populations, setup["decoder_config"])
    outputs = decoder.decode_series(
        result.recorder.spike_times_ms,
        result.recorder.spike_neuron_indices,
        decode_start,
        decode_end,
    )
    requested = {
        "ROLL": decoder.decode_requested(
            "ROLL",
            result.recorder.spike_times_ms,
            result.recorder.spike_neuron_indices,
            decode_start,
            decode_end,
        ).as_dict()
    }

    decode_window = recorder.time_window(decode_start, decode_end)
    full_window = recorder.time_window(0.0, duration_ms)
    motor_per_neuron = recorder.per_neuron(
        0.0, duration_ms, "motor", annotation_columns=MOTOR_ANNOTATIONS
    )
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    motor = np.asarray(populations.motor_mask, dtype=bool)
    stimulated_mask = np.zeros(graph.n_nodes, dtype=bool)
    stimulated_mask[stimulated] = True

    condition = {
        "label": label,
        "description": description,
        "stimulated_neurons": int(stimulated.size),
        "current_pa": None if not stimulated.size else float(current_pa),
        "stimulation_window_ms": (
            None if not stimulated.size else [STIM_START_MS, STIM_END_MS]
        ),
        "duration_ms": float(duration_ms),
        "dt_ms": float(dt_ms),
        "seed": int(seed),
        "activity": {
            "total_spikes": int(counts.sum()),
            "motor_spikes": int(counts[motor].sum()),
            "motor_active_neurons": int(np.count_nonzero(counts[motor])),
            "non_motor_spikes": int(counts[~motor].sum()),
            "stimulated_spikes": int(counts[stimulated_mask].sum()),
            "downstream_spikes": int(counts[~stimulated_mask].sum()),
            "active_neurons": int(np.count_nonzero(counts)),
        },
        "populations": {
            name: recorder.selection(name).describe()
            for name in (
                "motor",
                "descending",
                "ascending",
                "vnc_intrinsic",
                "non_motor",
                "unassigned_motor",
                "left_motor",
                "right_motor",
                "jump_motor",
            )
        },
        "full_window": full_window.as_dict(),
        "decode_window": decode_window.as_dict(),
        "motor_per_neuron": motor_per_neuron,
        "decoder_outputs": [_compact_output(output) for output in outputs],
        "decoded_state_counts": _state_counts(outputs),
        "requested_channels": requested,
        "spike_hash": activity_hash(result.recorder),
        "decision_hash": digest_json(
            [output.as_dict() for output in outputs]
        ),
        "simulation": result.summary["simulation"],
        "activity_summary": result.summary["activity"],
        "activity_by_stimulation": result.summary["activity_by_stimulation"],
        "synaptic_transmission": result.summary["synaptic_transmission"],
        "diagnostics": result.summary["diagnostics"],
        "wall_time_s": round(time.perf_counter() - started, 3),
    }
    return condition


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=int, choices=(1, 5, 10), default=THRESHOLD)
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS)
    parser.add_argument("--dt-ms", type=float, default=DT_MS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--stimulus-count", type=int, default=STIM_COUNT)
    parser.add_argument(
        "--selection",
        choices=(
            "vnc_intrinsic_ranked",
            "vnc_intrinsic_random",
            "highest_out_degree",
            "random_non_motor",
        ),
        default="vnc_intrinsic_ranked",
    )
    parser.add_argument("--stimulus-current-pa", type=float, default=STIM_CURRENT_PA)
    parser.add_argument(
        "--conditions",
        default="probe,no_stimulus",
        help="comma-separated subset of {probe,no_stimulus}",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = Path(args.output)
    if output.exists() and not args.force:
        print(
            f"refusing to overwrite {output}; pass --force to replace it",
            file=sys.stderr,
        )
        return 2
    conditions = [name.strip() for name in str(args.conditions).split(",") if name.strip()]
    unknown = sorted(set(conditions) - {"probe", "no_stimulus"})
    if unknown:
        print(f"unknown conditions: {unknown}", file=sys.stderr)
        return 2

    started = time.perf_counter()
    setup = load_setup(args.threshold)
    graph = setup["graph"]
    populations = setup["populations"]
    probe, selection_metadata = select_probe_indices(
        graph,
        setup["nodes"],
        setup["policy"],
        populations,
        count=args.stimulus_count,
        selection=args.selection,
        seed=args.seed,
    )
    reference = None
    if args.selection == "vnc_intrinsic_ranked" and args.stimulus_count == STIM_COUNT:
        reference = verify_phase4g_reference(graph, probe)

    condition_records = {}
    if "probe" in conditions:
        condition_records["probe"] = run_condition(
            setup,
            probe,
            label=f"phase4:{args.selection}@{args.stimulus_current_pa:g}pA",
            description=(
                "Declared structural probe. Non-motor neurons receive current; "
                "motor spikes are downstream model output, not a biological "
                "motor command."
            ),
            duration_ms=args.duration_ms,
            dt_ms=args.dt_ms,
            seed=args.seed,
            current_pa=args.stimulus_current_pa,
        )
    if "no_stimulus" in conditions:
        condition_records["no_stimulus"] = run_condition(
            setup,
            np.empty(0, dtype=np.int64),
            label="phase4:no_stimulus",
            description=(
                "Negative control: identical graph and model with no injected "
                "current. Any spikes here would contradict the deterministic "
                "baseline."
            ),
            duration_ms=args.duration_ms,
            dt_ms=args.dt_ms,
            seed=args.seed,
            current_pa=args.stimulus_current_pa,
        )

    sign = setup["sign_policy"].describe()
    decoder_description = GameActionDecoder(
        populations, setup["decoder_config"]
    ).describe()
    payload = {
        "phase": "4",
        "pipeline": "BANC connectome -> simulation -> motor recording -> game-action output",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "inputs": {
            "graph": str(setup["graph_path"].relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "graph_sha256": sha256_file(setup["graph_path"]),
            "node_table": str(NODES_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "node_table_sha256": sha256_file(NODES_PATH),
            "policy_config_sha256": sha256_file(POLICY_CONFIG),
            "decoder_config_sha256": sha256_file(DECODER_CONFIG),
            "neuron_config_sha256": sha256_file(NEURON_CONFIG),
        },
        "graph": {
            "threshold": int(graph.threshold),
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "n_isolated": int(graph.n_isolated),
        },
        "populations": populations.report(),
        "decoder": decoder_description,
        "sign_policy": sign,
        "weight_policy": setup["weight_policy"].describe(),
        "probe_selection": selection_metadata,
        "phase_4g_reference": reference,
        "conditions": condition_records,
        "supported_mappings": {
            action: {
                "channel": action,
                "population": decoder_description["supported_channels"][action][
                    "population"
                ],
                "size": decoder_description["supported_channels"][action]["size"],
            }
            for action in ("LEFT", "RIGHT", "JUMP")
        },
        "unresolved_mappings": decoder_description["unsupported_channels"],
        "scientific_status": [
            "Weights are transformed structural synapse counts, not conductances.",
            "Transmitter signs are presynaptic modelling priors, not measured postsynaptic effects.",
            "The probe is a declared structural stimulation, not a biological motor command.",
            "LEFT, RIGHT and JUMP are annotation-derived decoder labels, not identified actions.",
            "ROLL and DUCK have no annotated population in this export and remain unresolved.",
            "The no-stimulus condition is the negative control for fabricated activity.",
        ],
        "reproduce": (
            "python experiments/phase_4/run_motor_output_pipeline.py"
        ),
        "wall_time_s": round(time.perf_counter() - started, 3),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=1, allow_nan=False, default=str) + "\n",
        encoding="utf-8",
    )

    summary = {
        "output": str(output),
        "graph": payload["graph"],
        "populations": populations.sizes,
        "probe": {
            "selection": args.selection,
            "n_stimulated": int(probe.size),
            "root_ids_match_phase_4g": None
            if reference is None
            else reference["matches_recorded_root_ids"],
        },
        "conditions": {
            name: {
                "total_spikes": record["activity"]["total_spikes"],
                "motor_spikes": record["activity"]["motor_spikes"],
                "motor_active_neurons": record["activity"]["motor_active_neurons"],
                "non_motor_spikes": record["activity"]["non_motor_spikes"],
                "decoded_state_counts": record["decoded_state_counts"],
            }
            for name, record in condition_records.items()
        },
        "roll_request_state": (
            condition_records["probe"]["requested_channels"]["ROLL"]["state"]
            if "probe" in condition_records
            else None
        ),
        "wall_time_s": payload["wall_time_s"],
    }
    print(json.dumps(summary, indent=1))
    if (
        "probe" in condition_records
        and condition_records["probe"]["requested_channels"]["ROLL"]["state"] != UNMAPPED
    ):
        print("ROLL was not reported as UNMAPPED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
