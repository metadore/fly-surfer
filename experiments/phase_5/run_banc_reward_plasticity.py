"""Reward-modulated synaptic plasticity on the real BANC graph.

The runner composes existing components and adds no new simulator:

    BANC v888 graph + Phase 4G sign/weight policy
        -> PlasticSimulator (LIF, three-factor rule, eligibility traces)
        -> RewardStream / RewardModulation (declared experimental rewards)
        -> WeightState learned deltas + checkpoint
        -> post-update replay
        -> Phase 4 motor activity recorder and decoder

Reward events are declared experimental inputs. No game was played and no
outcome was observed. Weight changes are transformed structural synapse counts
in pA, not conductances and not biological learning.

Conditions:
    baseline             eta = 0, no reward, traces enabled
    no_plasticity        eta = 0, identical reward events (control)
    reward_modulated     eta > 0, identical reward events
    reward_modulated_2   repeat for determinism
    post_update          eta = 0, no reward, weights reloaded from checkpoint
    post_control         eta = 0, no reward, original weights

Example::

    python experiments/phase_5/run_banc_reward_plasticity.py

The result is deterministic apart from timestamps and wall-clock fields.
"""

from __future__ import annotations

import argparse
import importlib.util
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

from brain.banc_graph import sha256_file  # noqa: E402
from brain.banc_simulator import BancStimulation  # noqa: E402
from plasticity.checkpoint import (  # noqa: E402
    graph_checksum,
    load_checkpoint,
    policy_digest,
    save_checkpoint,
)
from plasticity.diagnostics import summarize_updates  # noqa: E402
from plasticity.modulation import (  # noqa: E402
    ModulationConfig,
    ModulationRewardProvider,
    RewardModulation,
    RewardStream,
)
from plasticity.plastic_simulator import PlasticSimulator  # noqa: E402
from plasticity.rules import RuleConfig, ThreeFactorRule  # noqa: E402
from plasticity.traces import TraceConfig  # noqa: E402
from plasticity.weights import WeightBounds, WeightState  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "plasticity_banc.yaml"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "phase_5"
    / "banc_reward_plasticity.json"
)
DEFAULT_CHECKPOINT = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "phase_5"
    / "checkpoints"
    / "banc_reward_plasticity.npz"
)
DEFAULT_DECODER = PROJECT_ROOT / "configs" / "motor_decoder.yaml"
_PHASE4 = None


