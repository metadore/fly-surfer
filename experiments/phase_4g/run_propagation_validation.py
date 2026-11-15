"""Phase 4G.4 propagation validation on controlled toy graphs.

This script does not test the biological graph. It tests whether the BANC
simulation pathway implements directed synaptic propagation as specified:
activation order, edge necessity, weight dependence, direction, sign handling,
unknown-sign exclusion, predicted-fallback sensitivity, delay, refractoriness,
and determinism. Every scenario is a synthetic graph with known structure.

The full-BANC smoke test is not re-run here; its recorded metadata and the
determinism repeat are read from ``experiments/results/phase_4g``.

Output: ``reports/PHASE_4G4_PROPAGATION_VALIDATION.json``.
"""

from __future__ import annotations

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

from brain.banc_graph import BancConnectome  # noqa: E402
from brain.banc_simulator import BancSimulator, BancStimulation  # noqa: E402
from brain.banc_synapse_policy import (  # noqa: E402
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)

SMOKE_DIRS = (
    "phase_4g4_smoke_t5_seed20261108",
    "phase_4g4_smoke_t5_seed20261108_repeat",
)
CONFIG_PATH = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
OUTPUT_PATH = PROJECT_ROOT / "reports" / "PHASE_4G4_PROPAGATION_VALIDATION.json"

EXCITATORY = "acetylcholine"
INHIBITORY = "gaba"


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
    verified: list[str | None],
    predicted: list[str | None] | None = None,
    *,
    sign_policy: SignPolicy | None = None,
    weight_policy: WeightPolicy | None = None,
):
    nodes = pd.DataFrame(
        {
            "banc_888_id": [str(value) for value in graph.root_ids],
            "node_index": np.arange(graph.n_nodes),
            "neurotransmitter_verified": verified,
            "neurotransmitter_predicted": (
                [None] * graph.n_nodes if predicted is None else predicted
            ),
        }
    )
    return build_synapse_policy(
        graph,
        nodes,
        sign_policy or SignPolicy(),
        weight_policy or WeightPolicy(),
    )


def run_sim(
    n_nodes: int,
    edges: list[tuple[int, int, int]],
    verified: list[str | None],
    *,
    predicted: list[str | None] | None = None,
    sign_policy: SignPolicy | None = None,
    weight_policy: WeightPolicy | None = None,
    stimulation: BancStimulation | None = None,
    duration_ms: float = 40.0,
    dt_ms: float = 0.5,
    seed: int = 0,
    noise_std_pa: float = 0.0,
):
    graph = make_graph(n_nodes, edges)
    policy = make_policy(
        graph,
        verified,
        predicted,
        sign_policy=sign_policy,
        weight_policy=weight_policy,
    )
    simulator = BancSimulator(
        graph,
        policy,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        seed=seed,
        noise_std_pa=noise_std_pa,
        stimulation=stimulation,
    )
    return graph, policy, simulator, simulator.run()


def spike_times(result, neuron: int) -> np.ndarray:
    mask = result.recorder.spike_neuron_indices == neuron
    return np.asarray(result.recorder.spike_times_ms[mask], dtype=np.float64)


def first_spike(result, neuron: int) -> float | None:
    times = spike_times(result, neuron)
    return float(times.min()) if times.size else None


def spike_hash(result) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(result.recorder.spike_times_ms).tobytes())
    digest.update(
        np.ascontiguousarray(result.recorder.spike_neuron_indices).tobytes()
    )
    return digest.hexdigest()


