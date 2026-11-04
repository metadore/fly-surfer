"""Phase 2.5 benchmark helpers, validation and failure recording."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from brain.brain_simulator import BrainSimulator, Stimulus
from brain.neural_activity import SpikeRecorder
from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseParameters
from experiments.phase_2_5 import benchmark, run_all


def neuron_params() -> LIFParameters:
    return LIFParameters.from_config(
        {
            "capacitance_pf": 200.0,
            "leak_conductance_ns": 10.0,
            "resting_potential_mv": -65.0,
            "threshold_mv": -50.0,
            "reset_potential_mv": -68.0,
            "refractory_ms": 2.0,
            "initial_potential_mv": -65.0,
        }
    )


def synapse_params(**overrides) -> SynapseParameters:
    values = dict(
        weight_transform="linear",
        weight_scale_pa_per_synapse=1.0,
        weight_exponent=0.75,
        tau_exc_ms=5.0,
        tau_inh_ms=8.0,
        delay_ms=1.0,
    )
    values.update(overrides)
    return SynapseParameters(**values)


def test_graph_stats_reports_degrees(graph_factory) -> None:
    graph = graph_factory(4, [(0, 1, 10), (0, 2, 5), (2, 3, 7)])
    stats = benchmark._graph_stats(graph)
    assert stats["n_nodes"] == 4
    assert stats["n_edges"] == 3
    assert stats["n_synapses"] == 22
    assert stats["max_out_degree"] == 2
    assert stats["max_in_degree"] == 1
    assert stats["isolated_neurons"] == 0
    assert stats["kind"] == "subgraph"


def test_activity_hash_is_deterministic() -> None:
    first = SpikeRecorder(3, 8)
    first.record(0, np.array([1], dtype=np.int32), 0.5)
    first.record(2, np.array([0, 2], dtype=np.int32), 0.5)
    second = SpikeRecorder(3, 8)
    second.record(0, np.array([1], dtype=np.int32), 0.5)
    second.record(2, np.array([0, 2], dtype=np.int32), 0.5)
    third = SpikeRecorder(3, 8)
    third.record(1, np.array([1], dtype=np.int32), 0.5)

    digest = benchmark._activity_hash(first)
    assert digest == benchmark._activity_hash(second)
    assert digest != benchmark._activity_hash(third)


def _stable_run(graph_factory):
    graph = graph_factory(2, [(0, 1, 200)])
    stimulus = Stimulus(
        indices=np.array([0]), current_pa=4000.0, start_ms=0.0, end_ms=20.0
    )
    simulator = BrainSimulator(
        graph,
        neuron_params(),
        synapse_params(weight_scale_pa_per_synapse=5.0),
        dt_ms=0.5,
        duration_ms=20.0,
        seed=1,
        stimulus=stimulus,
    )
    return graph, simulator, simulator.run(progress=False)


def test_validate_run_passes_for_stable_run(graph_factory) -> None:
    graph, simulator, result = _stable_run(graph_factory)
    validation = benchmark._validate_run(graph, simulator, result)
    assert result.recorder.n_spikes > 0
    assert validation["passed"] is True
    assert validation["finite_state"] is True
    assert validation["voltage_bounds_ok"] is True
    assert validation["refractory_ok"] is True
    assert validation["directional_consistency_ok"] is True
    assert validation["expected_transmissions"] == validation[
        "recorded_transmissions"
    ]


def test_validate_run_detects_directional_mismatch(graph_factory) -> None:
    graph, simulator, result = _stable_run(graph_factory)
    result.summary["synapses"]["spike_transmissions"] += 1
    validation = benchmark._validate_run(graph, simulator, result)
    assert validation["directional_consistency_ok"] is False
    assert validation["passed"] is False


def test_validate_run_detects_non_finite_state(graph_factory) -> None:
    graph, simulator, result = _stable_run(graph_factory)
    simulator.neurons._V[0] = np.nan
    validation = benchmark._validate_run(graph, simulator, result)
    assert validation["finite_state"] is False
    assert validation["passed"] is False


def test_failure_payload_records_reason_and_memory(tmp_path: Path) -> None:
    error = benchmark.BenchmarkSkipped("only 0.2 GB free")
    payload = benchmark._failure_payload(
        status="skipped",
        label="full",
        size_request="full",
        reason=str(error),
        available_gb=0.2,
        suite_path=Path("suite.yaml"),
        exc=error,
    )
    target = tmp_path / "result.json"
    benchmark._write_json(target, payload)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["status"] == "skipped"
    assert loaded["reason"] == "only 0.2 GB free"
    assert loaded["available_memory_gb"] == 0.2
    assert loaded["exception_type"] == "BenchmarkSkipped"
    assert not (tmp_path / "result.tmp").exists()


def test_main_records_skip_when_memory_is_low(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(benchmark, "_available_gb", lambda: 0.0)
    target = tmp_path / "full.json"
    code = benchmark.main(
        [
            "--suite",
            str(benchmark.DEFAULT_SUITE),
            "--size",
            "full",
            "--output",
            str(target),
        ]
    )
    assert code == 2
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["status"] == "skipped"
    assert loaded["available_memory_gb"] == 0.0
    assert "at least" in loaded["reason"]


def test_parse_sizes_accepts_space_and_comma() -> None:
    assert run_all._parse_sizes(["800,5000", "20000"]) == [800, 5000, 20000]
    with pytest.raises(ValueError):
        run_all._parse_sizes(["1"])


def test_reproducibility_comparison() -> None:
    base = {
        "label": "n800",
        "status": "ok",
        "activity_hash": "abc",
        "sample": {"root_id_sha256": "root"},
        "activity": {"n_spikes": 10},
        "synapses": {"spike_transmissions": 20},
    }
    repeat = {
        "label": "n800_repeat",
        "status": "ok",
        "activity_hash": "abc",
        "sample": {"root_id_sha256": "root"},
        "activity": {"n_spikes": 10},
        "synapses": {"spike_transmissions": 20},
    }
    result = run_all._reproducibility([base, repeat], 800)
    assert result["passed"] is True
    assert result["activity_hash_match"] is True

    repeat["activity_hash"] = "different"
    result = run_all._reproducibility([base, repeat], 800)
    assert result["passed"] is False
    assert result["activity_hash_match"] is False


def test_build_report_preserves_failure_context(tmp_path: Path) -> None:
    suite = {
        "benchmark": {},
        "sampling": {"sizes": [50000], "full_size": 139255},
    }
    successful = {
        "status": "ok",
        "label": "n50000",
        "graph": {"n_nodes": 50000, "n_edges": 1, "n_synapses": 1},
        "performance": {"steps_per_second": 100.0},
        "activity_hash": "abc",
        "orchestrator": {"role": "series"},
    }
    failed_full = {
        "status": "failed",
        "label": "full",
        "size_request": "139255",
        "reason": "MemoryError: allocation failed",
        "available_memory_gb": 0.4,
        "last_successful_benchmark": {
            "label": "n50000",
            "n_neurons": 50000,
        },
        "orchestrator": {"role": "series"},
    }
    report = run_all.build_report(
        suite_path=tmp_path / "suite.yaml",
        suite=suite,
        records=[successful, failed_full],
        reproducibility={"size": None, "passed": None},
        plots=[],
        expected_sizes=[50000, 139255],
        include_full=True,
        started_at="start",
        finished_at="finish",
    )
    assert report["status"] == "partial"
    full = report["full_connectome"]
    assert full["status"] == "failed"
    assert full["reason"] == "MemoryError: allocation failed"
    assert full["available_memory_gb"] == 0.4
    assert full["last_successful_benchmark"]["n_neurons"] == 50000
    assert report["failures"][0]["reason"] == "MemoryError: allocation failed"


def test_last_success_ignores_failures() -> None:
    records = [
        {"label": "n800", "status": "ok", "graph": {"n_nodes": 800},
         "performance": {"steps_per_second": 100.0}},
        {"label": "n5000", "status": "failed", "reason": "boom"},
        {"label": "n20000", "status": "ok", "graph": {"n_nodes": 20000},
         "performance": {"steps_per_second": 10.0}},
    ]
    last = run_all._last_success(records)
    assert last["label"] == "n20000"
    assert last["n_neurons"] == 20000
