"""Phase 5D unit experiments: separated weights, rule and eta = 0 equivalence.

Runs four things and records every result, including negative ones:

1. toy rule arithmetic on a synthetic substrate (exact expected deltas);
2. eta = 0 spike-hash equality between ``BancSimulator`` and
   ``PlasticSimulator``, with traces enabled and disabled;
3. a nonzero-eta plastic smoke run, with sign/bound/structural invariants;
4. checkpoint round-trip, wrong-graph rejection and tamper rejection;
5. the same eta = 0 equality on the real BANC t5 graph, with and without
   background noise.

Writes ``experiments/results/phase_5d/plasticity_unit_experiments.json``.
The fixed-weight simulator is never modified and remains the oracle.

Usage:
  python -m experiments.phase_5.run_plasticity_unit_experiments
  python -m experiments.phase_5.run_plasticity_unit_experiments --quick
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import BancConnectome  # noqa: E402
from brain.banc_simulator import BancSimulator, BancStimulation  # noqa: E402
from brain.banc_synapse_policy import (  # noqa: E402
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)
from experiments.phase_4h.common import (  # noqa: E402
    integrity_snapshot,
    process_memory,
    software_versions,
)
from plasticity.checkpoint import (  # noqa: E402
    graph_checksum,
    load_checkpoint,
    save_checkpoint,
)
from plasticity.config import load_plasticity_config  # noqa: E402
from plasticity.diagnostics import spike_hash, summarize_updates  # noqa: E402
from plasticity.plastic_simulator import PlasticSimulator  # noqa: E402
from plasticity.rules import RuleConfig, ThreeFactorRule  # noqa: E402
from plasticity.synthetic import synthetic_substrate  # noqa: E402
from plasticity.weights import WeightBounds, WeightState  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"
POLICY_CONFIG = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
GRAPH_T5 = PROJECT_ROOT / "datasets" / "processed" / "banc_v888" / "banc_graph_t5.npz"
NODES_PATH = PROJECT_ROOT / "datasets" / "processed" / "banc_v888" / "banc_nodes.csv.gz"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase_5d"
RESULT_PATH = RESULTS_DIR / "plasticity_unit_experiments.json"
BANC_THRESHOLD = 5
DT_MS = 0.5


class StepRewards:
    """Reward on named steps; ``None`` on all other steps (no event)."""

    def __init__(self, rewards: dict[int, float]) -> None:
        self.rewards = dict(rewards)
        self._seen: set[int] = set()

    def reset(self) -> None:
        self._seen.clear()

    def step(self, step: int, time_ms: float, context=None):
        del time_ms, context
        if step in self.rewards and step not in self._seen:
            self._seen.add(step)
            return float(self.rewards[step])
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_json(value) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, default=_json_default), encoding="utf-8")
    tmp.replace(path)


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


# ---------------------------------------------------------------------------
# 1. toy rule arithmetic
# ---------------------------------------------------------------------------


def toy_rule_check(config) -> dict:
    graph, policy = synthetic_substrate(n_nodes=16, n_edges=48, seed=21)
    state = WeightState(graph, policy, WeightBounds(max_abs_update_pa=None))
    rule = ThreeFactorRule(RuleConfig(eta=0.1), state)
    exc = np.flatnonzero(state.sign_class == 1)[:3]
    inh = np.flatnonzero(state.sign_class == -1)[:2]
    edges = np.concatenate([exc, inh])
    traces = np.array([1.0, 2.0, 3.0, 1.0, 0.5])
    rpe = -2.0
    expected = 0.1 * rpe * traces
    report = rule.apply(5, edges, traces, delta_t=rpe)
    applied = state.delta_exc[exc].astype(np.float64).tolist() + state.delta_inh[
        inh
    ].astype(np.float64).tolist()
    error = float(np.max(np.abs(np.asarray(applied) - expected)))
    eta_zero_rule = ThreeFactorRule(RuleConfig(eta=0.0), state)
    before = state.digest()
    zero_report = eta_zero_rule.apply(6, edges, traces, delta_t=1e6)
    return {
        "n_edges_updated": int(report.n_updates),
        "expected_deltas_pa": expected.tolist(),
        "applied_deltas_pa": applied,
        "max_abs_error_pa": error,
        "arithmetic_matches_declared_rule": bool(error < 1e-6),
        "negative_rpe_reduced_weights": bool(
            np.all(np.asarray(applied) < 0)
        ),
        "eta_zero_no_op": bool(zero_report.n_updates == 0 and state.digest() == before),
        "bounds": state.bounds.describe(),
    }


# ---------------------------------------------------------------------------
# 2/3. synthetic simulations
# ---------------------------------------------------------------------------


def synthetic_equivalence(config, *, quick: bool) -> dict:
    duration_ms = 30.0 if quick else 50.0
    n_nodes = 48 if quick else 64
    n_edges = 500 if quick else 800
    n_stim = 12 if quick else 16
    seed = 7
    graph, policy = synthetic_substrate(n_nodes=n_nodes, n_edges=n_edges, seed=5)
    stimulation = BancStimulation(np.arange(n_stim), 500.0, 0.0, duration_ms)
    n_steps = int(round(duration_ms / DT_MS))
    rewards = {n_steps // 3: 1.0, n_steps - 1: -1.0}
    common = {
        "dt_ms": DT_MS,
        "duration_ms": duration_ms,
        "seed": seed,
        "noise_std_pa": 25.0,
        "stimulation": stimulation,
        "max_recorded_spikes": 100_000,
    }
    started = time.perf_counter()
    fixed = BancSimulator(graph, policy, **common).run()
    fixed_s = time.perf_counter() - started
    fixed_hash = spike_hash(fixed.recorder)
    del fixed
    gc.collect()

    rows = {}
    for label, enable_traces in (("traces_enabled", True), ("traces_disabled", False)):
        state = WeightState(graph, policy)
        simulator = PlasticSimulator(
            graph,
            policy,
            weight_state=state,
            rule=ThreeFactorRule(RuleConfig(eta=0.0), state),
            trace_config=config.traces if enable_traces else None,
            enable_traces=enable_traces,
            reward_provider=StepRewards(rewards),
            **common,
        )
        started = time.perf_counter()
        result = simulator.run()
        runtime = time.perf_counter() - started
        rows[label] = {
            "spike_hash": result.spike_hash,
            "fixed_spike_hash": fixed_hash,
            "hashes_identical": bool(result.spike_hash == fixed_hash),
            "n_spikes": int(result.recorder.n_spikes),
            "n_transmissions": int(
                result.summary["synaptic_transmission"]["spike_transmissions"]
            ),
            "n_update_events": len(result.update_reports),
            "n_updates": int(sum(item.n_updates for item in result.update_reports)),
            "weight_delta_digest": state.delta_digest(),
            "initial_weight_digest": state.initial_digest(),
            "effective_equals_initial": bool(
                np.array_equal(state.effective_exc, state.initial_exc)
                and np.array_equal(state.effective_inh, state.initial_inh)
            ),
            "runtime_s": round(runtime, 4),
            "traces": result.summary["plasticity"]["traces"],
        }
        del simulator, state
        gc.collect()
    return {
        "graph": {
            "n_nodes": graph.n_nodes,
            "n_edges": graph.n_edges,
            "n_plastic": int(
                ((policy.edge_exc_weight > 0) | (policy.edge_inh_weight > 0)).sum()
            ),
            "seed": 5,
        },
        "simulation": {
            "duration_ms": duration_ms,
            "n_steps": n_steps,
            "dt_ms": DT_MS,
            "seed": seed,
            "noise_std_pa": 25.0,
            "stimulated_neurons": n_stim,
            "stimulation_pa": 500.0,
            "reward_steps": sorted(rewards),
        },
        "fixed_runtime_s": round(fixed_s, 4),
        "conditions": rows,
        "all_hashes_identical": bool(
            all(row["hashes_identical"] for row in rows.values())
        ),
    }


def synthetic_plastic_smoke(config, *, quick: bool) -> dict:
    duration_ms = 60.0 if quick else 80.0
    n_nodes = 48 if quick else 64
    n_edges = 500 if quick else 800
    n_stim = 12 if quick else 16
    n_steps = int(round(duration_ms / DT_MS))
    rewards = {n_steps // 3: 1.0, n_steps - 1: -1.0}
    graph, policy = synthetic_substrate(n_nodes=n_nodes, n_edges=n_edges, seed=5)
    state = WeightState(graph, policy, config.bounds)
    rule = ThreeFactorRule(
        RuleConfig(eta=0.02, update_cadence="reward_event"), state
    )
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=config.traces,
        reward_provider=StepRewards(rewards),
        dt_ms=DT_MS,
        duration_ms=duration_ms,
        seed=7,
        noise_std_pa=40.0,
        stimulation=BancStimulation(np.arange(n_stim), 500.0, 0.0, duration_ms),
        max_recorded_spikes=100_000,
    )
    started = time.perf_counter()
    result = simulator.run()
    runtime = time.perf_counter() - started
    invariants = state.assert_invariants()
    description = state.describe()
    updates = summarize_updates(result.update_reports)
    return {
        "configuration": {
            "eta": rule.eta,
            "bounds": config.bounds.describe(),
            "duration_ms": duration_ms,
            "n_steps": n_steps,
            "reward_steps": sorted(rewards),
            "reward_magnitudes": [rewards[key] for key in sorted(rewards)],
            "stimulated_neurons": n_stim,
            "noise_std_pa": 40.0,
        },
        "n_spikes": int(result.recorder.n_spikes),
        "spike_hash": result.spike_hash,
        "runtime_s": round(runtime, 4),
        "steps_per_second": round(n_steps / runtime, 1) if runtime else None,
        "update_summary": {key: value for key, value in updates.items() if key != "records"},
        "update_records": updates["records"],
        "traces": result.summary["plasticity"]["traces"],
        "weights": {key: value for key, value in description.items() if key != "updates"},
        "invariants": invariants,
        "structural_digest": state.structural_digest(),
        "initial_digest": state.initial_digest(),
        "delta_digest": state.delta_digest(),
        "effective_digest": state.effective_digest(),
        "sign_preserved": bool(
            np.all(state.sign_class[state.delta_exc != 0] == 1)
            and np.all(state.sign_class[state.delta_inh != 0] == -1)
            and np.all(state.effective_exc >= 0)
            and np.all(state.effective_inh >= 0)
        ),
        "structural_counts_immutable": bool(
            np.array_equal(state.structural_count, graph.edge_weight)
        ),
        "memory": result.summary["memory"],
        "process_memory": process_memory(),
    }


# ---------------------------------------------------------------------------
# 4. checkpoints
# ---------------------------------------------------------------------------


def checkpoint_check(config) -> dict:
    graph, policy = synthetic_substrate(n_nodes=24, n_edges=120, seed=9)
    state = WeightState(graph, policy, config.bounds)
    rule = ThreeFactorRule(RuleConfig(eta=0.05), state)
    duration_ms = 25.0
    n_steps = int(round(duration_ms / DT_MS))
    simulator = PlasticSimulator(
        graph,
        policy,
        weight_state=state,
        rule=rule,
        trace_config=config.traces,
        reward_provider=StepRewards({n_steps // 3: 1.0, n_steps - 1: -1.0}),
        dt_ms=DT_MS,
        duration_ms=duration_ms,
        seed=4,
        stimulation=BancStimulation(np.array([0, 1, 2]), 500.0, 0.0, duration_ms),
        max_recorded_spikes=50_000,
    )
    result = simulator.run()
    directory = Path(tempfile.mkdtemp(prefix="phase5d_checkpoint_"))
    try:
        changed_from_run = int(state.describe()["n_changed_edges"])
        # A round-trip over an all-zero delta layer would not exercise the
        # restore path. Apply a small deterministic fixture update if the
        # simulation produced no coincidence at the reward steps.
        fixture_applied = False
        if changed_from_run == 0:
            edges = state.plastic_positions[:4]
            rule.apply(
                result.n_steps, edges, np.ones(edges.size), delta_t=1.0
            )
            fixture_applied = True
        path = directory / "checkpoint.npz"
        payload = save_checkpoint(
            path,
            weight_state=state,
            graph=graph,
            policy=policy,
            config=config.describe(),
            trace_store=simulator.engine.trace_store,
            step=result.n_steps,
            seed=4,
        )
        restored_state = WeightState(graph, policy, config.bounds)
        restored = PlasticSimulator(
            graph,
            policy,
            weight_state=restored_state,
            rule=ThreeFactorRule(RuleConfig(eta=0.05), restored_state),
            trace_config=config.traces,
            dt_ms=DT_MS,
            duration_ms=1.0,
            seed=4,
        )
        info = load_checkpoint(
            path,
            weight_state=restored_state,
            graph=graph,
            policy=policy,
            trace_store=restored.engine.trace_store,
        )
        round_trip_ok = bool(
            info["weight_digest"] == state.delta_digest()
            and info["effective_digest"] == state.effective_digest()
            and restored.engine.trace_store.digest()
            == simulator.engine.trace_store.digest()
        )

        other_graph, other_policy = synthetic_substrate(
            n_nodes=20, n_edges=80, seed=10
        )
        wrong_state = WeightState(other_graph, other_policy, config.bounds)
        try:
            load_checkpoint(
                path,
                weight_state=wrong_state,
                graph=other_graph,
                policy=other_policy,
            )
            wrong_graph_rejected = False
            wrong_graph_reason = "accepted"
        except ValueError as error:
            wrong_graph_rejected = True
            wrong_graph_reason = str(error)

        with np.load(path, allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
        tampered = arrays["delta_exc"].copy()
        tampered[np.flatnonzero(state.plastic)[0]] += 0.5
        arrays["delta_exc"] = tampered
        tampered_path = directory / "tampered.npz"
        np.savez_compressed(tampered_path, **arrays)
        fresh = WeightState(graph, policy, config.bounds)
        try:
            load_checkpoint(
                tampered_path, weight_state=fresh, graph=graph, policy=policy
            )
            tamper_rejected = False
            tamper_reason = "accepted"
        except ValueError as error:
            tamper_rejected = True
            tamper_reason = str(error)
        return {
            "n_update_events": len(result.update_reports),
            "n_changed_edges_from_run": changed_from_run,
            "fixture_update_applied": fixture_applied,
            "n_changed_edges_saved": int(state.describe()["n_changed_edges"]),
            "checkpoint_step": result.n_steps,
            "checkpoint_graph_checksum": payload["graph_checksum"],
            "expected_graph_checksum": graph_checksum(graph),
            "round_trip_ok": round_trip_ok,
            "traces_restored": bool(info["restored_traces"]),
            "wrong_graph_rejected": wrong_graph_rejected,
            "wrong_graph_reason": wrong_graph_reason,
            "tamper_rejected": tamper_rejected,
            "tamper_reason": tamper_reason,
            "tamper_left_state_untouched": bool(
                fresh.delta_digest() == WeightState(graph, policy).delta_digest()
            ),
        }
    finally:
        shutil.rmtree(directory, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5. BANC t5 eta = 0 equivalence
# ---------------------------------------------------------------------------


def load_banc_world():
    graph = BancConnectome.load(GRAPH_T5)
    nodes = pd.read_csv(NODES_PATH)
    with POLICY_CONFIG.open("r", encoding="utf-8") as handle:
        policy_payload = yaml.safe_load(handle)
    sign_policy = SignPolicy.from_config(policy_payload["transmitter_sign_policy"])
    weight_policy = WeightPolicy.from_config(policy_payload["weight_policy"]["primary"])
    policy = build_synapse_policy(graph, nodes, sign_policy, weight_policy)
    return graph, policy


def banc_equivalence(config, *, quick: bool) -> dict:
    if not GRAPH_T5.is_file() or not NODES_PATH.is_file():
        return {
            "available": False,
            "reason": "BANC t5 graph or node table is not present",
        }
    started = time.perf_counter()
    graph, policy = load_banc_world()
    load_s = time.perf_counter() - started
    duration_ms = 24.0 if quick else 30.0
    n_stim = 32 if quick else 64
    n_steps = int(round(duration_ms / DT_MS))
    stimulation = BancStimulation(
        np.arange(n_stim, dtype=np.int64), 300.0, 0.0, duration_ms
    )
    common = {
        "dt_ms": DT_MS,
        "duration_ms": duration_ms,
        "seed": 20261114,
        "stimulation": stimulation,
        "max_recorded_spikes": 500_000,
    }
    rows = {}
    for label, noise in (("no_noise", 0.0), ("background_noise", 25.0)):
        started = time.perf_counter()
        fixed = BancSimulator(graph, policy, noise_std_pa=noise, **common).run()
        fixed_runtime = time.perf_counter() - started
        fixed_hash = spike_hash(fixed.recorder)
        fixed_spikes = int(fixed.recorder.n_spikes)
        del fixed
        gc.collect()

        started = time.perf_counter()
        state = WeightState(graph, policy, config.bounds)
        construction_s = time.perf_counter() - started
        simulator = PlasticSimulator(
            graph,
            policy,
            weight_state=state,
            rule=ThreeFactorRule(RuleConfig(eta=0.0), state),
            trace_config=config.traces,
            reward_provider=StepRewards({n_steps // 2: 1.0, n_steps - 1: -1.0}),
            noise_std_pa=noise,
            **common,
        )
        started = time.perf_counter()
        result = simulator.run()
        plastic_runtime = time.perf_counter() - started
        rows[label] = {
            "noise_std_pa": noise,
            "fixed_spike_hash": fixed_hash,
            "plastic_spike_hash": result.spike_hash,
            "hashes_identical": bool(result.spike_hash == fixed_hash),
            "fixed_spikes": fixed_spikes,
            "plastic_spikes": int(result.recorder.n_spikes),
            "n_transmissions": int(
                result.summary["synaptic_transmission"]["spike_transmissions"]
            ),
            "n_update_events": len(result.update_reports),
            "n_updates": int(sum(item.n_updates for item in result.update_reports)),
            "weight_state_construction_s": round(construction_s, 4),
            "fixed_runtime_s": round(fixed_runtime, 4),
            "plastic_runtime_s": round(plastic_runtime, 4),
            "plastic_steps_per_second": round(n_steps / plastic_runtime, 1)
            if plastic_runtime
            else None,
            "delta_digest": state.delta_digest(),
            "initial_digest": state.initial_digest(),
            "effective_digest": state.effective_digest(),
            "effective_equals_initial": bool(
                np.array_equal(state.effective_exc, state.initial_exc)
                and np.array_equal(state.effective_inh, state.initial_inh)
            ),
            "structural_equals_graph": bool(
                np.array_equal(state.structural_count, graph.edge_weight)
            ),
            "memory": result.summary["memory"],
            "traces": result.summary["plasticity"]["traces"],
            "process_memory": process_memory(),
        }
        del simulator, state, result
        gc.collect()

    return {
        "available": True,
        "graph": {
            "path": relative(GRAPH_T5),
            "sha256": sha256_file(GRAPH_T5),
            "threshold": BANC_THRESHOLD,
            "n_nodes": int(graph.n_nodes),
            "n_edges": int(graph.n_edges),
            "n_synapses": int(graph.n_synapses),
            "n_plastic_edges": int(policy.signed_edges),
        },
        "simulation": {
            "duration_ms": duration_ms,
            "n_steps": n_steps,
            "seed": 20261114,
            "stimulated_neurons": n_stim,
            "stimulation_pa": 300.0,
            "reward_steps": [n_steps // 2, n_steps - 1],
        },
        "load_s": round(load_s, 4),
        "conditions": rows,
        "all_hashes_identical": bool(
            all(row["hashes_identical"] for row in rows.values())
        ),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="reduced sizes")
    parser.add_argument("--skip-banc", action="store_true")
    args = parser.parse_args(argv)

    config = load_plasticity_config(CONFIG_PATH)
    started = time.perf_counter()
    toy = toy_rule_check(config)
    equivalence = synthetic_equivalence(config, quick=args.quick)
    plastic = synthetic_plastic_smoke(config, quick=args.quick)
    checkpoint = checkpoint_check(config)
    banc = (
        {"available": False, "reason": "skipped by --skip-banc"}
        if args.skip_banc
        else banc_equivalence(config, quick=args.quick)
    )
    integrity = integrity_snapshot()

    checks = {
        "toy_rule_arithmetic": toy["arithmetic_matches_declared_rule"],
        "eta_zero_no_op": toy["eta_zero_no_op"],
        "synthetic_eta_zero_hashes": equivalence["all_hashes_identical"],
        "plastic_invariants": bool(
            all(plastic["invariants"].values())
            and plastic["sign_preserved"]
            and plastic["structural_counts_immutable"]
        ),
        "checkpoint_round_trip": checkpoint["round_trip_ok"],
        "checkpoint_wrong_graph_rejected": checkpoint["wrong_graph_rejected"],
        "checkpoint_tamper_rejected": checkpoint["tamper_rejected"],
        "banc_eta_zero_hashes": (
            banc.get("all_hashes_identical") if banc.get("available") else None
        ),
        "banc_conditions_produced_spikes": (
            all(
                row["fixed_spikes"] > 0 and row["plastic_spikes"] > 0
                for row in banc["conditions"].values()
            )
            if banc.get("available")
            else None
        ),
        "integrity": integrity["pass"],
    }
    failures = [name for name, ok in checks.items() if ok is False]
    payload = {
        "phase": "5D",
        "status": "complete" if not failures else "complete_with_failures",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": {
            "quick": bool(args.quick),
            "skip_banc": bool(args.skip_banc),
            "module": "experiments.phase_5.run_plasticity_unit_experiments",
        },
        "software": software_versions(),
        "config": {
            "path": relative(CONFIG_PATH),
            "sha256": sha256_file(CONFIG_PATH),
            "digest": digest_json(config.describe()),
            "description": config.describe(),
        },
        "toy_rule": toy,
        "synthetic_equivalence": equivalence,
        "synthetic_plastic_smoke": plastic,
        "checkpoint": checkpoint,
        "banc_equivalence": banc,
        "integrity": integrity,
        "checks": checks,
        "failures": failures,
        "all_checks_passed": not failures,
        "runtime_s": round(time.perf_counter() - started, 4),
        "process_memory": process_memory(),
        "limitations": [
            "The synthetic substrate is a validation fixture, not a brain circuit.",
            "A nonzero weight delta is a model output of the declared rule and is "
            "not evidence of learning or of a biological synaptic change.",
            "eta = 0 equality is verified only for the seeds, durations and inputs "
            "recorded here; it is not a proof for every possible configuration.",
            "The BANC section uses a short simulation window and a small stimulated "
            "population; it validates the software contract, not connectome dynamics.",
            "Rewards are external computational scalars; no dopamine, octopamine or "
            "serotonin quantity was measured.",
        ],
    }
    write_json(RESULT_PATH, payload)
    print(json.dumps(
        {
            "result": relative(RESULT_PATH),
            "checks": checks,
            "failures": failures,
            "runtime_s": payload["runtime_s"],
            "banc": banc.get("available"),
        },
        indent=1,
    ))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
