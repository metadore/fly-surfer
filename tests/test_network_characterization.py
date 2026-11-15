"""P3-T12: instrumentation equivalence, partition measurement and gates."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from brain.brain_simulator import BrainSimulator
from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from experiments.phase_3c import causal_control as cc
from experiments.phase_3c import network_characterization as nc

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StepScheduler:
    """Minimal input schedule: constant current on fixed indices for N steps."""

    def __init__(self, indices, current_pa: float, until_step: int) -> None:
        self.indices = np.asarray(indices, dtype=np.int64)
        self.current_pa = float(current_pa)
        self.until_step = int(until_step)
        self.config = SimpleNamespace(pulse_decay_ms=150.0, max_hold_ms=250.0)
        self.horizon_ms = 1_000.0

    def apply(self, step: int, time_ms: float, current: np.ndarray) -> None:
        if step < self.until_step:
            current[self.indices] += self.current_pa

    @property
    def stimulated_indices(self) -> np.ndarray:
        return self.indices

    @property
    def memory_bytes(self) -> int:
        return 0

    def signature(self) -> dict:
        return {
            "indices": self.indices.astype(np.int64),
            "values": np.zeros(self.indices.size, dtype=np.float64),
            "starts": np.zeros(self.indices.size, dtype=np.int64),
            "frame_values": np.zeros((1, self.indices.size), dtype=np.float64),
            "frame_times": np.zeros(1, dtype=np.float64),
            "pulse_values": np.zeros((0, self.indices.size), dtype=np.float64),
            "pulse_onsets": np.zeros(0, dtype=np.float64),
        }

    def input_statistics(self) -> dict:
        return {"n_frames": 0, "n_pulse_events": 0}

    def describe(self) -> dict:
        return {"kind": "test_scheduler"}


class FakeMapping:
    def __init__(self, graph, feature_indices: dict[str, np.ndarray], n: int) -> None:
        self.graph = graph
        self._indices = feature_indices
        self.populations = {
            name: SimpleNamespace(
                size=lambda indices=indices: int(indices.size)
            )
            for name, indices in feature_indices.items()
        }
        self.seed = 0

    def indices(self, feature: str) -> np.ndarray:
        return self._indices[feature]

    def size(self, feature: str) -> int:
        return int(self._indices[feature].size)

    def stimulated_indices(self) -> np.ndarray:
        return np.unique(np.concatenate(list(self._indices.values())))


def _setup(graph, feature_indices):
    mapping = FakeMapping(graph, feature_indices, graph.n_nodes)
    encoders = {name: object() for name in feature_indices}
    return SimpleNamespace(mapping=mapping, encoders=encoders, amplitudes={}, dt_ms=0.5)


def _config(cfg_sampling, *, noise_std_pa: float = 0.0):
    reference = {
        "dt_ms": 0.5,
        "duration_ms": 100.0,
        "n_steps": 200,
        "max_recorded_spikes": 2_000_000,
        "background_current_pa": 0.0,
        "noise_std_pa": noise_std_pa,
        "mapping_seed": 1,
        "simulation_seed": 0,
    }
    causal = SimpleNamespace(
        reference=reference,
        archived={"spike_counts_sha256": "0" * 64, "scheduler_sha256": "0" * 64},
    )
    return nc.CharacterizationConfig(
        source_path=PROJECT_ROOT / "configs" / "p3_t12_characterization.yaml",
        version="test",
        description="test",
        causal=causal,
        output=PROJECT_ROOT / "unused.json",
        smoke_output=PROJECT_ROOT / "unused_smoke.json",
        repeats=1,
        conditions=nc.ABLATION_NAMES + (nc.WASHOUT_NAME, "C0", "C1", "C2", "C3"),
        subprocess_conditions=(),
        sampling=cfg_sampling,
        washout={"extra_ms": 750.0, "silent_window_ms": 500.0},
        limitations=("test",),
    )


def _spec(name="stimulated"):
    return cc.ConditionSpec(
        name=name,
        description="test",
        frame_source="none",
        active_features=None,
    )


@pytest.fixture
def sampling():
    return nc.CharacterizationConfig.load().sampling


def test_config_durations_and_specs() -> None:
    cfg = nc.CharacterizationConfig.load()
    assert cfg.duration_for("C3", smoke_ms=None) == pytest.approx(3300.5)
    assert cfg.duration_for("C3-washout", smoke_ms=None) == pytest.approx(4050.5)
    assert cfg.duration_for("C3-washout", smoke_ms=600.0) == pytest.approx(1350.0)
    assert cfg.prefix_cutoff_for(smoke_ms=None) == pytest.approx(3300.5)
    ablation = cfg.spec_for("no-train_lane")
    assert len(ablation.active_features) == 13
    assert "train_lane" not in ablation.active_features
    assert cfg.spec_for("C2").active_features is not None
    assert cfg.spec_for("C3-washout").active_features is None


def test_config_rejects_reordered_conditions(tmp_path) -> None:
    source = (PROJECT_ROOT / "configs/p3_t12_characterization.yaml").read_text(
        encoding="utf-8"
    )
    mutated = source.replace(
        "  - C0\n  - C1\n  - C2\n  - C3",
        "  - C1\n  - C0\n  - C2\n  - C3",
    )
    assert mutated != source
    target = tmp_path / "mutated.yaml"
    target.write_text(mutated, encoding="utf-8")
    with pytest.raises(ValueError, match="conditions must be exactly"):
        nc.CharacterizationConfig.load(target)


def test_instrumented_stepper_matches_brain_simulator(
    graph_factory, monkeypatch, sampling
) -> None:
    graph = graph_factory(
        8,
        [
            (0, 1, 10),
            (1, 2, 10),
            (2, 3, 10),
            (3, 4, 10),
            (4, 5, 10),
            (5, 0, 10),
            (2, 6, 5),
            (6, 7, 5),
        ],
    )
    feature_indices = {
        "a": np.array([0, 1], dtype=np.int64),
        "b": np.array([2, 3], dtype=np.int64),
    }
    setup = _setup(graph, feature_indices)
    cfg = _config(sampling)
    neuron = LIFParameters()
    synapse = SynapseParameters(
        weight_transform="linear",
        weight_scale_pa_per_synapse=5.0,
        weight_exponent=1.0,
        delay_ms=1.0,
    )
    scheduler = StepScheduler([0, 1], 320.0, until_step=120)
    monkeypatch.setattr(nc.cc, "build_scheduler", lambda spec, s, frames: scheduler)
    monkeypatch.setattr(nc.cc, "resolve_frames", lambda spec, c, cache, smoke_ms: ())

    simulator = BrainSimulator(
        graph,
        neuron,
        synapse,
        dt_ms=0.5,
        duration_ms=100.0,
        seed=0,
        background_current_pa=0.0,
        noise_std_pa=0.0,
        input_schedule=StepScheduler([0, 1], 320.0, until_step=120),
        max_recorded_spikes=2_000_000,
        progress_interval_ms=0.0,
        diagnostics_interval_steps=50,
    )
    result = simulator.run(progress=False)
    expected_times = np.asarray(result.recorder.spike_times_ms, dtype=np.float64)
    expected_neurons = np.asarray(result.recorder.spike_neuron_indices, dtype=np.int64)

    item, internal = nc.run_instrumented(
        _spec(),
        cfg,
        setup,
        neuron,
        synapse,
        None,
        duration_ms=100.0,
        smoke_ms=None,
        prefix_cutoff_ms=60.0,
    )

    assert item["simulation"]["spikes_total"] == int(expected_times.size)
    assert item["simulation"]["spikes_total"] > 0
    assert item["reproducibility_hashes"]["spikes_total"] == int(expected_times.size)
    assert item["simulation"]["diagnostics_stepwise"]["finite_state"] is True
    # The legacy activity-detection flag and the quoted classification agree.
    outside_spikes = item["partitions"]["outside_reference"]["spikes"]
    assert item["ignition"]["ignited"] is (outside_spikes > 0)
    legacy = item["ignition_classification"]["legacy_activity_detection"]
    assert legacy["value"] is item["ignition"]["ignited"]
    assert legacy["consistent_with_measurement"] is True
    # Prefix counts must equal the recorder counts restricted to the cutoff.
    expected_prefix = np.bincount(
        expected_neurons[expected_times <= 60.0 + 1e-6], minlength=graph.n_nodes
    )
    assert np.array_equal(internal["prefix_counts"], expected_prefix)
    # Stepwise extrema cover every step, so they are at least as extreme in
    # both directions as the simulator's subset-sampled diagnostics.
    diagnostics = result.summary["diagnostics"]
    assert item["simulation"]["diagnostics_stepwise"]["min_membrane_mv"] <= (
        diagnostics["min_membrane_mv"] + 1e-9
    )
    assert item["simulation"]["diagnostics_stepwise"]["max_membrane_mv"] >= (
        diagnostics["max_membrane_mv"] - 1e-9
    )
    # The sampled membrane population is fully accounted for per snapshot.
    for snapshot in item["simulation"]["membrane_samples"]:
        assert sum(snapshot["histogram_counts"]) == graph.n_nodes
        assert snapshot["at_floor"] + snapshot["near_threshold"] <= graph.n_nodes
        assert snapshot["min_mv"] >= neuron.minimum_potential_mv - 1e-12
        assert snapshot["max_mv"] < neuron.threshold_mv + 1e-12


def test_instrumented_rejects_nonzero_noise(sampling) -> None:
    graph = SimpleNamespace(n_nodes=4)
    setup = _setup(graph, {"a": np.array([0], dtype=np.int64)})
    cfg = _config(sampling, noise_std_pa=1.0)
    with pytest.raises(ValueError, match="background and noise"):
        nc.run_instrumented(
            _spec(),
            cfg,
            setup,
            LIFParameters(),
            SynapseParameters(),
            None,
            duration_ms=10.0,
            smoke_ms=None,
        )


def test_membrane_snapshot_counts_floor_and_threshold() -> None:
    params = LIFParameters()
    potential = np.array([-90.0, -90.0, -65.0, -50.02, -49.9], dtype=np.float64)
    refractory = np.array([0, 3, 0, 0, 0], dtype=np.int32)
    snapshot = nc.membrane_snapshot(
        potential,
        refractory,
        params,
        histogram_edges=[-90.0, -70.0, -50.0],
        percentiles=[50],
        near_threshold_margin_mv=0.05,
    )
    assert snapshot["at_floor"] == 2
    # -50.02 is within 0.05 mV of threshold; -49.9 could only exist after a
    # reset in the real model and is counted here as a near-threshold state.
    assert snapshot["near_threshold"] == 2
    assert snapshot["refractory"] == 1
    # Terminal-bin clipping keeps the fixed-edge histogram complete; -50.02
    # lands in the upper bin and -49.9 is clipped there and counted as
    # out-of-range.
    assert snapshot["histogram_counts"] == [2, 3]
    assert snapshot["histogram_out_of_range"] == 1
    assert snapshot["n_neurons"] == 5


def test_distance_from_sources_and_bucket_names(graph_factory) -> None:
    graph = graph_factory(
        5, [(0, 1, 1), (1, 2, 1), (2, 3, 1)]
    )
    distances = nc.distance_from_sources(graph, np.array([0]))
    assert distances[0] == 0
    assert distances[1] == 1
    assert distances[2] == 2
    assert distances[3] == 3
    assert np.isinf(distances[4])
    labels = nc.distance_bucket_labels(distances, [0, 1, 2, 3, 4])
    assert labels.tolist() == [0, 1, 2, 3, 4]
    assert nc.distance_bucket_name(0, [0, 1, 2, 3, 4]) == "0"
    assert nc.distance_bucket_name(1, [0, 1, 2, 3, 4]) == "1"
    assert nc.distance_bucket_name(4, [0, 1, 2, 3, 4]) == "unreachable_or_far"


def test_first_spike_times_and_gaps() -> None:
    times = np.array([0.5, 1.0, 1.0, 2.5, 9.0], dtype=np.float64)
    neurons = np.array([3, 1, 3, 1, 7], dtype=np.int64)
    first, unique, index = nc.first_spike_times(times, neurons, 10)
    assert unique.tolist() == [1, 3, 7]
    assert first[1] == 1.0
    assert first[3] == 0.5
    assert first[7] == 9.0
    assert np.isinf(first[0])
    assert np.array_equal(times[index], first[unique])
    assert nc.longest_interval_gap(times) == pytest.approx(6.5)
    assert nc.longest_interval_gap(np.array([], dtype=np.float64)) == 0.0


def test_prefix_gate_requires_identical_prefix() -> None:
    counts = np.array([1, 0, 4], dtype=np.int64)
    c3 = {"counts": counts}
    washout = {"prefix_counts": counts.copy()}
    gate = nc.prefix_gate(washout, {}, washout, c3, cutoff_ms=3300.5)
    assert gate["passed"] is True
    assert gate["identical"] is True
    assert gate["cutoff_ms"] == pytest.approx(3300.5)

    washout["prefix_counts"] = counts + np.array([1, 0, 0])
    mismatched = nc.prefix_gate(washout, {}, washout, c3, cutoff_ms=3300.5)
    assert mismatched["passed"] is False
    assert mismatched["prefix_spikes"] == 6


def test_archived_equivalence_accepts_reference_and_rejects_mutation() -> None:
    cfg = nc.CharacterizationConfig.load()
    artifact = PROJECT_ROOT / "experiments/phase_3c/results/p3_t2_full.json"
    if not artifact.is_file():
        pytest.skip("archived P3-T2 payload not available")
    c3 = json.loads(artifact.read_text(encoding="utf-8"))["conditions"]["C3"]
    item = {
        "simulation": {
            "spikes_total": c3["simulation"]["spikes_total"],
            "diagnostics_stepwise": {
                "min_membrane_mv": c3["simulation"]["diagnostics"]["min_membrane_mv"],
                "max_membrane_mv": c3["simulation"]["diagnostics"]["max_membrane_mv"],
            },
        },
        "partitions": {
            "active": {"spikes": c3["simulation"]["activity_by_stimulation"]["stimulated_spikes"]},
            "outside_active": {
                "spikes": c3["simulation"]["activity_by_stimulation"]["non_stimulated_spikes"]
            },
        },
        "reproducibility_hashes": c3["reproducibility_hashes"],
        "scheduler": {"signature_sha256": c3["scheduler"]["signature_sha256"]},
    }
    gate = nc.archived_equivalence(item, cfg)
    assert gate["passed"] is True
    assert all(gate["checks"].values())

    item["partitions"]["outside_active"]["spikes"] += 1
    mutated = nc.archived_equivalence(item, cfg)
    assert mutated["passed"] is False
    assert mutated["checks"]["spikes_unstimulated"] is False


def test_last_drive_step_reports_final_injected_step() -> None:
    scheduler = StepScheduler([0], 10.0, until_step=30)
    assert nc.last_drive_step(scheduler, n_nodes=2, n_steps=100, dt_ms=0.5) == 29
    assert nc.last_drive_step(None, n_nodes=2, n_steps=100, dt_ms=0.5) is None