def phase4_runner():
    """Load the Phase 4 runner by path; ``experiments`` is not a package."""
    global _PHASE4
    if _PHASE4 is None:
        path = (
            PROJECT_ROOT
            / "experiments"
            / "phase_4"
            / "run_motor_output_pipeline.py"
        )
        spec = importlib.util.spec_from_file_location(
            "phase4_motor_output_pipeline", path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load the Phase 4 motor-output runner")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _PHASE4 = module
    return _PHASE4


def load_experiment_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("experiment config must be a mapping")

    graph = payload.get("graph")
    simulation = payload.get("simulation")
    probe = payload.get("probe")
    reward = payload.get("reward")
    plasticity = payload.get("plasticity")
    for name, block in (
        ("graph", graph),
        ("simulation", simulation),
        ("probe", probe),
        ("reward", reward),
        ("plasticity", plasticity),
    ):
        if not isinstance(block, dict):
            raise ValueError(f"{name} must be a mapping")
    if int(graph.get("threshold", -1)) not in (1, 5, 10):
        raise ValueError("graph.threshold must be 1, 5 or 10")
    for key in ("dt_ms", "duration_ms", "max_recorded_spikes"):
        value = float(simulation.get(key, 0))
        if value <= 0:
            raise ValueError(f"simulation.{key} must be positive")
    if float(probe.get("end_ms", 0)) <= float(probe.get("start_ms", 0)):
        raise ValueError("probe.end_ms must exceed probe.start_ms")
    if int(probe.get("count", 0)) < 1:
        raise ValueError("probe.count must be positive")
    if float(plasticity.get("eta", 0)) < 0:
        raise ValueError("plasticity.eta must be non-negative")
    if float(plasticity.get("control_eta", -1)) != 0.0:
        raise ValueError("plasticity.control_eta must be exactly 0.0")
    events = reward.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("reward.events must be a non-empty list")
    return payload


def build_weight_state(graph, policy, plasticity: dict) -> WeightState:
    bounds = WeightBounds.from_config(plasticity.get("bounds", {}))
    return WeightState(graph, policy, bounds)


def build_trace_config(plasticity: dict) -> TraceConfig:
    return TraceConfig({"traces": plasticity.get("traces", {})})


def build_provider(reward: dict, modulation: dict) -> ModulationRewardProvider:
    stream = RewardStream(
        reward["events"],
        provenance=str(reward.get("provenance", "")),
        classification=str(reward.get("classification", "")),
    )
    return ModulationRewardProvider(
        stream, RewardModulation(ModulationConfig.from_config(modulation))
    )


def run_condition(
    setup: dict,
    config: dict,
    *,
    label: str,
    weight_state: WeightState,
    eta: float,
    provider: ModulationRewardProvider | None,
    enable_traces: bool,
    probe: np.ndarray,
) -> dict:
    simulation = config["simulation"]
    probe_cfg = config["probe"]
    stimulation = BancStimulation(
        np.asarray(probe, dtype=np.int64),
        float(probe_cfg["current_pa"]),
        float(probe_cfg["start_ms"]),
        float(probe_cfg["end_ms"]),
        label=f"phase5:{label}",
    )
    simulator = PlasticSimulator(
        setup["graph"],
        setup["policy"],
        weight_state=weight_state,
        rule=ThreeFactorRule(
            RuleConfig(eta=float(eta), update_cadence="reward_event"),
            weight_state,
        ),
        trace_config=build_trace_config(config["plasticity"]),
        enable_traces=bool(enable_traces),
        reward_provider=provider,
        neuron_params=setup["neuron_params"],
        dt_ms=float(simulation["dt_ms"]),
        duration_ms=float(simulation["duration_ms"]),
        seed=int(simulation["seed"]),
        background_current_pa=float(simulation.get("background_current_pa", 0.0)),
        noise_std_pa=float(simulation.get("noise_std_pa", 0.0)),
        stimulation=stimulation,
        max_recorded_spikes=int(simulation["max_recorded_spikes"]),
        tau_exc_ms=float(simulation.get("tau_exc_ms", 5.0)),
        tau_inh_ms=float(simulation.get("tau_inh_ms", 8.0)),
        delay_ms=float(simulation.get("delay_ms", 1.0)),
    )
    started = time.perf_counter()
    result = simulator.run()
    return {
        "label": label,
        "eta": float(eta),
        "provider": provider,
        "result": result,
        "runtime_s": round(time.perf_counter() - started, 3),
    }


def weight_change_statistics(state: WeightState) -> dict:
    delta = state.delta_exc.astype(np.float64) + state.delta_inh.astype(np.float64)
    changed = delta != 0
    values = delta[changed]
    if values.size:
        absolute = np.abs(values)
        percentiles = {
            str(p): round(float(np.percentile(absolute, p)), 9)
            for p in (50, 90, 99, 100)
        }
        counts, edges = np.histogram(values, bins=10)
        histogram = {
            "bin_edges_pa": [round(float(value), 6) for value in edges],
            "counts": [int(value) for value in counts],
        }
        stats = {
            "sum_pa": round(float(values.sum()), 9),
            "mean_signed_pa": round(float(values.mean()), 9),
            "mean_abs_pa": round(float(absolute.mean()), 9),
            "max_abs_pa": round(float(absolute.max()), 9),
            "positive_changes": int(np.count_nonzero(values > 0)),
            "negative_changes": int(np.count_nonzero(values < 0)),
            "abs_percentiles_pa": percentiles,
            "histogram": histogram,
        }
    else:
        stats = {
            "sum_pa": 0.0,
            "mean_signed_pa": 0.0,
            "mean_abs_pa": 0.0,
            "max_abs_pa": 0.0,
            "positive_changes": 0,
            "negative_changes": 0,
            "abs_percentiles_pa": {str(p): 0.0 for p in (50, 90, 99, 100)},
            "histogram": {"bin_edges_pa": [], "counts": []},
        }
    return {
        "n_plastic_edges": int(state.n_plastic),
        "n_changed_edges": int(values.size),
        "changed_share_of_plastic": round(
            float(values.size) / max(1, state.n_plastic), 9
        ),
        **stats,
        "bounds": state.bounds.describe(),
        "n_update_calls": int(state.n_update_calls),
        "cumulative_clamp_hits": int(state.clamp_hits_total),
        "cumulative_update_clips": int(state.update_clip_hits_total),
        "digests": {
            "structural": state.structural_digest(),
            "initial": state.initial_digest(),
            "learned_delta": state.delta_digest(),
            "effective": state.effective_digest(),
        },
    }


def _state_counts(outputs) -> dict:
    counts: dict[str, int] = {}
    for output in outputs:
        counts[output.state] = counts.get(output.state, 0) + 1
    return dict(sorted(counts.items()))


def activity_block(
    setup: dict,
    result,
    probe: np.ndarray,
    *,
    decode_start_ms: float,
    decode_end_ms: float,
) -> dict:
    from motor.action_decoder import GameActionDecoder
    from motor.activity_recorder import MotorActivityRecorder

    graph = setup["graph"]
    populations = setup["populations"]
    recorder = MotorActivityRecorder(
        result.recorder,
        populations,
        setup["nodes"],
        graph=graph,
        stimulated_indices=probe,
    )
    decoder = GameActionDecoder(populations, setup["decoder_config"])
    outputs = decoder.decode_series(
        result.recorder.spike_times_ms,
        result.recorder.spike_neuron_indices,
        decode_start_ms,
        decode_end_ms,
    )
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    motor = np.asarray(populations.motor_mask, dtype=bool)
    stimulated_mask = np.zeros(int(graph.n_nodes), dtype=bool)
    stimulated_mask[np.asarray(probe, dtype=np.int64)] = True
    return {
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
                "unassigned_motor",
                "left_motor",
                "right_motor",
                "jump_motor",
            )
        },
        "window": recorder.time_window(
            decode_start_ms, decode_end_ms
        ).as_dict(),
        "decoder_outputs": [output.as_dict() for output in outputs],
        "decoded_state_counts": _state_counts(outputs),
        "spike_hash": result.spike_hash,
    }


