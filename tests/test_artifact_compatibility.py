"""The simulation layer must consume the validated connectome artifact as-is."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from brain.brain_simulator import BrainSimulator
from brain.connectome_loader import load_connectome
from brain.neuron_model import LIFParameters
from brain.subgraph import (
    extract_induced_subgraph,
    sample_connected_neurons,
    weak_component_count,
)
from brain.synapse_model import SynapseParameters

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = PROJECT_ROOT / "datasets" / "processed" / "connectome.npz"

pytestmark = pytest.mark.skipif(
    not ARTIFACT.exists(), reason="validated connectome artifact not available"
)


@pytest.fixture(scope="module")
def connectome():
    return load_connectome(ARTIFACT)


def test_verified_connectome_counts(connectome) -> None:
    assert connectome.n_nodes == 139_255
    assert connectome.n_edges == 3_732_460
    assert connectome.n_synapses == 50_666_648
    assert connectome.out_indptr.shape == (connectome.n_nodes + 1,)
    assert connectome.in_indptr.shape == (connectome.n_nodes + 1,)
    assert int(connectome.out_indptr[-1]) == connectome.n_edges
    assert bool(np.all(np.diff(connectome.root_ids) > 0))
    assert bool(np.all(connectome.edge_weight >= 1))
    assert int(np.count_nonzero(connectome.edge_src == connectome.edge_dst)) == 0


def test_small_sample_can_be_simulated(connectome) -> None:
    selection = sample_connected_neurons(
        connectome,
        n_neurons=50,
        seed=11,
        min_degree=5,
        candidate_seeds_per_class=1,
        random_candidate_seeds=2,
    )
    subgraph = extract_induced_subgraph(connectome, selection.node_indices)
    assert subgraph.n_nodes == 50
    assert weak_component_count(subgraph)[0] == 1
    assert subgraph.n_edges > 0

    simulator = BrainSimulator(
        subgraph,
        LIFParameters(),
        SynapseParameters(),
        dt_ms=0.5,
        duration_ms=20.0,
        seed=0,
    )
    result = simulator.run(progress=False)
    assert result.recorder.n_spikes == 0
    assert result.summary["diagnostics"]["finite_state"] is True
    assert result.summary["synapses"]["effective_delay_ms"] > 0
