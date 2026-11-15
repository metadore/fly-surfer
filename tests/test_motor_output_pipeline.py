"""Phase 4 motor recording, game-action interface and BANC integration."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import BancConnectome
from brain.banc_simulator import BancSimulator, BancStimulation
from brain.banc_synapse_policy import (
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)
from brain.neural_activity import SpikeRecorder
from brain.neuron_model import LIFParameters
from motor.action_decoder import (
    NO_ACTION,
    UNMAPPED,
    GameActionDecoder,
)
from motor.activity_recorder import MotorActivityRecorder
from motor.motor_decoder import DecoderConfig
from motor.populations import (
    ACTION_POPULATIONS,
    MotorPopulations,
    build_populations,
)


# ---------------------------------------------------------------------------
# synthetic annotations
# ---------------------------------------------------------------------------


def pathway_nodes() -> pd.DataFrame:
    """Four motor neurons, then descending, ascending and VNC intrinsic."""
    return pd.DataFrame(
        {
            "node_index": np.arange(10, dtype=np.int64),
            "banc_888_id": np.arange(1000, 1010, dtype=np.int64),
            "super_class": [
                "motor",
                "motor",
                "motor",
                "motor",
                "descending",
                "descending",
                "ascending",
                "ascending",
                "ventral_nerve_cord_intrinsic",
                "ventral_nerve_cord_intrinsic",
            ],
            "cell_class": [None] * 10,
            "cell_sub_class": [None] * 10,
            "cell_type": [None] * 10,
            "side": ["left", "left", "right", None, None, None, None, None, None, None],
            "body_part_effector": [
                "front_leg",
                "front_leg",
                "middle_leg",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            "peripheral_target_type": [
                None,
                None,
                None,
                "tergotrochanter_extensor_muscle",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            "neurotransmitter_verified": [
                "acetylcholine",
                "acetylcholine",
                "acetylcholine",
                "acetylcholine",
                "glutamate",
                "glutamate",
                "acetylcholine",
                "acetylcholine",
                "acetylcholine",
                "acetylcholine",
            ],
            "proofread": [True] * 10,
        }
    )


def pathway_populations() -> tuple[pd.DataFrame, MotorPopulations]:
    nodes = pathway_nodes()
    return nodes, build_populations(nodes, n_neurons=10, threshold=5)


def make_recorder(events, n_neurons: int = 10) -> SpikeRecorder:
    recorder = SpikeRecorder(n_neurons, max_spikes=10_000)
    for step, indices in events:
        recorder.record(
            int(step), np.asarray(indices, dtype=np.int32), dt_ms=1.0
        )
    return recorder


def action_populations(
    sizes: dict[str, int], n_neurons: int | None = None
) -> MotorPopulations:
    total = int(n_neurons if n_neurons is not None else sum(sizes.values()))
    masks = {}
    cursor = 0
    for action in ACTION_POPULATIONS:
        size = int(sizes.get(action, 0))
        mask = np.zeros(total, dtype=bool)
        mask[cursor : cursor + size] = True
        cursor += size
        masks[action] = mask
    motor = np.zeros(total, dtype=bool)
    for mask in masks.values():
        motor |= mask
    return MotorPopulations(
        n_neurons=total,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=np.zeros(total, dtype=bool),
        composition={},
        provenance={},
    )


def action_spikes(
    populations: MotorPopulations,
    active: dict[str, int],
    *,
    time_ms: float = 25.0,
) -> tuple[np.ndarray, np.ndarray]:
    times = []
    indices = []
    for action, count in active.items():
        members = np.flatnonzero(populations.mask(action))[: int(count)]
        times.append(np.full(members.size, time_ms, dtype=float))
        indices.append(members)
    if not times:
        return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
    return np.concatenate(times), np.concatenate(indices).astype(np.int64)


# ---------------------------------------------------------------------------
# motor activity recorder
# ---------------------------------------------------------------------------


def test_recorder_selects_annotated_populations():
    nodes, populations = pathway_populations()
    recorder = MotorActivityRecorder(
        make_recorder([]), populations, nodes
    )
    assert recorder.selection("motor").size == 4
    assert recorder.selection("descending").size == 2
    assert recorder.selection("ascending").size == 2
    assert recorder.selection("vnc_intrinsic").size == 2
    assert recorder.selection("non_motor").size == 6
    assert recorder.selection("left_motor").size == 2
    assert recorder.selection("right_motor").size == 1
    assert recorder.selection("jump_motor").size == 1
    assert list(recorder.selection("motor").banc_ids) == [1000, 1001, 1002, 1003]
    assert recorder.selection("motor").role == "motor_neuron"
    assert "super_class == 'motor'" in recorder.selection("motor").definition


def test_window_counts_rates_and_half_open_boundaries():
    nodes, populations = pathway_populations()
    recorder = MotorActivityRecorder(
        make_recorder(
            [
                (0, [0, 1]),  # t = 1 ms
                (1, [0]),  # t = 2 ms
                (2, [2]),  # t = 3 ms
                (3, [0]),  # t = 4 ms
            ]
        ),
        populations,
        nodes,
    )
    window = recorder.time_window(1.5, 3.5)
    assert window.n_spikes == 2
    assert window.duration_ms == pytest.approx(2.0)
    motor = window.populations["motor"]
    assert motor["spikes"] == 2
    assert motor["active_neurons"] == 2
    assert motor["active_fraction"] == pytest.approx(0.5)
    assert motor["mean_rate_hz"] == pytest.approx(250.0)

    at_start = recorder.time_window(1.0, 2.0)
    assert at_start.n_spikes == 2  # time 1 is included
    at_end = recorder.time_window(1.0, 3.0)
    assert at_end.n_spikes == 3  # times 1 and 2; time 3 is excluded


def test_direct_stimulation_and_downstream_are_separated():
    nodes, populations = pathway_populations()
    recorder = MotorActivityRecorder(
        make_recorder([(0, [0, 1, 4])]),
        populations,
        nodes,
        stimulated_indices=[0, 4],
    )
    window = recorder.time_window(0.0, 2.0)
    assert window.stimulated_neurons == 2
    assert window.direct is not None and window.direct["spikes"] == 2
    assert window.downstream is not None and window.downstream["spikes"] == 1
    motor = window.populations["motor"]
    assert motor["direct_spikes"] == 1
    assert motor["downstream_spikes"] == 1
    descending = window.populations["descending"]
    assert descending["direct_spikes"] == 1
    assert descending["downstream_spikes"] == 0


def test_silent_populations_are_safe():
    nodes, populations = pathway_populations()
    recorder = MotorActivityRecorder(make_recorder([]), populations, nodes)
    window = recorder.time_window(0.0, 100.0)
    assert window.n_spikes == 0
    for block in window.populations.values():
        assert block["spikes"] == 0
        assert block["active_neurons"] == 0
        assert block["mean_rate_hz"] == 0.0
    table = recorder.per_neuron(0.0, 100.0, "motor")
    assert table["n_neurons"] == 4
    assert table["spikes"] == [0, 0, 0, 0]
    assert table["rate_hz"] == [0.0, 0.0, 0.0, 0.0]
    assert table["active"] == [False, False, False, False]


def test_per_neuron_preserves_ids_and_annotation_provenance():
    nodes, populations = pathway_populations()
    recorder = MotorActivityRecorder(
        make_recorder([(0, [0, 0, 2])]), populations, nodes
    )
    table = recorder.per_neuron(0.0, 10.0, "motor")
    assert table["banc_888_id"] == [1000, 1001, 1002, 1003]
    assert table["spikes"] == [2, 0, 1, 0]
    assert table["rate_hz"] == [200.0, 0.0, 100.0, 0.0]
    assert table["annotations"]["super_class"] == ["motor"] * 4
    assert table["annotations"]["side"] == ["left", "left", "right", None]
    assert table["annotations"]["body_part_effector"] == [
        "front_leg",
        "front_leg",
        "middle_leg",
        None,
    ]
    assert table["annotations"]["neurotransmitter_verified"][0] == "acetylcholine"

    active_only = recorder.per_neuron(
        0.0, 10.0, "motor", include_silent=False
    )
    assert active_only["banc_888_id"] == [1000, 1002]


def test_recorder_validates_its_inputs():
    nodes, populations = pathway_populations()
    with pytest.raises(ValueError, match="node table"):
        MotorActivityRecorder(make_recorder([]), populations, nodes.iloc[:5])
    with pytest.raises(ValueError, match="neuron count"):
        MotorActivityRecorder(make_recorder([], n_neurons=9), populations, nodes)
    recorder = MotorActivityRecorder(make_recorder([]), populations, nodes)
    with pytest.raises(KeyError):
        recorder.selection("sensory")
    with pytest.raises(ValueError, match="window end"):
        recorder.time_window(5.0, 5.0)
    with pytest.raises(ValueError, match="outside"):
        recorder.set_stimulated_indices([50])


# ---------------------------------------------------------------------------
# game-action interface
# ---------------------------------------------------------------------------


def test_no_activity_is_no_action():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    decoder = GameActionDecoder(populations)
    output = decoder.decode_window(
        *action_spikes(populations, {}), 0.0, 50.0
    )
    assert output.state == NO_ACTION
    assert output.neutral
    assert output.action is None
    assert output.supported
    assert output.confidence == 0.0
    assert output.active_channels == ()
    assert output.unresolved_channels["ROLL"]


def test_left_activity_maps_to_the_left_channel():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    decoder = GameActionDecoder(populations)
    output = decoder.decode_window(
        *action_spikes(populations, {"LEFT": 6}), 0.0, 50.0
    )
    assert output.state == "LEFT"
    assert output.action == "LEFT"
    assert output.supported
    assert output.confidence == pytest.approx(0.6)
    assert output.activation_scores["LEFT"] == pytest.approx(0.6)
    assert output.active_channels == ("LEFT",)
    assert output.simultaneous is False
    assert output.evidence["LEFT"]["spikes"] == 6


def test_simultaneous_populations_are_reported_not_hidden():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    output = GameActionDecoder(populations).decode_window(
        *action_spikes(populations, {"LEFT": 6, "RIGHT": 6}), 0.0, 50.0
    )
    assert output.state == "LEFT"
    assert output.active_channels == ("LEFT", "RIGHT")
    assert output.simultaneous is True
    assert output.reason == "tie_broken_by_priority"


def test_unassigned_motor_activity_is_not_forced_into_an_action():
    masks = {action: np.zeros(5, dtype=bool) for action in ACTION_POPULATIONS}
    motor = np.zeros(5, dtype=bool)
    motor[4] = True
    unassigned = motor.copy()
    populations = MotorPopulations(
        n_neurons=5,
        threshold=5,
        masks=masks,
        motor_mask=motor,
        unassigned_mask=unassigned,
        composition={},
        provenance={},
    )
    times = np.full(20, 25.0)
    output = GameActionDecoder(populations).decode_window(
        times, np.full(20, 4, dtype=np.int64), 0.0, 50.0
    )
    assert output.state == NO_ACTION
    assert output.active_channels == ()


def test_roll_request_returns_explicit_unmapped_state():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    decoder = GameActionDecoder(populations)
    output = decoder.decode_requested(
        "ROLL",
        *action_spikes(populations, {"LEFT": 10}),
        0.0,
        50.0,
    )
    assert output.state == UNMAPPED
    assert output.unmapped
    assert output.supported is False
    assert output.action == "ROLL"
    assert output.confidence is None
    assert output.requested_channel == "ROLL"
    assert "No published BANC annotation" in output.reason
    assert output.active_channels == ()

    duck = decoder.decode_requested(
        "DUCK",
        *action_spikes(populations, {"LEFT": 10}),
        0.0,
        50.0,
    )
    assert duck.state == UNMAPPED
    assert duck.requested_channel == "DUCK"


def test_thresholds_and_confidence_are_configurable():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    weak = action_spikes(populations, {"LEFT": 4})
    strict = GameActionDecoder(
        populations,
        DecoderConfig(
            activation_threshold=0.5, min_active_neurons=1, min_spikes=1
        ),
    )
    assert strict.decode_window(*weak, 0.0, 50.0).state == NO_ACTION

    confidence_gate = GameActionDecoder(
        populations,
        DecoderConfig(min_active_neurons=1, min_spikes=1),
        confidence_threshold=0.7,
    )
    gated = confidence_gate.decode_window(
        *action_spikes(populations, {"LEFT": 6}), 0.0, 50.0
    )
    assert gated.state == NO_ACTION
    assert gated.reason == "confidence_below_threshold"
    assert gated.confidence == pytest.approx(0.6)


def test_decoding_is_reproducible():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    times, indices = action_spikes(
        populations, {"LEFT": 6, "RIGHT": 5, "JUMP": 4}
    )
    first = GameActionDecoder(populations).decode_window(
        times, indices, 0.0, 50.0
    )
    second = GameActionDecoder(populations).decode_window(
        times, indices, 0.0, 50.0
    )
    assert first.as_dict() == second.as_dict()


def test_describe_lists_supported_and_unresolved_channels():
    populations = action_populations({"LEFT": 10, "RIGHT": 10, "JUMP": 10})
    description = GameActionDecoder(populations).describe()
    assert set(description["supported_channels"]) == set(ACTION_POPULATIONS)
    assert "ROLL" in description["unsupported_channels"]
    assert description["neutral_state"] == NO_ACTION
    assert description["unmapped_state"] == UNMAPPED
    assert description["supported_channels"]["LEFT"]["population"] == "LEFT"


def test_unknown_channel_is_rejected():
    populations = action_populations({"LEFT": 10})
    decoder = GameActionDecoder(populations)
    with pytest.raises(ValueError, match="unknown channel"):
        decoder.decode_requested(
            "BRAKE",
            np.empty(0, dtype=float),
            np.empty(0, dtype=np.int64),
            0.0,
            50.0,
        )


# ---------------------------------------------------------------------------
# small BANC-format end-to-end integration
# ---------------------------------------------------------------------------


def banc_setup():
    """One VNC intrinsic excitatory source driving two left motor neurons."""
    root_ids = np.arange(5000, 5005, dtype=np.int64)
    edge_src = np.array([0, 0], dtype=np.int64)
    edge_dst = np.array([1, 2], dtype=np.int64)
    edge_weight = np.array([20, 20], dtype=np.int64)
    out_indptr = np.zeros(6, dtype=np.int64)
    out_indptr[1:] = np.cumsum(np.bincount(edge_src, minlength=5))
    in_indptr = np.zeros(6, dtype=np.int64)
    in_indptr[1:] = np.cumsum(np.bincount(edge_dst, minlength=5))
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int64)
    graph = BancConnectome(
        root_ids=root_ids,
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        threshold=5,
    )
    nodes = pd.DataFrame(
        {
            "node_index": np.arange(5, dtype=np.int64),
            "banc_888_id": root_ids,
            "super_class": [
                "ventral_nerve_cord_intrinsic",
                "motor",
                "motor",
                "motor",
                "motor",
            ],
            "cell_class": [None] * 5,
            "cell_sub_class": [None] * 5,
            "cell_type": [None] * 5,
            "side": [None, "left", "left", "right", None],
            "body_part_effector": [
                None,
                "front_leg",
                "front_leg",
                "middle_leg",
                None,
            ],
            "peripheral_target_type": [
                None,
                None,
                None,
                None,
                "tergotrochanter_extensor_muscle",
            ],
            "neurotransmitter_verified": ["acetylcholine"] * 5,
            "neurotransmitter_predicted": [None] * 5,
            "proofread": [True] * 5,
        }
    )
    policy = build_synapse_policy(
        graph,
        nodes,
        SignPolicy(),
        WeightPolicy(scale_pa=50.0, cap_pa=300.0),
    )
    populations = build_populations(nodes, n_neurons=5, threshold=5)
    return graph, nodes, policy, populations


def simulate(graph, policy, stimulation=None):
    simulator = BancSimulator(
        graph,
        policy,
        neuron_params=LIFParameters(),
        dt_ms=0.5,
        duration_ms=80.0,
        seed=7,
        stimulation=stimulation,
        max_recorded_spikes=10_000,
    )
    return simulator.run()


def test_small_banc_graph_activity_reaches_motor_output():
    graph, nodes, policy, populations = banc_setup()
    stimulation = BancStimulation(
        np.array([0], dtype=np.int64), 600.0, 0.0, 40.0, label="test_probe"
    )
    result = simulate(graph, policy, stimulation)
    recorder = MotorActivityRecorder(
        result.recorder, populations, nodes, graph=graph, stimulated_indices=[0]
    )
    window = recorder.time_window(0.0, 80.0)
    assert window.direct is not None and window.direct["spikes"] > 0
    assert window.populations["motor"]["spikes"] > 0
    assert window.populations["motor"]["direct_spikes"] == 0
    assert window.populations["motor"]["downstream_spikes"] > 0

    decoder = GameActionDecoder(
        populations,
        DecoderConfig(
            window_ms=80.0,
            step_ms=80.0,
            min_active_neurons=1,
            min_spikes=1,
        ),
    )
    outputs = decoder.decode_series(
        result.recorder.spike_times_ms,
        result.recorder.spike_neuron_indices,
        0.0,
        80.0,
    )
    assert len(outputs) == 1
    assert outputs[0].state == "LEFT"
    assert outputs[0].supported
    assert outputs[0].confidence > 0.0
    assert decoder.decode_requested(
        "ROLL",
        result.recorder.spike_times_ms,
        result.recorder.spike_neuron_indices,
        0.0,
        80.0,
    ).state == UNMAPPED


def test_no_stimulus_control_stays_silent():
    graph, nodes, policy, populations = banc_setup()
    result = simulate(graph, policy)
    assert result.recorder.n_spikes == 0
    recorder = MotorActivityRecorder(
        result.recorder, populations, nodes, graph=graph
    )
    window = recorder.time_window(0.0, 80.0)
    assert window.n_spikes == 0
    assert window.populations["motor"]["spikes"] == 0
    decoder = GameActionDecoder(
        populations,
        DecoderConfig(
            window_ms=80.0, step_ms=80.0, min_active_neurons=1, min_spikes=1
        ),
    )
    outputs = decoder.decode_series(
        result.recorder.spike_times_ms,
        result.recorder.spike_neuron_indices,
        0.0,
        80.0,
    )
    assert outputs[0].state == NO_ACTION