def condition_record(
    setup: dict,
    config: dict,
    run: dict,
    probe: np.ndarray,
    *,
    duration_ms: float,
) -> dict:
    probe_cfg = config["probe"]
    decode_end = min(float(probe_cfg.get("decode_end_ms", duration_ms)), duration_ms)
    decode_start = min(
        float(probe_cfg.get("decode_start_ms", probe_cfg["start_ms"])),
        max(0.0, decode_end - float(config["simulation"]["dt_ms"])),
    )
    if decode_end <= decode_start:
        raise ValueError("simulation duration is too short to decode a window")
    result = run["result"]
    block = activity_block(
        setup,
        result,
        probe,
        decode_start_ms=decode_start,
        decode_end_ms=decode_end,
    )
    provider = run["provider"]
    return {
        "label": run["label"],
        "eta": run["eta"],
        "spike_hash": result.spike_hash,
        "runtime_s": run["runtime_s"],
        "activity": block["activity"],
        "populations": block["populations"],
        "decode_window": block["window"],
        "decoder_outputs": block["decoder_outputs"],
        "decoded_state_counts": block["decoded_state_counts"],
        "weights": weight_change_statistics(result.weight_state),
        "updates": summarize_updates(result.update_reports),
        "reward_provider": None if provider is None else provider.describe(),
        "modulation_series": (
            None
            if provider is None
            else {
                "sample_interval_ms": 1.0,
                "values": provider.modulation_series(duration_ms, 1.0),
            }
        ),
        "simulation": result.summary["simulation"],
        "diagnostics": result.summary["diagnostics"],
    }


