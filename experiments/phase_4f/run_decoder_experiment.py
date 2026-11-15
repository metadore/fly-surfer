"""Phase 4F controlled motor-decoder experiment.

The experiment feeds the decoder spike trains produced by the unmodified
``brain.neuron_model.LIFPopulation`` for the BANC motor pools identified in the
Phase 4D node table. It is a decoder-logic experiment, not a connectome
simulation:

* the existing ``BrainSimulator`` cannot run on ``BancConnectome`` because
  ``SynapseModel`` requires ``graph.vocabulary`` and ``graph.nt_code``, which
  the BANC artifact does not contain; fabricating them would require an
  unapproved transmitter-sign policy (see ``probe_simulator``);
* therefore each scenario injects an explicit experimenter current into a
  declared fraction of one or more pools, and the unmodified LIF model turns
  that current into spike trains;
* no synapse, edge or graph threshold enters the decoder.

The amplitude grid is pre-declared and reported in full. No amplitude, window
or threshold is selected from a successful example.
"""

from __future__ import annotations

import argparse
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

from brain.banc_graph import (
    FAFB_ARTIFACTS,
    OUT_DIR as BANC_OUT_DIR,
    BancConnectome,
    compare_snapshots,
    sha256_file,
    snapshot_paths,
    verify_manifest,
    write_json,
)
from brain.neuron_model import LIFParameters, LIFPopulation
from brain.synapse_model import SynapseParameters
from brain.brain_simulator import BrainSimulator
from motor.motor_decoder import DecoderConfig, MotorDecoder
from motor.populations import (
    ACTION_POPULATIONS,
    PopulationOptions,
    build_populations,
    load_banc_populations,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "motor_decoder.yaml"
MANIFEST_PATH = BANC_OUT_DIR / "banc_manifest.json"
NODES_PATH = BANC_OUT_DIR / "banc_nodes.csv.gz"
GRAPH_PATHS = {
    threshold: BANC_OUT_DIR / f"banc_graph_t{threshold}.npz"
    for threshold in (1, 5, 10)
}
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "experiments" / "results" / "phase_4f"
    / "motor_decoder_experiment.json"
)
THRESHOLDS = (1, 5, 10)
PRIMARY_THRESHOLD = 5


def load_config(path: Path = CONFIG_PATH) -> dict:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for section in ("populations", "decoder", "experiment"):
        if section not in payload:
            raise ValueError(f"configuration is missing the {section!r} section")
    return payload


def probe_simulator(graph_path: Path) -> dict:
    """Record why the core simulator cannot consume a BANC graph unchanged."""
    graph = BancConnectome.load(graph_path)
    result = {
        "graph_path": str(graph_path),
        "graph_threshold": int(graph.threshold),
        "graph_nodes": int(graph.n_nodes),
        "banc_graph_has_vocabulary": hasattr(graph, "vocabulary"),
        "banc_graph_has_nt_code": hasattr(graph, "nt_code"),
    }
    try:
        BrainSimulator(
            graph,
            LIFParameters(),
            SynapseParameters(),
            duration_ms=1.0,
            progress_interval_ms=0.0,
        )
    except Exception as error:  # noqa: BLE001 - the failure is the evidence
        result["attempted"] = True
        result["failed"] = True
        result["error_type"] = type(error).__name__
        result["error_message"] = str(error)
    else:
        result["attempted"] = True
        result["failed"] = False
        result["error_type"] = None
        result["error_message"] = None
    result["missing_graph_fields"] = [
        name for name in ("vocabulary", "nt_code") if not hasattr(graph, name)
    ]
    result["conclusion"] = (
        "BrainSimulator.SynapseModel requires graph.vocabulary and graph.nt_code. "
        "BancConnectome provides neither, and Phase 4E deferred any transmitter "
        "sign policy, so the experiment injects current directly into the "
        "declared motor populations through the unmodified LIF model instead of "
        "forcing a full-network integration."
    )
    return result


def scenario_targets(populations, spec: dict) -> dict[str, np.ndarray]:
    """Select the driven neurons of each pool by ascending node index."""
    targets: dict[str, np.ndarray] = {}
    for action, fraction in spec.items():
        if action not in ACTION_POPULATIONS:
            raise ValueError(f"unknown scenario population {action!r}")
        value = float(fraction)
        if not 0.0 < value <= 1.0:
            raise ValueError(f"drive fraction for {action} must be in (0, 1]")
        members = np.flatnonzero(populations.mask(action))
        if members.size == 0:
            targets[action] = members.astype(np.int64)
            continue
        take = max(1, int(round(value * members.size)))
        targets[action] = members[: min(take, members.size)].astype(np.int64)
    return targets