def main() -> int:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    checks: list[dict] = []

    def add(
        name: str,
        description: str,
        expectation: str,
        observed: dict,
        passed: bool,
    ) -> None:
        checks.append(
            {
                "name": name,
                "description": description,
                "expectation": expectation,
                "observed": observed,
                "passed": bool(passed),
            }
        )

    # Common chain: 4 sources -> 4 intermediates -> 1 target, all excitatory.
    n_nodes = 9
    chain_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(intermediate, 8, 500) for intermediate in range(4, 8)]
    chain_labels = [EXCITATORY] * 9
    stim = BancStimulation(np.arange(4), 2000.0, 1.0, 3.0)

    baseline_graph, _, _, baseline = run_sim(
        n_nodes, chain_edges, chain_labels, stimulation=stim
    )
    baseline_sources = [first_spike(baseline, n) for n in range(4)]
    baseline_inter = [first_spike(baseline, n) for n in range(4, 8)]
    baseline_target = first_spike(baseline, 8)
    baseline_target_count = int(spike_times(baseline, 8).size)

    # 1. convergent chain preserves source -> intermediate -> target order
    ordered = (
        all(value is not None for value in baseline_sources + baseline_inter)
        and baseline_target is not None
        and min(baseline_inter) >= max(baseline_sources) + 1.0 - 1e-9
        and baseline_target >= max(baseline_inter) + 1.0 - 1e-9
    )
    add(
        "convergent_chain_ordering",
        "Four stimulated sources drive four intermediates, which converge on one target.",
        "Every layer spikes and each layer is at least one delay later than the previous.",
        {
            "source_first_spikes_ms": baseline_sources,
            "intermediate_first_spikes_ms": baseline_inter,
            "target_first_spike_ms": baseline_target,
            "target_spike_count": baseline_target_count,
            "spike_transmissions": baseline.summary["synaptic_transmission"]["spike_transmissions"],
        },
        ordered,
    )

    # 2. a single capped structural edge does not fire a resting neuron
    _, _, _, single = run_sim(
        2,
        [(0, 1, 300)],
        [EXCITATORY, EXCITATORY],
        stimulation=BancStimulation(np.array([0]), 2000.0, 1.0, 3.0),
    )
    single_target = spike_times(single, 1)
    add(
        "single_edge_attenuation",
        "One 300 pA capped edge from a driven source to a resting target.",
        "The source spikes; the single structural edge alone is below firing threshold.",
        {
            "source_spikes": int(spike_times(single, 0).size),
            "target_spikes": int(single_target.size),
            "max_excitatory_synaptic_current_pa": single.summary["diagnostics"]["max_excitatory_synaptic_current_pa"],
            "note": "300 pA through g=10 nS is 30 mV of steady drive but the exponential EPSP peaks well below it; a resting neuron needs temporal summation.",
        },
        spike_times(single, 0).size > 0 and single_target.size == 0,
    )

    # 3. convergence of four weaker edges fires the target
    _, _, _, convergence = run_sim(
        5,
        [(source, 4, 300) for source in range(4)],
        [EXCITATORY] * 5,
        stimulation=BancStimulation(np.arange(4), 2000.0, 1.0, 3.0),
    )
    add(
        "convergence_required",
        "Four sources each deliver the same 300 pA capped edge to one target.",
        "Convergent input fires the target while a single edge does not.",
        {
            "target_spikes": int(spike_times(convergence, 4).size),
            "target_first_spike_ms": first_spike(convergence, 4),
            "max_excitatory_synaptic_current_pa": convergence.summary["diagnostics"]["max_excitatory_synaptic_current_pa"],
        },
        spike_times(convergence, 4).size > 0,
    )

    # 4. removing the downstream edges silences only the target
    downstream_removed = [
        edge for edge in chain_edges if edge[1] != 8
    ]
    _, _, _, removed_down = run_sim(
        n_nodes,
        downstream_removed,
        chain_labels,
        stimulation=stim,
    )
    removed_inter = [spike_times(removed_down, n) for n in range(4, 8)]
    inter_unchanged = all(
        np.array_equal(before, after)
        for before, after in zip(removed_inter, [spike_times(baseline, n) for n in range(4, 8)])
    )
    add(
        "edge_removal_downstream",
        "Delete every intermediate -> target edge, keep everything else.",
        "Intermediates spike exactly as in the baseline; the target is silent.",
        {
            "intermediate_trains_identical": inter_unchanged,
            "target_spikes": int(spike_times(removed_down, 8).size),
        },
        inter_unchanged and spike_times(removed_down, 8).size == 0,
    )

    # 5. removing the upstream edges silences the intermediate layer
    upstream_removed = [edge for edge in chain_edges if edge[0] >= 4]
    _, _, _, removed_up = run_sim(
        n_nodes,
        upstream_removed,
        chain_labels,
        stimulation=stim,
    )
    add(
        "edge_removal_upstream",
        "Delete every source -> intermediate edge.",
        "Stimulated sources still spike; intermediates and target are silent.",
        {
            "source_spikes": [int(spike_times(removed_up, n).size) for n in range(4)],
            "intermediate_spikes": [int(spike_times(removed_up, n).size) for n in range(4, 8)],
            "target_spikes": int(spike_times(removed_up, 8).size),
        },
        all(spike_times(removed_up, n).size > 0 for n in range(4))
        and all(spike_times(removed_up, n).size == 0 for n in range(4, 8))
        and spike_times(removed_up, 8).size == 0,
    )

    # 6. reducing the converging weight below recruitment silences the target
    weak_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(intermediate, 8, 10) for intermediate in range(4, 8)]
    _, _, _, weak = run_sim(n_nodes, weak_edges, chain_labels, stimulation=stim)
    add(
        "weight_reduction_below_recruitment",
        "Reduce intermediate -> target counts from 500 to 10 (28 pA per edge).",
        "Intermediates still fire; the target no longer reaches threshold.",
        {
            "intermediate_spikes": [int(spike_times(weak, n).size) for n in range(4, 8)],
            "target_spikes": int(spike_times(weak, 8).size),
            "max_excitatory_synaptic_current_pa": weak.summary["diagnostics"]["max_excitatory_synaptic_current_pa"],
        },
        all(spike_times(weak, n).size > 0 for n in range(4, 8))
        and spike_times(weak, 8).size == 0,
    )

    # 7. a weaker uncapped weight does not advance the target relative to a
    # capped one
    moderate_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(intermediate, 8, 200) for intermediate in range(4, 8)]
    _, _, _, moderate = run_sim(
        n_nodes, moderate_edges, chain_labels, stimulation=stim
    )
    add(
        "weight_monotonicity",
        "Intermediate -> target counts 200 (266 pA, uncapped) versus 500 (capped at 300 pA).",
        "The stronger capped baseline does not fire the target later than the weaker uncapped input.",
        {
            "baseline_target_first_spike_ms": baseline_target,
            "moderate_target_first_spike_ms": first_spike(moderate, 8),
            "baseline_target_spikes": baseline_target_count,
            "moderate_target_spikes": int(spike_times(moderate, 8).size),
        },
        first_spike(moderate, 8) is not None
        and baseline_target is not None
        and baseline_target <= first_spike(moderate, 8) + 1e-9,
    )

    # 8. above the cap, larger counts are numerically identical
    sat_a_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(intermediate, 8, 240) for intermediate in range(4, 8)]
    sat_b_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(intermediate, 8, 5000) for intermediate in range(4, 8)]
    _, _, _, sat_a = run_sim(n_nodes, sat_a_edges, chain_labels, stimulation=stim)
    _, _, _, sat_b = run_sim(n_nodes, sat_b_edges, chain_labels, stimulation=stim)
    cap_threshold = (300.0 / 5.0) ** (1.0 / 0.75)
    add(
        "cap_saturation_equivalence",
        "Counts 240 and 5000 both exceed the 300 pA cap.",
        "Spike trains are bit-identical because both weights saturate at the cap.",
        {
            "count_at_cap": round(float(cap_threshold), 2),
            "hash_240": spike_hash(sat_a),
            "hash_5000": spike_hash(sat_b),
        },
        spike_hash(sat_a) == spike_hash(sat_b),
    )

    # 9. reversing the downstream direction removes the target response
    reversed_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ] + [(8, intermediate, 500) for intermediate in range(4, 8)]
    _, _, _, reversed_result = run_sim(
        n_nodes, reversed_edges, chain_labels, stimulation=stim
    )
    add(
        "direction_reversal",
        "Reverse every intermediate -> target edge to target -> intermediate.",
        "Intermediates still fire from the sources; the unstimulated target is silent.",
        {
            "intermediate_spikes": [int(spike_times(reversed_result, n).size) for n in range(4, 8)],
            "target_spikes": int(spike_times(reversed_result, 8).size),
        },
        all(spike_times(reversed_result, n).size > 0 for n in range(4, 8))
        and spike_times(reversed_result, 8).size == 0,
    )

    # 10. an all-inhibitory intermediate layer cannot drive the target
    inhibitory_labels = [EXCITATORY] * 4 + [INHIBITORY] * 4 + [EXCITATORY]
    _, _, _, inhibitory = run_sim(
        n_nodes, chain_edges, inhibitory_labels, stimulation=stim
    )
    add(
        "inhibitory_only_target_silent",
        "Label all four intermediates inhibitory; keep identical structure and drive.",
        "Intermediates spike but deliver inhibition; the target does not fire.",
        {
            "intermediate_spikes": [int(spike_times(inhibitory, n).size) for n in range(4, 8)],
            "target_spikes": int(spike_times(inhibitory, 8).size),
            "max_inhibitory_synaptic_current_pa": inhibitory.summary["diagnostics"]["max_inhibitory_synaptic_current_pa"],
            "min_membrane_mv": inhibitory.summary["diagnostics"]["min_membrane_mv"],
        },
        all(spike_times(inhibitory, n).size > 0 for n in range(4, 8))
        and spike_times(inhibitory, 8).size == 0
        and inhibitory.summary["diagnostics"]["max_inhibitory_synaptic_current_pa"] > 0,
    )

    # 11. one inhibitory input among four changes target recruitment
    mixed_labels = [EXCITATORY] * 4 + [INHIBITORY] + [EXCITATORY] * 3 + [EXCITATORY]
    _, _, _, mixed = run_sim(n_nodes, chain_edges, mixed_labels, stimulation=stim)
    mixed_target_count = int(spike_times(mixed, 8).size)
    mixed_target_first = first_spike(mixed, 8)
    add(
        "inhibitory_mixed_reduces_target",
        "Make one of the four converging intermediates inhibitory.",
        "The target fires no earlier and no more often than the all-excitatory baseline; inhibitory current is present.",
        {
            "baseline_target_spikes": baseline_target_count,
            "mixed_target_spikes": mixed_target_count,
            "baseline_target_first_spike_ms": baseline_target,
            "mixed_target_first_spike_ms": mixed_target_first,
            "max_inhibitory_synaptic_current_pa": mixed.summary["diagnostics"]["max_inhibitory_synaptic_current_pa"],
        },
        mixed_target_count <= baseline_target_count
        and (
            mixed_target_first is None
            or baseline_target is None
            or mixed_target_first >= baseline_target - 1e-9
        )
        and mixed.summary["diagnostics"]["max_inhibitory_synaptic_current_pa"] > 0,
    )

    # 12. unannotated intermediates contribute exactly zero current
    unknown_labels = [EXCITATORY] * 4 + [None] * 4 + [EXCITATORY]
    unknown_graph, unknown_policy, _, unknown = run_sim(
        n_nodes, chain_edges, unknown_labels, stimulation=stim
    )
    target_edge_weights = [
        float(unknown_policy.edge_exc_weight[row] + unknown_policy.edge_inh_weight[row])
        for row in range(unknown_graph.n_edges)
        if int(unknown_graph.edge_dst[row]) == 8
    ]
    add(
        "unknown_sign_excluded",
        "Leave the intermediates unannotated so their edges have unknown sign.",
        "Intermediates spike; every edge into the target carries zero weight; target silent.",
        {
            "intermediate_spikes": [int(spike_times(unknown, n).size) for n in range(4, 8)],
            "target_edge_weights_pa": target_edge_weights,
            "target_spikes": int(spike_times(unknown, 8).size),
        },
        all(spike_times(unknown, n).size > 0 for n in range(4, 8))
        and target_edge_weights
        and all(weight == 0.0 for weight in target_edge_weights)
        and spike_times(unknown, 8).size == 0,
    )

    # 13/14. predicted-only labels are excluded by default and admitted on request
    predicted_labels = [EXCITATORY] * 4 + [None] * 4 + [EXCITATORY]
    predicted_values = [None] * 4 + ["acetylcholine"] * 4 + [None]
    _, primary_policy, _, predicted_primary = run_sim(
        n_nodes,
        chain_edges,
        predicted_labels,
        predicted=predicted_values,
        stimulation=stim,
    )
    fallback_policy = SignPolicy.from_config(
        {**config["transmitter_sign_policy"], "predicted_fallback": True}
    )
    _, fallback_built_policy, _, predicted_fallback = run_sim(
        n_nodes,
        chain_edges,
        predicted_labels,
        predicted=predicted_values,
        sign_policy=fallback_policy,
        stimulation=stim,
    )
    add(
        "predicted_only_excluded",
        "Intermediates have predicted but no verified transmitter, under the primary policy.",
        "Predicted labels are not part of the primary policy; the target is silent.",
        {
            "target_spikes": int(spike_times(predicted_primary, 8).size),
            "declared_policy": primary_policy.coverage["declared_policy"],
        },
        spike_times(predicted_primary, 8).size == 0,
    )
    add(
        "predicted_fallback_enables_propagation",
        "Same labels, predicted fallback enabled as a declared sensitivity condition.",
        "The target now fires, which shows the fallback changes results and must be reported as a sensitivity.",
        {
            "target_spikes": int(spike_times(predicted_fallback, 8).size),
            "declared_policy": fallback_built_policy.coverage["declared_policy"],
        },
        spike_times(predicted_fallback, 8).size > 0,
    )

    # 15. no stimulation means no activity
    _, _, _, quiet = run_sim(n_nodes, chain_edges, chain_labels)
    add(
        "no_stimulation_silence",
        "Identical network with no stimulation and no noise.",
        "No neuron spikes.",
        {"total_spikes": quiet.summary["activity"]["n_spikes"]},
        quiet.summary["activity"]["n_spikes"] == 0,
    )

    # 16. sub-rheobase injection does not fire; suprathreshold injection does
    _, _, _, subthreshold = run_sim(
        1,
        [],
        [EXCITATORY],
        stimulation=BancStimulation(np.array([0]), 100.0, 1.0, 20.0),
    )
    _, _, _, suprathreshold = run_sim(
        1,
        [],
        [EXCITATORY],
        stimulation=BancStimulation(np.array([0]), 300.0, 1.0, 20.0),
    )
    add(
        "current_injection_threshold",
        "Inject 100 pA and 300 pA into a single isolated neuron.",
        "100 pA is below the 150 pA rheobase and does not fire; 300 pA does.",
        {
            "spikes_at_100_pa": int(subthreshold.summary["activity"]["n_spikes"]),
            "spikes_at_300_pa": int(suprathreshold.summary["activity"]["n_spikes"]),
        },
        subthreshold.summary["activity"]["n_spikes"] == 0
        and suprathreshold.summary["activity"]["n_spikes"] > 0,
    )

    # 17. transmission respects the configured delay
    transparent_edges = [
        (source, intermediate, 500)
        for source in range(4)
        for intermediate in range(4, 8)
    ]
    _, _, _, delayed = run_sim(
        8,
        transparent_edges,
        [EXCITATORY] * 8,
        stimulation=stim,
    )
    latency = min(first_spike(delayed, n) for n in range(4, 8)) - max(
        first_spike(delayed, n) for n in range(4)
    )
    add(
        "delay_quantisation",
        "Measure the shortest source -> intermediate latency on the chain.",
        "Latency is at least the 1.0 ms configured axonal delay.",
        {
            "measured_min_latency_ms": round(float(latency), 3),
            "configured_delay_ms": 1.0,
            "dt_ms": 0.5,
        },
        latency >= 1.0 - 1e-9,
    )

    # 18. refractory period bounds the maximum rate
    _, _, _, refractory = run_sim(
        1,
        [],
        [EXCITATORY],
        stimulation=BancStimulation(np.array([0]), 5000.0, 1.0, 30.0),
    )
    refractory_times = spike_times(refractory, 0)
    isi = np.diff(refractory_times)
    add(
        "refractory_interval",
        "Drive one neuron at 5000 pA for 30 ms.",
        "Every inter-spike interval is at least the 2 ms refractory period.",
        {
            "spike_count": int(refractory_times.size),
            "min_isi_ms": round(float(isi.min()), 3) if isi.size else None,
            "max_isi_ms": round(float(isi.max()), 3) if isi.size else None,
        },
        refractory_times.size > 1 and float(isi.min()) >= 2.0 - 1e-9,
    )

    # 19. isolated nodes never spike
    _, _, _, isolated = run_sim(
        6,
        [(0, 1, 500), (1, 2, 500)],
        [EXCITATORY] * 6,
        stimulation=BancStimulation(np.array([0]), 3000.0, 1.0, 10.0),
    )
    add(
        "isolated_nodes_silent",
        "Add three isolated nodes to a small driven chain.",
        "Only the connected neurons spike; isolated nodes stay silent.",
        {
            "connected_spikes": [int(spike_times(isolated, n).size) for n in range(3)],
            "isolated_spikes": [int(spike_times(isolated, n).size) for n in (3, 4, 5)],
        },
        all(spike_times(isolated, n).size == 0 for n in (3, 4, 5)),
    )

    # 20. seeded noise is reproducible; a different seed is not
    _, _, _, seeded_a = run_sim(
        n_nodes,
        chain_edges,
        chain_labels,
        stimulation=stim,
        duration_ms=60.0,
        seed=7,
        noise_std_pa=50.0,
    )
    _, _, _, seeded_b = run_sim(
        n_nodes,
        chain_edges,
        chain_labels,
        stimulation=stim,
        duration_ms=60.0,
        seed=7,
        noise_std_pa=50.0,
    )
    _, _, _, seeded_c = run_sim(
        n_nodes,
        chain_edges,
        chain_labels,
        stimulation=stim,
        duration_ms=60.0,
        seed=8,
        noise_std_pa=50.0,
    )
    hash_a, hash_b, hash_c = spike_hash(seeded_a), spike_hash(seeded_b), spike_hash(seeded_c)
    add(
        "deterministic_repeat",
        "Run the same noisy chain twice with seed 7 and once with seed 8.",
        "The two seed-7 runs are bit-identical; the seed-8 run differs.",
        {
            "hash_seed7_run1": hash_a,
            "hash_seed7_run2": hash_b,
            "hash_seed8": hash_c,
            "seed7_spikes": seeded_a.summary["activity"]["n_spikes"],
            "seed8_spikes": seeded_c.summary["activity"]["n_spikes"],
        },
        hash_a == hash_b and hash_a != hash_c,
    )

    # Full-graph smoke record and its determinism repeat.
    smoke = []
    for name in SMOKE_DIRS:
        path = PROJECT_ROOT / "experiments" / "results" / "phase_4g" / name / "run_metadata.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        smoke.append(
            {
                "directory": str(path.parent.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "threshold": payload["summary"]["graph"]["graph_threshold"],
                "nodes": payload["summary"]["graph"]["n_nodes"],
                "edges": payload["summary"]["graph"]["n_edges"],
                "synapses": payload["summary"]["graph"]["n_synapses"],
                "stimulated_neurons": len(payload["stimulus_indices"]),
                "stimulation": payload["summary"]["stimulation"],
                "duration_ms": payload["summary"]["simulation"]["duration_ms"],
                "dt_ms": payload["summary"]["simulation"]["dt_ms"],
                "seed": payload["summary"]["simulation"]["seed"],
                "spikes": payload["summary"]["activity"]["n_spikes"],
                "active_neurons": payload["summary"]["activity"]["active_neurons"],
                "active_fraction": payload["summary"]["activity"]["active_fraction"],
                "mean_rate_hz": payload["summary"]["activity"]["mean_rate_hz"],
                "runtime_s": payload["summary"]["simulation"]["runtime_s"],
                "steps_per_second": payload["summary"]["simulation"]["steps_per_second"],
                "memory_after": payload["setup"]["memory_after"],
                "activity_sha256": payload["activity_sha256"],
            }
        )
    smoke_deterministic = smoke[0]["activity_sha256"] == smoke[1]["activity_sha256"]

    passed = sum(1 for check in checks if check["passed"])
    payload = {
        "phase": "4G.4",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
        "policy_config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "toy_graph_suite": {
            "checks_total": len(checks),
            "checks_passed": passed,
            "checks_failed": len(checks) - passed,
            "checks": checks,
        },
        "full_banc_smoke": {
            "selection": (
                "highest_out_degree: 64 nodes with the largest structural out-degree "
                "at threshold 5, ties broken by ascending node index; chosen before "
                "any simulation output was inspected"
            ),
            "runs": smoke,
            "deterministic_across_repeats": smoke_deterministic,
        },
        "verdict": (
            "PASS" if passed == len(checks) and smoke_deterministic else "FAIL"
        ),
        "limitations": [
            "Toy graphs are synthetic and use the same neuron and synapse models as the full graph; they test implementation, not biology.",
            "A structural edge under the primary weight policy is insufficient to fire a resting neuron; propagation in the full graph depends on convergence.",
            "The single smoke test demonstrates that a seeded, sparse full-graph simulation runs and is reproducible; it is not evidence of physiological propagation.",
        ],
        "runtime_s": round(time.perf_counter() - started, 3),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "checks": len(checks),
                "passed": passed,
                "failed": len(checks) - passed,
                "smoke_deterministic": smoke_deterministic,
                "verdict": payload["verdict"],
                "output": str(OUTPUT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "runtime_s": payload["runtime_s"],
            },
            indent=2,
        )
    )
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