def _per_neuron_times(result) -> dict[int, np.ndarray]:
    recorder = result.recorder
    times = np.asarray(recorder.spike_times_ms, dtype=np.float64)
    indices = np.asarray(recorder.spike_neuron_indices, dtype=np.int64)
    order = np.lexsort((times, indices))
    sorted_times = times[order]
    sorted_indices = indices[order]
    unique, starts = np.unique(sorted_indices, return_index=True)
    bounds = np.append(starts, sorted_indices.size)
    return {
        int(neuron): sorted_times[bounds[position] : bounds[position + 1]]
        for position, neuron in enumerate(unique)
    }


def spike_sequence_difference(reference_result, candidate_result) -> dict:
    """Per-neuron spike count and timing differences between two runs."""
    reference = _per_neuron_times(reference_result)
    candidate = _per_neuron_times(candidate_result)
    count_changes: dict[str, int] = {}
    timing_changes: dict[str, float] = {}
    empty = np.empty(0, dtype=np.float64)
    for neuron in sorted(set(reference) | set(candidate)):
        left = reference.get(neuron, empty)
        right = candidate.get(neuron, empty)
        if left.size != right.size:
            count_changes[str(neuron)] = int(right.size - left.size)
        elif left.size and not np.array_equal(left, right):
            timing_changes[str(neuron)] = round(
                float(np.abs(left - right).max()), 6
            )
    return {
        "n_neurons_with_count_change": len(count_changes),
        "count_changes_by_neuron": count_changes,
        "n_neurons_with_timing_change": len(timing_changes),
        "timing_changes_by_neuron_ms": timing_changes,
        "max_abs_timing_shift_ms": (
            0.0 if not timing_changes else max(timing_changes.values())
        ),
    }


