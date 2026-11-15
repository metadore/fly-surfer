"""Focused tests for the separate Phase 4G.3 BANC simulation pathway."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from brain.banc_graph import BancConnectome
from brain.banc_simulator import (
    BancSignedSynapses,
    BancSimulationResult,
    BancSimulator,
    BancStimulation,
)
from brain.banc_synapse_policy import SignPolicy, WeightPolicy, build_synapse_policy
from brain.neuron_model import LIFParameters
from brain.synapse_model import SynapseModel, SynapseParameters


def make_graph(
    n_nodes: int, edges: list[tuple[int, int, int]], threshold: int = 5
) -> BancConnectome:
    order = sorted((int(s), int(d), int(w)) for s, d, w in edges)
    edge_src = np.array([edge[0] for edge in order], dtype=np.int32)
    edge_dst = np.array([edge[1] for edge in order], dtype=np.int32)
    edge_weight = np.array([edge[2] for edge in order], dtype=np.int32)
    out_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=n_nodes), out=out_indptr[1:])
    in_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=n_nodes), out=in_indptr[1:])
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int32)
    return BancConnectome(
        root_ids=np.arange(1000, 1000 + n_nodes, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        threshold=threshold,
    )


def make_policy(
    graph: BancConnectome,
    labels: list[str | None],
    weight_policy: WeightPolicy | None = None,
    sign_policy: SignPolicy | None = None,
):
    nodes = pd.DataFrame(
        {
            "banc_888_id": [str(value) for value in graph.root_ids],
            "node_index": np.arange(graph.n_nodes),
            "neurotransmitter_verified": labels,
            "neurotransmitter_predicted": [None] * graph.n_nodes,
        }
    )
    return build_synapse_policy(
        graph,
        nodes,
        sign_policy or SignPolicy(),
        weight_policy or WeightPolicy(),
    )


def first_spike(times: np.ndarray, indices: np.ndarray, neuron: int) -> float | None:
    selected = times[indices == neuron]
    return float(selected.min()) if selected.size else None


def simulate(edges, labels, *, duration_ms=40.0, dt_ms=0.5, **kwargs):
    graph = make_graph(len(labels), edges)
    policy = make_policy(graph, labels)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        **kwargs,
    )
    return simulator, simulator.run()


def test_convergent_chain_propagates_in_order():
    # A single structural edge delivers about 5 mV to a resting neuron, below the
    # 15 mV threshold. Propagation through the toy network therefore requires
    # convergence, as it does in the biological graph under this policy.
    labels = ["acetylcholine"] * 9
    edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(intermediate, 8, 500) for intermediate in range(4, 8)]
    simulator, result = simulate(
        edges,
        labels,
        duration_ms=40.0,
        stimulation=BancStimulation(np.arange(4), 2000.0, 1.0, 3.0),
    )
    times = result.recorder.spike_times_ms
    indices = result.recorder.spike_neuron_indices
    source_times = np.array(
        [first_spike(times, indices, neuron) for neuron in range(4)], dtype=float
    )
    intermediate_times = np.array(
        [first_spike(times, indices, neuron) for neuron in range(4, 8)],
        dtype=float,
    )
    target_time = first_spike(times, indices, 8)
    assert np.all(np.isfinite(source_times))
    assert np.all(np.isfinite(intermediate_times))
    assert target_time is not None
    assert intermediate_times.min() >= source_times.max() + 1.0 - 1e-9
    assert target_time >= intermediate_times.max() + 1.0 - 1e-9
    assert result.summary["synaptic_transmission"]["spike_transmissions"] > 0
    assert result.summary["activity_by_stimulation"]["stimulated_spikes"] >= 4
    assert result.summary["activity_by_stimulation"]["non_stimulated_spikes"] >= 5


def test_inhibitory_edge_drives_a_negative_current():
    graph = make_graph(2, [(0, 1, 500)])
    labels = ["gaba", "acetylcholine"]
    policy = make_policy(graph, labels)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=8.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    simulator.run()
    assert simulator.synapses.inhibitory_current_pa[1] > 0
    assert simulator.synapses.excitatory_current_pa[1] == 0
    assert float(simulator.neurons.membrane_potential[1]) < -65.0


def test_unknown_sign_edge_carries_no_current():
    graph = make_graph(2, [(0, 1, 500)])
    labels = [None, "acetylcholine"]
    policy = make_policy(graph, labels)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=20.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert result.recorder.n_spikes > 0
    assert np.count_nonzero(result.recorder.spike_neuron_indices == 0) >= 1
    assert np.count_nonzero(result.recorder.spike_neuron_indices == 1) == 0
    assert simulator.synapses.excitatory_current_pa[1] == 0
    assert simulator.synapses.inhibitory_current_pa[1] == 0


def test_multiple_incoming_edges_sum_on_the_target():
    graph = make_graph(3, [(0, 2, 25), (1, 2, 25)])
    policy = make_policy(graph, ["acetylcholine"] * 3)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=10.0,
        stimulation=BancStimulation(np.array([0, 1]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    weight = float(policy.edge_exc_weight[0])
    peak = result.summary["diagnostics"]["max_excitatory_synaptic_current_pa"]
    assert peak > 0
    assert peak == pytest.approx(2.0 * weight, rel=1e-3)


def test_one_source_reaches_all_outgoing_targets():
    graph = make_graph(3, [(0, 1, 50), (0, 2, 50)])
    policy = make_policy(graph, ["acetylcholine"] * 3)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=10.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert simulator.synapses.excitatory_current_pa[1] > 0
    assert simulator.synapses.excitatory_current_pa[2] > 0
    assert result.summary["synaptic_transmission"]["spike_transmissions"] >= 2 * int(
        np.count_nonzero(result.recorder.spike_neuron_indices == 0)
    )


def test_transmission_is_directed():
    graph = make_graph(2, [(0, 1, 500)])
    policy = make_policy(graph, ["acetylcholine"] * 2)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=20.0,
        stimulation=BancStimulation(np.array([1]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert np.count_nonzero(result.recorder.spike_neuron_indices == 1) >= 1
    assert simulator.synapses.excitatory_current_pa[0] == 0
    assert result.summary["synaptic_transmission"]["spike_transmissions"] == 0


def test_absent_edge_does_not_transmit():
    graph = make_graph(3, [(0, 1, 500)])
    policy = make_policy(graph, ["acetylcholine"] * 3)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=20.0,
        stimulation=BancStimulation(np.array([2]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert result.summary["synaptic_transmission"]["spike_transmissions"] == 0
    assert np.count_nonzero(result.recorder.spike_neuron_indices == 0) == 0
    assert np.count_nonzero(result.recorder.spike_neuron_indices == 1) == 0


def test_weight_transformation_changes_delivered_current():
    graph = make_graph(2, [(0, 1, 100)])
    labels = ["acetylcholine"] * 2
    stimulation = BancStimulation(np.array([0]), 2000.0, 1.0, 3.0)
    peaks = {}
    for name, policy in (
        (
            "power",
            WeightPolicy(transform="power", exponent=0.75, scale_pa=5.0, cap_pa=300.0),
        ),
        (
            "linear",
            WeightPolicy(transform="linear", scale_pa=0.5, cap_pa=300.0),
        ),
    ):
        simulator = BancSimulator(
            graph,
            make_policy(graph, labels, weight_policy=policy),
            dt_ms=0.5,
            duration_ms=10.0,
            stimulation=stimulation,
        )
        simulator.run()
        peaks[name] = float(simulator.synapses.excitatory_current_pa[1])
    assert peaks["power"] > 2.0 * peaks["linear"]


def test_threshold_sensitivity_and_mismatch_rejection():
    graphs = {
        5: make_graph(2, [(0, 1, 10)], threshold=5),
        10: make_graph(2, [(0, 1, 20)], threshold=10),
    }
    labels = ["acetylcholine"] * 2
    for threshold, graph in graphs.items():
        policy = make_policy(graph, labels)
        simulator = BancSimulator(graph, policy, duration_ms=5.0)
        result = simulator.run()
        assert result.threshold == threshold
        assert result.summary["graph"]["graph_threshold"] == threshold
        assert float(policy.edge_exc_weight[0]) == pytest.approx(
            5.0 * graph.edge_weight[0] ** 0.75, rel=1e-4
        )
    with pytest.raises(ValueError):
        BancSimulator(graphs[5], make_policy(graphs[10], labels))


def test_delay_buffer_holds_the_packet_for_two_steps():
    graph = make_graph(2, [(0, 1, 100)])
    policy = make_policy(graph, ["acetylcholine"] * 2)
    synapses = BancSignedSynapses(graph, policy, dt_ms=0.5, delay_ms=1.0)
    assert synapses.delay_steps == 2
    assert synapses.effective_delay_ms == 1.0
    synapses.propagate(np.array([0], dtype=np.int32))
    synapses.advance()
    assert synapses.excitatory_current_pa[1] == 0
    synapses.advance()
    assert synapses.excitatory_current_pa[1] > 0

    short = BancSignedSynapses(graph, policy, dt_ms=0.5, delay_ms=0.0)
    assert short.delay_steps == 1
    assert short.effective_delay_ms == 0.5


def test_refractory_period_limits_spike_rate():
    labels = ["acetylcholine"]
    graph = make_graph(1, [])
    policy = make_policy(graph, labels)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=30.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 29.0),
    )
    result = simulator.run()
    times = np.sort(result.recorder.spike_times_ms)
    assert times.size >= 5
    assert np.min(np.diff(times)) >= 2.0 - 1e-6


def test_no_stimulation_no_spikes():
    graph = make_graph(5, [(0, 1, 50), (1, 2, 50), (2, 3, 50)])
    policy = make_policy(graph, ["acetylcholine"] * 5)
    simulator = BancSimulator(graph, policy, dt_ms=0.5, duration_ms=50.0)
    result = simulator.run()
    assert result.recorder.n_spikes == 0
    assert result.summary["activity"]["active_neurons"] == 0
    assert not np.any(simulator.synapses.synaptic_current_pa)


def test_external_current_injection_drives_spiking():
    graph = make_graph(1, [])
    policy = make_policy(graph, ["acetylcholine"])
    without = BancSimulator(graph, policy, dt_ms=0.5, duration_ms=20.0).run()
    with_current = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=20.0,
        stimulation=BancStimulation(np.array([0]), 1000.0, 1.0, 6.0),
    ).run()
    assert without.recorder.n_spikes == 0
    assert with_current.recorder.n_spikes >= 1


def test_noisy_simulation_stays_finite():
    graph = make_graph(50, [(index, (index + 1) % 50, 20) for index in range(50)])
    policy = make_policy(graph, ["acetylcholine"] * 50)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=20.0,
        seed=7,
        background_current_pa=80.0,
        noise_std_pa=150.0,
    )
    result = simulator.run()
    assert result.summary["diagnostics"]["finite_state"] is True
    assert result.summary["diagnostics"]["min_membrane_mv"] >= -90.0001
    assert np.all(np.isfinite(simulator.neurons.membrane_potential))
    assert np.all(np.isfinite(simulator.synapses.synaptic_current_pa))


def test_seeded_runs_are_reproducible_and_seeds_differ():
    graph = make_graph(10, [(index, (index + 1) % 10, 200) for index in range(10)])
    policy = make_policy(graph, ["acetylcholine"] * 10)

    def run(seed):
        simulator = BancSimulator(
            graph,
            policy,
            dt_ms=0.5,
            duration_ms=40.0,
            seed=seed,
            noise_std_pa=100.0,
            stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 15.0),
        )
        result = simulator.run()
        return result.recorder.spike_times_ms.copy(), result.recorder.spike_neuron_indices.copy()

    first = run(11)
    second = run(11)
    other = run(12)
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])
    assert not (
        np.array_equal(first[0], other[0]) and np.array_equal(first[1], other[1])
    )


def test_invalid_inputs_are_rejected():
    graph = make_graph(3, [(0, 1, 10)])
    policy = make_policy(graph, ["acetylcholine"] * 3)
    with pytest.raises(ValueError):
        BancSimulator(graph, policy, dt_ms=0.0)
    with pytest.raises(ValueError):
        BancSimulator(graph, policy, duration_ms=-1.0)
    with pytest.raises(ValueError):
        BancSimulator(graph, policy, noise_std_pa=-1.0)
    with pytest.raises(ValueError):
        BancSimulator(
            graph, policy, stimulation=BancStimulation(np.array([3]), 100.0, 0.0, 1.0)
        )
    with pytest.raises(ValueError):
        BancStimulation(np.array([], dtype=np.int64), 100.0, 0.0, 1.0)
    with pytest.raises(ValueError):
        BancStimulation(np.array([0]), 100.0, 2.0, 1.0)
    with pytest.raises(TypeError):
        BancSimulator(graph, policy, input_schedule=object())
    simulator = BancSimulator(graph, policy)
    with pytest.raises(ValueError):
        simulator.run(duration_ms=0.1)


def test_isolated_nodes_are_reported_without_error():
    graph = make_graph(5, [(0, 1, 50)])
    policy = make_policy(graph, ["acetylcholine"] * 5)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=10.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert result.summary["graph"]["n_isolated"] == 3
    assert result.recorder.n_spikes >= 1


def test_large_structural_weight_is_capped_and_finite():
    graph = make_graph(2, [(0, 1, 10_000_000)], threshold=1)
    policy = make_policy(
        graph,
        ["acetylcholine"] * 2,
        weight_policy=WeightPolicy(
            transform="power", exponent=0.75, scale_pa=5.0, cap_pa=300.0
        ),
    )
    assert float(policy.edge_exc_weight.max()) == pytest.approx(300.0)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=10.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert np.isfinite(result.summary["diagnostics"]["max_abs_total_current_pa"])
    assert np.all(np.isfinite(simulator.synapses.synaptic_current_pa))


def test_memory_breakdown_is_consistent():
    graph = make_graph(10, [(index, index + 1, 20) for index in range(9)])
    policy = make_policy(graph, ["acetylcholine"] * 10)
    simulator = BancSimulator(graph, policy)
    memory = simulator.memory_breakdown()
    assert memory["retained_arrays_bytes"] == (
        memory["graph_arrays_bytes"]
        + memory["policy_arrays_bytes"]
        + memory["neuron_state_bytes"]
        + memory["synapse_state_bytes"]
        + memory["spike_recorder_bytes"]
    )
    assert memory["delay_buffer_bytes"] == 2 * 2 * 10 * 4


def test_simulator_matches_the_fafb_synapse_dynamics():
    graph = make_graph(4, [(0, 1, 40), (0, 2, 40), (1, 3, 80), (2, 3, 80)])
    policy = make_policy(graph, ["acetylcholine"] * 4)
    banc = BancSignedSynapses(graph, policy, dt_ms=0.5)

    fafb_graph = SimpleNamespace(
        n_nodes=graph.n_nodes,
        out_indptr=graph.out_indptr,
        edge_src=graph.edge_src,
        edge_dst=graph.edge_dst,
        edge_weight=graph.edge_weight,
        vocabulary={"nt_type": ["ACH"]},
        nt_code=np.zeros(graph.n_nodes, dtype=np.int16),
    )
    fafb = SynapseModel(
        fafb_graph,
        SynapseParameters(
            weight_transform="power",
            weight_scale_pa_per_synapse=5.0,
            weight_exponent=0.75,
            tau_exc_ms=5.0,
            tau_inh_ms=8.0,
            delay_ms=1.0,
        ),
        dt_ms=0.5,
    )
    for spikes in (
        np.array([0], dtype=np.int32),
        np.array([1, 2], dtype=np.int32),
        np.array([], dtype=np.int32),
    ):
        banc.propagate(spikes)
        fafb.propagate(spikes)
        for _ in range(3):
            banc.advance()
            fafb.advance()
    assert np.allclose(
        banc.excitatory_current_pa, fafb.excitatory_current_pa, rtol=1e-5
    )
    assert np.allclose(
        banc.inhibitory_current_pa, fafb.inhibitory_current_pa, rtol=1e-5
    )
    assert banc.total_transmissions == fafb.total_transmissions


def test_result_serialisation_round_trip(tmp_path):
    graph = make_graph(3, [(0, 1, 50), (1, 2, 50)])
    policy = make_policy(graph, ["acetylcholine"] * 3)
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=0.5,
        duration_ms=20.0,
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    result = simulator.run()
    assert isinstance(result, BancSimulationResult)
    paths = result.save(tmp_path)
    assert (tmp_path / "activity.npz").exists()
    assert (tmp_path / "simulation_metadata.json").exists()
    assert paths["activity"].endswith("activity.npz")
    with np.load(tmp_path / "activity.npz") as data:
        assert int(data["n_neurons"]) == 3
        assert data["spike_times_ms"].shape == data["spike_neuron_indices"].shape
    assert result.summary["model"]["neuron"]["capacitance_pf"] == LIFParameters().capacitance_pf