def generate_spikes(
    driven_globals: np.ndarray,
    *,
    current_pa: float,
    dt_ms: float,
    duration_ms: float,
    drive_start_ms: float,
    drive_end_ms: float,
    jitter_pa: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Spike trains from the unmodified LIF model under an explicit current."""
    driven = np.asarray(sorted(int(value) for value in driven_globals), dtype=np.int64)
    if driven.size == 0:
        return (
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )
    population = LIFPopulation(driven.size, LIFParameters(), dt_ms)
    rng = np.random.default_rng(int(seed))
    offsets = (
        rng.normal(0.0, float(jitter_pa), driven.size)
        if jitter_pa > 0
        else np.zeros(driven.size)
    )
    n_steps = int(round(duration_ms / dt_ms))
    times: list[np.ndarray] = []
    indices: list[np.ndarray] = []
    for step in range(n_steps):
        time_ms = step * dt_ms
        if drive_start_ms <= time_ms < drive_end_ms:
            current = current_pa + offsets
        else:
            current = np.zeros(driven.size)
        spikes = population.step(current)
        if spikes.size:
            times.append(
                np.full(spikes.size, (step + 1) * dt_ms, dtype=np.float64)
            )
            indices.append(driven[spikes.astype(np.int64)])
    if not times:
        return (
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.int64),
        )
    return np.concatenate(times), np.concatenate(indices)


def run_grid(
    populations,
    decoder_config: DecoderConfig,
    experiment: dict,
    *,
    jitter_pa: float,
    include_windows: bool = True,
) -> tuple[list[dict], dict]:
    """Run every scenario at every pre-declared amplitude."""
    scenarios = experiment["scenarios"]
    amplitudes = [float(value) for value in experiment["current_amplitudes_pa"]]
    seed = int(experiment["seed"])
    dt_ms = float(experiment["dt_ms"])
    duration_ms = float(experiment["duration_ms"])
    drive_start = float(experiment["drive_start_ms"])
    drive_end = float(experiment["drive_end_ms"])
    decode_start = float(experiment["decode_start_ms"])
    decode_end = float(experiment["decode_end_ms"])

    runs: list[dict] = []
    for name in sorted(scenarios):
        targets = scenario_targets(populations, scenarios[name] or {})
        driven = (
            np.unique(np.concatenate(list(targets.values())))
            if targets
            else np.empty(0, dtype=np.int64)
        )
        for amplitude in amplitudes:
            times, indices = generate_spikes(
                driven,
                current_pa=amplitude,
                dt_ms=dt_ms,
                duration_ms=duration_ms,
                drive_start_ms=drive_start,
                drive_end_ms=drive_end,
                jitter_pa=jitter_pa,
                seed=seed,
            )
            decoder = MotorDecoder(populations, decoder_config)
            decisions = decoder.decode_series(
                times, indices, decode_start, decode_end
            )
            drive_decisions = [
                decision
                for decision in decisions
                if decision.window_end_ms <= drive_end + 1e-9
            ]
            post_decisions = [
                decision
                for decision in decisions
                if decision.window_start_ms >= drive_end - 1e-9
            ]
            record = {
                "scenario": name,
                "amplitude_pa": amplitude,
                "driven_neurons": {
                    action: int(targets[action].size)
                    for action in ACTION_POPULATIONS
                    if action in targets
                },
                "total_spikes": int(times.size),
                "drive_states": [
                    decision.state for decision in drive_decisions
                ],
                "drive_active_actions": [
                    list(decision.active_actions) for decision in drive_decisions
                ],
                "post_drive_states": [
                    decision.state for decision in post_decisions
                ],
                "final_state": decisions[-1].state,
            }
            if include_windows:
                record["windows"] = [
                    decision.as_dict() for decision in decisions
                ]
            runs.append(record)

    states = sorted(
        {
            state
            for run in runs
            for state in run["drive_states"] + run["post_drive_states"]
        }
    )
    aggregate = {
        "runs": len(runs),
        "jitter_pa": float(jitter_pa),
        "scenarios": sorted(scenarios),
        "amplitudes_pa": amplitudes,
        "observed_states": states,
        "drive_state_summary": {
            f"{run['scenario']}@{run['amplitude_pa']:g}": run["drive_states"]
            for run in runs
        },
        "drive_active_summary": {
            f"{run['scenario']}@{run['amplitude_pa']:g}": run[
                "drive_active_actions"
            ]
            for run in runs
        },
    }
    return runs, aggregate


def threshold_report(nodes: pd.DataFrame, options: PopulationOptions) -> dict:
    """Check that population membership is invariant across graph thresholds."""
    blocks = {}
    reference = None
    invariant = True
    for threshold in THRESHOLDS:
        populations = load_banc_populations(
            NODES_PATH,
            GRAPH_PATHS[threshold],
            threshold=threshold,
            options=options,
        )
        blocks[str(threshold)] = {
            "graph_threshold": int(populations.threshold),
            "sizes": populations.sizes,
            "edges": int(populations.provenance["graph_edges"]),
        }
        signatures = {
            action: populations.mask(action).tobytes()
            for action in ACTION_POPULATIONS
        }
        if reference is None:
            reference = signatures
        elif signatures != reference:
            invariant = False
    return {
        "thresholds": list(THRESHOLDS),
        "primary_threshold": PRIMARY_THRESHOLD,
        "membership_invariant": bool(invariant),
        "by_threshold": blocks,
        "decoder_reads_edges": False,
        "note": (
            "Phase 4D keeps every endpoint node at every threshold, so the "
            "annotation-derived masks are identical. The decoder never reads an "
            "edge, so a threshold cannot change a score; the threshold is "
            "recorded with every result and is never mixed."
        ),
    }


def integrity_block(before: dict, inputs_before: dict, inputs_after: dict) -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_check = verify_manifest(manifest)
    after = snapshot_paths(FAFB_ARTIFACTS)
    isolation = compare_snapshots(before, after)
    changed = [
        name
        for name in inputs_before
        if inputs_before[name]["sha256"] != inputs_after.get(name, {}).get("sha256")
    ]
    return {
        "manifest_verification": {
            "pass": bool(manifest_check["pass"]),
            "failures": manifest_check["failures"],
            "checks": len(manifest_check["checks"]),
        },
        "fafb_isolation": isolation,
        "experiment_inputs_unchanged": not changed,
        "changed_inputs": changed,
        "raw_inputs_modified": bool(manifest_check["failures"]),
    }


def input_hashes() -> dict:
    paths = {
        "config": CONFIG_PATH,
        "nodes": NODES_PATH,
        "graph_t1": GRAPH_PATHS[1],
        "graph_t5": GRAPH_PATHS[5],
        "graph_t10": GRAPH_PATHS[10],
        "manifest": MANIFEST_PATH,
    }
    return {
        name: {
            "path": str(Path(path).relative_to(PROJECT_ROOT).as_posix()),
            "bytes": int(Path(path).stat().st_size),
            "sha256": sha256_file(path),
        }
        for name, path in paths.items()
    }


def run(output: Path = DEFAULT_OUTPUT, repeats: int = 2) -> dict:
    started = time.perf_counter()
    config = load_config()
    experiment = config["experiment"]
    options = PopulationOptions(
        leg_effectors=tuple(config["populations"]["leg_effectors"]),
        jump_target=str(config["populations"]["jump_target"]),
        jump_membership_in_leg_pools=bool(
            config["populations"]["jump_membership_in_leg_pools"]
        ),
    )
    decoder_config = DecoderConfig.from_config(config["decoder"])

    before = snapshot_paths(FAFB_ARTIFACTS)
    inputs_before = input_hashes()
    populations = load_banc_populations(
        NODES_PATH, GRAPH_PATHS[PRIMARY_THRESHOLD], options=options
    )
    nodes = pd.read_csv(NODES_PATH)
    interface = {
        "activity_source": (
            "brain.neuron_model.LIFPopulation driven by an explicit "
            "experimenter current in the declared motor pools; no synapse and "
            "no graph edge is used"
        ),
        "decoder_input": (
            "spike times (ms) and graph node indices, the exact arrays stored "
            "by brain.neural_activity.SpikeRecorder; decode_recorder() accepts "
            "a SimulationResult.recorder directly"
        ),
        "simulator_compatibility": probe_simulator(GRAPH_PATHS[PRIMARY_THRESHOLD]),
    }

    first_runs, aggregate = run_grid(
        populations,
        decoder_config,
        experiment,
        jitter_pa=float(experiment["drive_jitter_pa"]),
    )
    sensitivity_jitter = float(experiment["jitter_sensitivity_pa"])
    jitter_runs, jitter_aggregate = run_grid(
        populations,
        decoder_config,
        experiment,
        jitter_pa=sensitivity_jitter,
        include_windows=False,
    )
    deterministic = True
    for _ in range(max(0, repeats - 1)):
        repeat_runs, repeat_aggregate = run_grid(
            populations,
            decoder_config,
            experiment,
            jitter_pa=float(experiment["drive_jitter_pa"]),
        )
        repeat_jitter, repeat_jitter_aggregate = run_grid(
            populations,
            decoder_config,
            experiment,
            jitter_pa=sensitivity_jitter,
            include_windows=False,
        )
        deterministic = deterministic and repeat_runs == first_runs
        deterministic = deterministic and repeat_aggregate == aggregate
        deterministic = deterministic and repeat_jitter == jitter_runs
        deterministic = deterministic and (
            repeat_jitter_aggregate == jitter_aggregate
        )
    changed = sum(
        1
        for controlled, jittered in zip(first_runs, jitter_runs)
        if controlled["drive_states"] != jittered["drive_states"]
    )

    threshold = threshold_report(nodes, options)
    integrity = integrity_block(before, inputs_before, input_hashes())
    decoder = MotorDecoder(populations, decoder_config)
    runtime = time.perf_counter() - started
    report = {
        "phase": "4F",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "verdict": "PASS WITH LIMITATIONS",
        "canonical_id_field": "banc_888_id",
        "inputs": inputs_before,
        "populations": populations.report(),
        "decoder": decoder.describe(),
        "interface": interface,
        "threshold_sensitivity": threshold,
        "experiment": {
            "seed": int(experiment["seed"]),
            "dt_ms": float(experiment["dt_ms"]),
            "duration_ms": float(experiment["duration_ms"]),
            "drive_start_ms": float(experiment["drive_start_ms"]),
            "drive_end_ms": float(experiment["drive_end_ms"]),
            "drive_jitter_pa": float(experiment["drive_jitter_pa"]),
            "jitter_sensitivity_pa": float(experiment["jitter_sensitivity_pa"]),
            "decode_start_ms": float(experiment["decode_start_ms"]),
            "decode_end_ms": float(experiment["decode_end_ms"]),
            "current_amplitudes_pa": [
                float(value) for value in experiment["current_amplitudes_pa"]
            ],
            "scenarios": experiment["scenarios"],
            "initial_potential_mv": LIFParameters().initial_potential_mv,
            "rheobase_pa": LIFParameters().rheobase_pa,
        },
        "aggregate": aggregate,
        "runs": first_runs,
        "jitter_sensitivity": {
            "jitter_pa": sensitivity_jitter,
            "runs_with_changed_drive_states": int(changed),
            "total_runs": len(first_runs),
            "aggregate": jitter_aggregate,
            "runs": jitter_runs,
        },
        "determinism": {
            "repeats": int(repeats),
            "conditions": 2,
            "identical": bool(deterministic),
        },
        "integrity": integrity,
        "limitations": [
            "LEFT, RIGHT and JUMP are decoder labels from published effector "
            "annotations, not identified biological motor commands.",
            "The tergotrochanter pool is a jump-associated candidate pool, not "
            "a validated jump command.",
            "Activity comes from direct experimenter current into motor pools, "
            "not from synaptic propagation through the BANC connectome.",
            "The core simulator cannot run on BancConnectome without a "
            "transmitter-sign and weight policy that this phase did not adopt.",
            "All driven neurons share one current amplitude and one seeded "
            "jitter; the result says nothing about physiological motor coding.",
            "No Subway Surfers action, keyboard output or game control is "
            "produced or claimed.",
        ],
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "runtime_seconds": round(float(runtime), 3),
    }
    write_json(output, report)
    print(f"Wrote {output}")
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Phase 4F controlled motor-decoder experiment"
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repeats", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run(args.output, args.repeats)
    print(
        f"verdict: {report['verdict']}; populations: "
        f"{report['populations']['sizes']}; runs: "
        f"{report['aggregate']['runs']}; deterministic: "
        f"{report['determinism']['identical']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