def compare(reference: dict, candidate: dict) -> dict:
    keys = (
        "total_spikes",
        "motor_spikes",
        "motor_active_neurons",
        "non_motor_spikes",
        "stimulated_spikes",
        "downstream_spikes",
        "active_neurons",
    )
    window_states = [
        (item["window_start_ms"], item["state"])
        for item in candidate["decoder_outputs"]
    ]
    reference_states = [
        (item["window_start_ms"], item["state"])
        for item in reference["decoder_outputs"]
    ]
    mismatches = sum(
        1
        for left, right in zip(reference_states, window_states)
        if left != right
    )
    population_delta = {}
    for name in reference["populations"]:
        left = reference["decode_window"]["populations"].get(name, {})
        right = candidate["decode_window"]["populations"].get(name, {})
        population_delta[name] = int(right.get("spikes", 0)) - int(
            left.get("spikes", 0)
        )
    return {
        "reference": reference["label"],
        "candidate": candidate["label"],
        "spike_hash_equal": reference["spike_hash"] == candidate["spike_hash"],
        "activity_delta": {
            key: int(candidate["activity"][key]) - int(reference["activity"][key])
            for key in keys
        },
        "population_spike_delta": population_delta,
        "decoded_state_counts": {
            "reference": reference["decoded_state_counts"],
            "candidate": candidate["decoded_state_counts"],
        },
        "decoded_state_counts_equal": (
            reference["decoded_state_counts"] == candidate["decoded_state_counts"]
        ),
        "decoder_window_mismatches": int(mismatches),
        "weight_digest_equal": (
            reference["weights"]["digests"]["learned_delta"]
            == candidate["weights"]["digests"]["learned_delta"]
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = Path(args.output)
    checkpoint_path = Path(args.checkpoint)
    for path in (output, checkpoint_path):
        if path.exists() and not args.force:
            print(
                f"refusing to overwrite {path}; pass --force to replace it",
                file=sys.stderr,
            )
            return 2

    started = time.perf_counter()
    config = load_experiment_config(args.config)
    phase4 = phase4_runner()
    setup = phase4.load_setup(int(config["graph"]["threshold"]))
    graph = setup["graph"]
    probe, probe_metadata = phase4.select_probe_indices(
        graph,
        setup["nodes"],
        setup["policy"],
        setup["populations"],
        count=int(config["probe"]["count"]),
        selection=str(config["probe"]["selection"]),
        seed=int(config["simulation"]["seed"]),
    )
    reference = None
    if (
        config["probe"]["selection"] == "vnc_intrinsic_ranked"
        and int(config["probe"]["count"]) == 64
    ):
        reference = phase4.verify_phase4g_reference(graph, probe)

    duration_ms = float(config["simulation"]["duration_ms"])
    eta = float(config["plasticity"]["eta"])
    control_eta = float(config["plasticity"]["control_eta"])
    structural_before = graph_checksum(graph)
    policy_before = policy_digest(setup["policy"])

    def fresh_state() -> WeightState:
        return build_weight_state(graph, setup["policy"], config["plasticity"])

    def fresh_provider() -> ModulationRewardProvider:
        return build_provider(config["reward"], config["modulation"])

    runs = {}
    runs["baseline"] = run_condition(
        setup,
        config,
        label="baseline",
        weight_state=fresh_state(),
        eta=0.0,
        provider=None,
        enable_traces=True,
        probe=probe,
    )
    runs["no_plasticity_control"] = run_condition(
        setup,
        config,
        label="no_plasticity_control",
        weight_state=fresh_state(),
        eta=control_eta,
        provider=fresh_provider(),
        enable_traces=True,
        probe=probe,
    )
    runs["reward_modulated"] = run_condition(
        setup,
        config,
        label="reward_modulated",
        weight_state=fresh_state(),
        eta=eta,
        provider=fresh_provider(),
        enable_traces=True,
        probe=probe,
    )
    runs["reward_modulated_repeat"] = run_condition(
        setup,
        config,
        label="reward_modulated_repeat",
        weight_state=fresh_state(),
        eta=eta,
        provider=fresh_provider(),
        enable_traces=True,
        probe=probe,
    )

    plastic_state = runs["reward_modulated"]["result"].weight_state
    checkpoint_meta = save_checkpoint(
        checkpoint_path,
        weight_state=plastic_state,
        graph=graph,
        policy=setup["policy"],
        config=config,
        step=int(runs["reward_modulated"]["result"].n_steps),
        seed=int(config["simulation"]["seed"]),
        metadata={
            "experiment": "phase5_banc_reward_plasticity",
            "probe_root_ids": [int(value) for value in graph.root_ids[probe]],
            "reward_source": "declared experimental input",
        },
    )
    post_state = fresh_state()
    restored = load_checkpoint(
        checkpoint_path,
        weight_state=post_state,
        graph=graph,
        policy=setup["policy"],
    )
    runs["post_update"] = run_condition(
        setup,
        config,
        label="post_update",
        weight_state=post_state,
        eta=0.0,
        provider=None,
        enable_traces=False,
        probe=probe,
    )
    runs["post_control"] = run_condition(
        setup,
        config,
        label="post_control",
        weight_state=fresh_state(),
        eta=0.0,
        provider=None,
        enable_traces=False,
        probe=probe,
    )

    records = {
        name: condition_record(setup, config, run, probe, duration_ms=duration_ms)
        for name, run in runs.items()
    }
    plastic = records["reward_modulated"]
    repeat = records["reward_modulated_repeat"]
    control = records["no_plasticity_control"]
    baseline = records["baseline"]
    post = records["post_update"]
    post_control = records["post_control"]

    structural_after = graph_checksum(graph)
    policy_after = policy_digest(setup["policy"])
    provider = runs["reward_modulated"]["provider"]
    control_provider = runs["no_plasticity_control"]["provider"]

    reproducibility = {
        "seed": int(config["simulation"]["seed"]),
        "plastic_repeat_spike_hash_equal": (
            plastic["spike_hash"] == repeat["spike_hash"]
        ),
        "plastic_repeat_learned_digest_equal": (
            plastic["weights"]["digests"]["learned_delta"]
            == repeat["weights"]["digests"]["learned_delta"]
        ),
        "plastic_repeat_effective_digest_equal": (
            plastic["weights"]["digests"]["effective"]
            == repeat["weights"]["digests"]["effective"]
        ),
        "plastic_repeat_modulation_digest_equal": (
            provider.modulation.digest()
            == runs["reward_modulated_repeat"]["provider"].modulation.digest()
        ),
        "control_weights_unchanged": (
            control["weights"]["n_changed_edges"] == 0
            and control["weights"]["digests"]["learned_delta"]
            == baseline["weights"]["digests"]["learned_delta"]
        ),
        "control_spike_hash_equals_baseline": (
            control["spike_hash"] == baseline["spike_hash"]
        ),
        "post_control_spike_hash_equals_baseline": (
            post_control["spike_hash"] == baseline["spike_hash"]
        ),
        "checkpoint_reloaded": True,
        "checkpoint_reload_digest_equal": (
            restored["weight_digest"]
            == plastic["weights"]["digests"]["learned_delta"]
        ),
        "structural_checksum_before": structural_before,
        "structural_checksum_after": structural_after,
        "structural_unchanged": structural_before == structural_after,
        "policy_digest_before": policy_before,
        "policy_digest_after": policy_after,
        "policy_unchanged": policy_before == policy_after,
    }

    payload = {
        "phase": "5",
        "experiment": "BANC reward-modulated synaptic plasticity",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "inputs": {
            "experiment_config": str(
                Path(args.config).resolve().relative_to(PROJECT_ROOT)
            ).replace("\\", "/"),
            "experiment_config_sha256": sha256_file(Path(args.config)),
            "graph_sha256": sha256_file(setup["graph_path"]),
            "node_table_sha256": sha256_file(phase4.NODES_PATH),
            "policy_config_sha256": sha256_file(phase4.POLICY_CONFIG),
            "decoder_config_sha256": sha256_file(phase4.DECODER_CONFIG),
            "neuron_config_sha256": sha256_file(phase4.NEURON_CONFIG),
        },
        "graph": {
            "source": "BANC v888",
            "threshold": int(graph.threshold),
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "n_isolated": int(graph.n_isolated),
            "structural_checksum": structural_before,
            "policy_digest": policy_before,
        },
        "probe": {
            **probe_metadata,
            "current_pa": float(config["probe"]["current_pa"]),
            "start_ms": float(config["probe"]["start_ms"]),
            "end_ms": float(config["probe"]["end_ms"]),
            "phase_4g_reference": reference,
        },
        "reward": {
            "stream": provider.stream.describe(),
            "modulation_config": provider.modulation.config.describe(),
            "plastic_run_provider": provider.describe(),
            "control_run_provider": None
            if control_provider is None
            else {
                "n_update_steps": control_provider.n_update_steps,
                "n_steps_without_reward": control_provider.n_steps_without_reward,
                "n_missing_events": control_provider.n_missing_events,
                "emitted_modulation": round(
                    float(control_provider.emitted_modulation), 9
                ),
            },
            "source_classification": (
                "declared experimental reward inputs; not gameplay-derived "
                "outcomes and not a biological dopamine measurement"
            ),
        },
        "plasticity": {
            "rule": "delta_w = eta * modulation * eligibility",
            "eta": eta,
            "control_eta": control_eta,
            "bounds": WeightBounds.from_config(
                config["plasticity"].get("bounds", {})
            ).describe(),
            "traces": build_trace_config(config["plasticity"]).describe(),
            "initial_weight_digest": baseline["weights"]["digests"]["initial"],
            "checkpoint": {
                "path": str(checkpoint_path.resolve().relative_to(PROJECT_ROOT)).replace(
                    "\\", "/"
                ),
                "format_version": checkpoint_meta["format_version"],
                "delta_digest": checkpoint_meta["delta_digest"],
                "effective_digest": restored["effective_digest"],
                "reloaded": True,
            },
        },
        "conditions": records,
        "weight_changes": {
            "n_eligible_connections": plastic["weights"]["n_plastic_edges"],
            "n_changed_connections": plastic["weights"]["n_changed_edges"],
            "mean_abs_change_pa": plastic["weights"]["mean_abs_pa"],
            "max_abs_change_pa": plastic["weights"]["max_abs_pa"],
            "positive_changes": plastic["weights"]["positive_changes"],
            "negative_changes": plastic["weights"]["negative_changes"],
            "update_events": plastic["updates"]["n_update_events"],
            "update_events_with_changes": plastic["updates"]["n_changed_events"],
        },
        "comparison": {
            name: {
                **compare(baseline, records[candidate]),
                "spike_sequence_difference": spike_sequence_difference(
                    runs["baseline"]["result"], runs[candidate]["result"]
                ),
            }
            for name, candidate in (
                ("reward_modulated_training_vs_baseline", "reward_modulated"),
                ("reward_modulated_post_update_vs_baseline", "post_update"),
                ("no_plasticity_control_vs_baseline", "no_plasticity_control"),
                ("post_control_vs_baseline", "post_control"),
            )
        },
        "reproducibility": reproducibility,
        "scientific_status": [
            "Reward events are declared experimental inputs; no game was played and no gameplay reward was observed.",
            "Modulation is a computational decaying scalar, not a biological dopamine measurement.",
            "Weights are transformed structural synapse counts in pA, not physiological conductances.",
            "A nonzero weight change is not evidence of learning.",
            "The post-update comparison reports whether the changed weights altered subsequent spike activity; it does not establish a learned behaviour.",
            "The probe is a structural stimulation of non-motor neurons; no motor neuron was stimulated and no spike was injected.",
            "BANC and FAFB were not merged; BANC neuron identities are used as published.",
        ],
        "reproduce": (
            "python experiments/phase_5/run_banc_reward_plasticity.py"
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
        "checkpoint": str(checkpoint_path),
        "graph": payload["graph"],
        "probe": {
            "n_stimulated": int(probe.size),
            "root_ids_match_phase_4g": None
            if reference is None
            else reference["matches_recorded_root_ids"],
        },
        "reward_events": payload["reward"]["stream"]["counts"],
        "weight_changes": payload["weight_changes"],
        "activity": {
            name: records[name]["activity"]
            for name in (
                "baseline",
                "no_plasticity_control",
                "reward_modulated",
                "post_update",
                "post_control",
            )
        },
        "decoded_state_counts": {
            name: records[name]["decoded_state_counts"]
            for name in (
                "baseline",
                "no_plasticity_control",
                "reward_modulated",
                "post_update",
            )
        },
        "post_update_vs_baseline": payload["comparison"][
            "reward_modulated_post_update_vs_baseline"
        ],
        "reproducibility": reproducibility,
        "wall_time_s": payload["wall_time_s"],
    }
    print(json.dumps(summary, indent=1))

    required = (
        reproducibility["control_weights_unchanged"],
        reproducibility["control_spike_hash_equals_baseline"],
        reproducibility["plastic_repeat_spike_hash_equal"],
        reproducibility["plastic_repeat_learned_digest_equal"],
        reproducibility["checkpoint_reload_digest_equal"],
        reproducibility["structural_unchanged"],
        reproducibility["policy_unchanged"],
    )
    if not all(required):
        print("one or more reproducibility checks failed", file=sys.stderr)
        return 1
    if plastic["weights"]["n_changed_edges"] == 0:
        print("reward-modulated run changed no weights", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
