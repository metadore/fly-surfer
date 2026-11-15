"""Non-simulation tests for the P3-3C.5 lane-encoding implementation.

IMPLEMENTATION ONLY. EXECUTION NOT AUTHORISED.

Every test here either validates the frozen configuration, constructs a
scheduler, audits the injected current, or applies arithmetic to synthetic
spike arrays. No test constructs a ``BrainSimulator`` and no test executes an
experiment instance. The three tests at the end are explicitly skipped because
they would require authorised execution.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from experiments.phase_3c import p3_3c5_lane_encoding as module


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def protocol():
    return module.load_protocol()


@pytest.fixture(scope="module")
def graph():
    return module._load_graph()


@pytest.fixture(scope="module")
def base_config():
    return module.build_base_sensory_config()


@pytest.fixture(scope="module")
def bundle(graph, base_config):
    mapping, config = module.build_mapping(
        graph, base_config, module.EXPECTED["main_seeds"][0]
    )
    return {
        "mapping": mapping,
        "config": config,
        "groups": module.lane_groups(mapping),
    }


@pytest.fixture(scope="module")
def scheduler_audits(protocol, bundle, base_config):
    setup = module.build_setup(bundle["mapping"], base_config)
    result = {}
    for condition in protocol["conditions"]:
        scheduler = module.build_scheduler(setup, condition, protocol)
        result[condition["id"]] = {
            "condition": condition,
            "scheduler": scheduler,
            "audit": module.audit_input_current(
                scheduler, condition, bundle["mapping"], protocol
            ),
        }
    return result


@pytest.fixture(scope="module")
def static(protocol, bundle, graph):
    hashes = module.assert_prereg_hashes(protocol)
    return module.static_gates(
        protocol, bundle["mapping"], bundle["groups"], graph, hashes
    )


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _empty_raw_runs(protocol):
    return {
        condition["id"]: {
            "seed": int(module.EXPECTED["main_seeds"][0]),
            "times": np.array([], dtype=np.float64),
            "indices": np.array([], dtype=np.int64),
            "n_steps": 1201,
            "duration_ms": 600.5,
            "stimulated_indices": np.array([], dtype=np.int64),
            "input_audit": {},
            "spike_digest": "",
            "schedule_digest": "",
            "wall_runtime_s": 0.0,
        }
        for condition in protocol["conditions"]
    }


def add_spikes(raw, neuron_ids, times):
    raw["times"] = np.concatenate(
        [raw["times"], np.asarray(times, dtype=np.float64)]
    )
    raw["indices"] = np.concatenate(
        [raw["indices"], np.asarray(neuron_ids, dtype=np.int64)]
    )


def current_at(scheduler, time_ms, n_nodes):
    buffer = np.zeros(n_nodes, dtype=np.float64)
    scheduler.apply(int(round(time_ms / 0.5)), time_ms, buffer)
    return buffer


def seed_analysis(
    primary=0.0,
    dwell=0.0,
    sep200=None,
    sep150=None,
    focal200=False,
    focal150=False,
    dwell_consistency=False,
    silent=False,
    outside=False,
    degenerate=False,
    transition=False,
    endpoint=False,
    delta_r=0.0,
    routes=None,
):
    return {
        "primary": {"value_hz": float(primary)},
        "dwell_replication": {"value_hz": float(dwell)},
        "predicates": {
            "separated_200": sep200,
            "separated_150": sep150,
            "focal_200": bool(focal200),
            "focal_150": bool(focal150),
            "dwell_consistency": bool(dwell_consistency),
            "silent_center": bool(silent),
            "outside_dominates": bool(outside),
            "reference_degenerate": bool(degenerate),
            "transition_onset_only_seed": bool(transition),
            "endpoint_confined": bool(endpoint),
        },
        "delta_r": {"value_hz": float(delta_r)},
        "routes": routes or {},
    }


def classify(cfg, analyses, failed=()):
    gates = {
        seed: {"failed": list(failed) if seed in failed else []}
        for seed in analyses
    }
    return module.classify_campaign(analyses, gates, cfg)


def gate_raw_runs(protocol):
    raw = {
        condition["id"]: {
            "times": np.array([], dtype=np.float64),
            "indices": np.array([], dtype=np.int64),
            "completed": True,
            "n_spikes": 0,
            "stimulus": None,
            "background_current_pa": 0.0,
            "noise_std_pa": 0.0,
            "schedule_digest": "synthetic",
            "seed": int(module.EXPECTED["main_seeds"][0]),
        }
        for condition in protocol["conditions"]
    }
    raw["N0"]["schedule_digest"] = module._sha256_bytes(b"no-input-schedule")

    prefix_150 = np.array([0.0, 10.0, 149.5], dtype=np.float64)
    prefix_ids = np.array([1, 2, 3], dtype=np.int64)
    for condition_id in ("C3", "C4"):
        raw[condition_id]["times"] = prefix_150.copy()
        raw[condition_id]["indices"] = prefix_ids.copy()
    add_spikes(raw["C3"], [4], [160.0])
    add_spikes(raw["C4"], [5], [160.0])

    prefix_400 = np.array([0.0, 10.0, 200.0, 399.5], dtype=np.float64)
    prefix_400_ids = np.array([1, 2, 3, 4], dtype=np.int64)
    for condition_id in ("C1", "T200_LC", "C2", "T200_RC"):
        raw[condition_id]["times"] = prefix_400.copy()
        raw[condition_id]["indices"] = prefix_400_ids.copy()
    add_spikes(raw["C1"], [7], [400.0])
    add_spikes(raw["T200_LC"], [8], [400.0])
    add_spikes(raw["C2"], [9], [400.0])
    add_spikes(raw["T200_RC"], [10], [400.0])
    return raw


def gate_inputs(protocol):
    raw = gate_raw_runs(protocol)
    conditions = module.conditions_by_id(protocol)
    condition_gates_map = {
        condition_id: {
            "E2": {"passed": True},
            "E3": {"passed": True},
            "E4": {"passed": True},
        }
        for condition_id in conditions
    }
    static = {
        gate_id: {"passed": True} for gate_id in ("E6", "E7", "E8", "E13", "E15")
    }
    measurements = {
        condition_id: {
            "outside": {"spikes": 0, "active_neurons": 0, "fraction": 0.0}
        }
        for condition_id in conditions
    }
    return raw, condition_gates_map, static, measurements


# --------------------------------------------------------------------------
# 1. configuration schema and parameter validation
# --------------------------------------------------------------------------


def test_protocol_matches_frozen_constants(protocol):
    assert protocol["phase"] == "P3-3C.5"
    assert protocol["version"] == "p3_3c5_lane_encoding_v1"
    assert protocol["status"] == "IMPLEMENTATION_ONLY_EXECUTION_NOT_AUTHORISED"
    assert protocol["protocol"]["duration_ms"] == 600.5
    assert protocol["protocol"]["frame_interval_ms"] == 50.0
    assert protocol["protocol"]["n_frames"] == 12
    assert protocol["protocol"]["dt_ms"] == 0.5
    assert protocol["protocol"]["n_steps"] == 1201
    assert protocol["protocol"]["current_pa"] == {"player_lane": 200.0}
    assert protocol["protocol"]["total_sensory_current_pa"] == 800.0
    assert protocol["protocol"]["transition_ms"] == {
        "step": 0.0,
        "crossfade": 50.0,
    }
    assert protocol["seeds"]["main"] == module.EXPECTED["main_seeds"]
    assert protocol["seeds"]["pilot"] == module.EXPECTED["pilot_seed"]


def test_protocol_rejects_changed_dt(tmp_path, protocol):
    changed = copy.deepcopy(protocol)
    changed["protocol"]["dt_ms"] = 1.0
    path = tmp_path / "changed_dt.yaml"
    with path.open("w", encoding="utf-8") as handle:
        module.yaml.safe_dump(changed, handle)
    with pytest.raises(ValueError):
        module.load_protocol(path)


def test_protocol_rejects_changed_instance_total(tmp_path, protocol):
    changed = copy.deepcopy(protocol)
    changed["run_matrix"]["planned_instances"] = 185
    path = tmp_path / "changed_total.yaml"
    with path.open("w", encoding="utf-8") as handle:
        module.yaml.safe_dump(changed, handle)
    with pytest.raises(ValueError):
        module.load_protocol(path)


def test_protocol_rejects_inference_flags(tmp_path, protocol):
    changed = copy.deepcopy(protocol)
    changed["decision"]["p_values"] = True
    path = tmp_path / "changed_decision.yaml"
    with path.open("w", encoding="utf-8") as handle:
        module.yaml.safe_dump(changed, handle)
    with pytest.raises(ValueError):
        module.load_protocol(path)


def test_protocol_rejects_withdrawn_gate_list_change(tmp_path, protocol):
    changed = copy.deepcopy(protocol)
    changed["gates"]["withdrawn"] = ["E11", "E2"]
    path = tmp_path / "changed_gates.yaml"
    with path.open("w", encoding="utf-8") as handle:
        module.yaml.safe_dump(changed, handle)
    with pytest.raises(ValueError):
        module.load_protocol(path)


def test_protocol_rejects_e11_replacement(tmp_path, protocol):
    changed = copy.deepcopy(protocol)
    changed["gates"]["replacement_for_e11"] = "E11_prime"
    path = tmp_path / "changed_replacement.yaml"
    with path.open("w", encoding="utf-8") as handle:
        module.yaml.safe_dump(changed, handle)
    with pytest.raises(ValueError):
        module.load_protocol(path)


def test_measurement_config_forbids_combination_and_cosine(protocol):
    measurement = protocol["measurement"]
    assert measurement["cross_population_combination"] is False
    assert measurement["cosine_on_signed_or_sparse_rate_vectors"] is False
    assert measurement["baseline_subtraction"] is False
    assert measurement["normalization"] == "none"
    assert measurement["units"] == "Hz"


# --------------------------------------------------------------------------
# 2. condition construction
# --------------------------------------------------------------------------


def test_condition_matrix_is_frozen(protocol):
    by_id = module.conditions_by_id(protocol)
    assert len(by_id) == 42
    counts = {group: 0 for group in module.CONDITION_GROUPS}
    for condition in protocol["conditions"]:
        counts[condition["group"]] += 1
    assert counts == module.CONDITION_GROUPS
    assert counts == {
        "core": 4,
        "linear_200": 4,
        "closed_150": 10,
        "constant": 3,
        "no_input": 1,
        "single_transition_200": 6,
        "single_transition_150": 6,
        "crossfade": 8,
    }


def test_core_sequences_are_exact(protocol):
    by_id = module.conditions_by_id(protocol)
    assert by_id["C1"]["sequence"] == ["L"] * 4 + ["C"] * 4 + ["R"] * 4
    assert by_id["C2"]["sequence"] == ["R"] * 4 + ["C"] * 4 + ["L"] * 4
    assert by_id["C3"]["sequence"] == ["L"] * 3 + ["C"] * 3 + ["R"] * 3 + ["L"] * 3
    assert by_id["C4"]["sequence"] == ["L"] * 3 + ["R"] * 3 + ["C"] * 3 + ["L"] * 3


def test_every_sequence_has_twelve_lane_frames(protocol):
    for condition in protocol["conditions"]:
        if condition["mode"] == "none":
            assert condition["sequence"] is None
            continue
        assert len(condition["sequence"]) == 12
        assert set(condition["sequence"]) <= {"L", "C", "R"}


def test_crossfade_replays_the_step_sequence(protocol):
    by_id = module.conditions_by_id(protocol)
    crossfade = [
        condition
        for condition in protocol["conditions"]
        if condition["group"] == "crossfade"
    ]
    assert len(crossfade) == 8
    for condition in crossfade:
        replay = by_id[condition["replay_of"]]
        assert replay["id"] != condition["id"]
        assert replay["sequence"] == condition["sequence"]
        assert replay["mode"] == "step"


def test_single_transition_metadata_matches_sequence(protocol):
    by_id = module.conditions_by_id(protocol)
    for condition in protocol["conditions"]:
        if not condition["group"].startswith("single_transition_"):
            continue
        sequence = condition["sequence"]
        transition = int(condition["transition_ms_absolute"] / 50.0)
        assert sequence[:transition] == [sequence[0]] * transition
        assert sequence[transition:] == [sequence[transition]] * (
            12 - transition
        )
        assert condition["route"] == f"{sequence[0]}->{sequence[transition]}"
        assert module.LANE_LETTERS[sequence[transition]] == condition["new_lane"]


# --------------------------------------------------------------------------
# 3. stimulus timing and frame boundaries
# --------------------------------------------------------------------------


def test_condition_timeline_uses_fifty_millisecond_frames(protocol):
    by_id = module.conditions_by_id(protocol)
    timeline = module.condition_timeline(by_id["C1"], 50.0)
    assert [timestamp for timestamp, _ in timeline] == [
        0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0,
        350.0, 400.0, 450.0, 500.0, 550.0,
    ]
    lanes = [state.player.lane.name.lower() for _, state in timeline]
    assert lanes == ["left"] * 4 + ["center"] * 4 + ["right"] * 4
    assert module.condition_timeline(by_id["N0"], 50.0) is None


def test_absolute_bin_edges_cover_zero_to_six_hundred(protocol):
    edges = module.absolute_bin_edges(protocol)
    assert edges.tolist() == [float(value) for value in range(0, 601, 50)]
    assert len(edges) == 13


def test_bin_indices_are_half_open():
    edges = np.arange(0.0, 601.0, 50.0)
    samples = np.array([0.0, 49.999, 50.0, 99.999, 599.999, 600.0])
    assert module._bin_indices(samples, edges).tolist() == [0, 0, 1, 1, 11, 12]


def test_bin_count_matrix_assigns_boundary_spikes_to_the_next_bin():
    edges = np.array([0.0, 50.0, 100.0, 150.0])
    times = np.array([0.0, 49.999, 50.0, 99.999, 149.999, 150.0])
    indices = np.array([7, 7, 7, 7, 7, 7], dtype=np.int64)
    matrix = module.bin_count_matrix(times, indices, [7], edges)
    assert matrix.tolist() == [[2, 2, 1]]


def test_tail_count_excludes_half_open_final_frame():
    times = np.array([0.0, 599.999, 600.0, 600.4])
    indices = np.array([1, 1, 1, 1], dtype=np.int64)
    assert module.tail_count(times, indices, [1]) == 2


# --------------------------------------------------------------------------
# 4. step scheduler integration
# --------------------------------------------------------------------------


def test_step_scheduler_follows_the_twelve_frames(protocol, scheduler_audits, bundle):
    scheduler = scheduler_audits["C1"]["scheduler"]
    groups = bundle["groups"]
    n_nodes = bundle["mapping"].graph.n_nodes
    assert scheduler.transition_ms == 0.0
    assert scheduler.stimulated_indices.size == 12

    for time_ms, lane in ((0.0, "left"), (199.5, "left"), (200.0, "center"),
                          (399.5, "center"), (400.0, "right"), (599.5, "right")):
        buffer = current_at(scheduler, time_ms, n_nodes)
        active = np.flatnonzero(buffer)
        assert active.tolist() == sorted(int(value) for value in groups[lane])
        assert np.allclose(buffer[groups[lane]], 200.0)
        assert abs(float(buffer.sum()) - 800.0) <= 1e-9


def test_step_scheduler_has_no_anticipatory_activity(protocol, scheduler_audits, bundle):
    scheduler = scheduler_audits["XF_C1"]["scheduler"]
    n_nodes = bundle["mapping"].graph.n_nodes
    right = bundle["groups"]["right"]
    for time_ms in (0.0, 100.0, 199.5, 300.0, 399.5):
        buffer = current_at(scheduler, time_ms, n_nodes)
        assert not np.any(buffer[right])


def test_n0_has_no_schedule(protocol, scheduler_audits):
    assert scheduler_audits["N0"]["scheduler"] is None
    audit = scheduler_audits["N0"]["audit"]
    assert audit["stimulated_set_size"] == 0
    assert audit["total_current_min_pa"] == 0.0
    assert audit["total_current_max_pa"] == 0.0


# --------------------------------------------------------------------------
# 5. crossfade scheduler integration
# --------------------------------------------------------------------------


def test_crossfade_is_linear_and_causal(protocol, scheduler_audits, bundle):
    scheduler = scheduler_audits["XF_C1"]["scheduler"]
    groups = bundle["groups"]
    n_nodes = bundle["mapping"].graph.n_nodes
    assert scheduler.transition_ms == 50.0

    before = current_at(scheduler, 200.0, n_nodes)
    assert np.allclose(before[groups["left"]], 200.0)
    assert np.allclose(before[groups["center"]], 0.0)

    half = current_at(scheduler, 225.0, n_nodes)
    assert np.flatnonzero(half).tolist() == sorted(
        int(value) for value in np.concatenate([groups["left"], groups["center"]])
    )
    assert np.allclose(half[groups["left"]], 100.0)
    assert np.allclose(half[groups["center"]], 100.0)
    assert abs(float(half.sum()) - 800.0) <= 1e-9

    after = current_at(scheduler, 250.0, n_nodes)
    assert np.allclose(after[groups["left"]], 0.0)
    assert np.allclose(after[groups["center"]], 200.0)


def test_crossfade_alpha_half_audit_matches_eight_by_one_hundred(
    protocol, scheduler_audits
):
    audit = scheduler_audits["XF_C1"]["audit"]
    half = audit["alpha_half_check"]
    assert half is not None
    assert half["time_ms"] == 225.0
    assert half["nonzero_neurons"] == 8
    assert half["per_neuron_pa"] == [100.0] * 8
    assert half["total_pa"] == 800.0


def test_step_and_crossfade_schedulers_differ(protocol, scheduler_audits):
    step = scheduler_audits["C1"]["scheduler"]
    crossfade = scheduler_audits["XF_C1"]["scheduler"]
    assert step.describe()["transition_ms"] == 0.0
    assert crossfade.describe()["transition_ms"] == 50.0
    assert module.schedule_signature_hash(step) != module.schedule_signature_hash(
        crossfade
    )


# --------------------------------------------------------------------------
# 6. stimulated neuron set and per-step current counts
# --------------------------------------------------------------------------


def test_stimulated_set_is_exactly_the_twelve_lane_neurons(
    protocol, scheduler_audits, bundle
):
    union = sorted(
        int(value)
        for lane in module.LANE_ORDER
        for value in bundle["groups"][lane]
    )
    for condition in protocol["conditions"]:
        audit = scheduler_audits[condition["id"]]["audit"]
        if condition["mode"] == "none":
            assert audit["stimulated_indices"] == []
            continue
        assert audit["stimulated_set_size"] == 12
        assert audit["stimulated_indices"] == union
        assert audit["outside_nonzero_entries"] == 0
        assert audit["outside_max_abs_pa"] == 0.0


def test_amended_e2_per_step_counts(protocol, scheduler_audits):
    for condition in protocol["conditions"]:
        audit = scheduler_audits[condition["id"]]["audit"]
        observed = set(audit["nonzero_counts_observed"])
        if condition["mode"] == "none":
            assert observed == {0}
        elif condition["mode"] == "crossfade":
            assert observed <= {4, 8}
        else:
            assert observed == {4}
        assert audit["nonzero_counts_ok"]


def test_condition_gates_accept_every_static_condition(
    protocol, scheduler_audits, bundle
):
    for condition in protocol["conditions"]:
        checks = module.condition_gates(
            condition,
            scheduler_audits[condition["id"]]["audit"],
            bundle["groups"],
        )
        assert all(check["passed"] for check in checks.values()), (
            condition["id"],
            checks,
        )


def test_constant_conditions_activate_only_their_lane(
    protocol, scheduler_audits, bundle
):
    for condition_id, lane in (("K_L", "left"), ("K_C", "center"), ("K_R", "right")):
        checks = module.condition_gates(
            protocol_condition(protocol, condition_id),
            scheduler_audits[condition_id]["audit"],
            bundle["groups"],
        )
        assert checks["E4"]["passed"]
        assert checks["E4"]["detail"]["active_indices"] == sorted(
            int(value) for value in bundle["groups"][lane]
        )


def protocol_condition(protocol, condition_id):
    return module.conditions_by_id(protocol)[condition_id]


# --------------------------------------------------------------------------
# 7. total input-current validation
# --------------------------------------------------------------------------


def test_total_current_is_800_pa_for_every_active_condition(
    protocol, scheduler_audits
):
    tolerance = protocol["gates"]["e3_tolerance_pa"]
    assert tolerance == 1e-9
    for condition in protocol["conditions"]:
        audit = scheduler_audits[condition["id"]]["audit"]
        expected = 0.0 if condition["mode"] == "none" else 800.0
        assert audit["expected_total_pa"] == expected
        assert audit["total_current_ok"]
        assert abs(audit["total_current_min_pa"] - expected) <= tolerance
        assert abs(audit["total_current_max_pa"] - expected) <= tolerance
        checks = module.condition_gates(
            condition, audit, {lane: np.array([0]) for lane in module.LANE_ORDER}
        )
        assert checks["E3"]["passed"]


# --------------------------------------------------------------------------
# 8. M6' calculations and units
# --------------------------------------------------------------------------


def test_rates_use_twenty_hertz_per_spike_in_fifty_milliseconds():
    counts = np.array([1], dtype=np.int64)
    assert module.rates_from_counts(counts, 50.0).tolist() == [20.0]


def test_m6_prime_aggregates_bins_then_neurons():
    counts = np.array(
        [[0, 0, 0], [0, 0, 0], [0, 0, 0], [4, 0, 0]], dtype=np.int64
    )
    value = module.m6_prime(counts, 50.0)
    assert value["per_neuron_hz"][3][0] == pytest.approx(80.0)
    assert value["per_bin_hz"] == pytest.approx([20.0, 0.0, 0.0])
    assert value["value_hz"] == pytest.approx(20.0 / 3.0)


def test_m6_prime_is_units_consistent_for_uniform_counts():
    counts = np.ones((4, 3), dtype=np.int64)
    value = module.m6_prime(counts, 50.0)
    assert value["per_bin_hz"] == pytest.approx([20.0, 20.0, 20.0])
    assert value["value_hz"] == pytest.approx(20.0)


def test_measurement_subtraction_is_per_neuron_and_per_bin():
    first = module.m6_prime(np.full((4, 3), 2, dtype=np.int64), 50.0)
    second = module.m6_prime(np.ones((4, 3), dtype=np.int64), 50.0)
    difference = module.subtract_measurement(first, second)
    assert difference["value_hz"] == pytest.approx(20.0)
    assert difference["per_bin_hz"] == pytest.approx([20.0, 20.0, 20.0])
    assert all(
        row == pytest.approx([20.0, 20.0, 20.0])
        for row in difference["per_neuron_hz"]
    )
    assert difference["per_neuron_mean_hz"] == pytest.approx([20.0] * 4)


def _measurement(rows, per_bin=None):
    rows = [list(row) for row in rows]
    width = len(rows[0]) if rows else 0
    return {
        "value_hz": 0.0,
        "per_bin_hz": [0.0] * width if per_bin is None else list(per_bin),
        "per_neuron_hz": rows,
    }


def test_per_neuron_scalar_matches_preregistered_equation():
    first_counts = np.array(
        [[0, 0, 0], [4, 0, 0], [0, 2, 0], [0, 0, 3]], dtype=np.int64
    )
    second_counts = np.array(
        [[1, 0, 0], [0, 1, 0], [0, 0, 1], [3, 0, 0]], dtype=np.int64
    )
    difference = module.subtract_measurement(
        module.m6_prime(first_counts, 50.0),
        module.m6_prime(second_counts, 50.0),
    )
    assert len(difference["per_neuron_mean_hz"]) == 4
    for neuron in range(4):
        expected = sum(
            difference["per_neuron_hz"][neuron]
        ) / 3.0
        assert difference["per_neuron_mean_hz"][neuron] == pytest.approx(
            expected
        )
    assert difference["per_neuron_mean_hz"] == pytest.approx(
        [-20.0 / 3.0, 20.0, 20.0 / 3.0, 0.0]
    )


def test_per_neuron_scalar_averages_three_state_relative_bins():
    counts = np.zeros((4, 3), dtype=np.int64)
    counts[1] = [1, 2, 3]
    difference = module.subtract_measurement(
        module.m6_prime(counts, 50.0),
        module.m6_prime(np.zeros((4, 3), dtype=np.int64), 50.0),
    )
    assert difference["per_neuron_mean_hz"][1] == pytest.approx(40.0)
    assert difference["per_neuron_mean_hz"] == pytest.approx(
        [0.0, 40.0, 0.0, 0.0]
    )


def test_per_neuron_scalar_keeps_c1_minus_c2_direction():
    first = module.m6_prime(np.full((4, 3), 2, dtype=np.int64), 50.0)
    second = module.m6_prime(np.full((4, 3), 1, dtype=np.int64), 50.0)
    forward = module.subtract_measurement(first, second)["per_neuron_mean_hz"]
    reverse = module.subtract_measurement(second, first)["per_neuron_mean_hz"]
    assert forward == pytest.approx([20.0] * 4)
    assert reverse == pytest.approx([-20.0] * 4)


def test_per_neuron_scalar_units_are_hertz():
    counts = np.zeros((4, 3), dtype=np.int64)
    counts[0, 0] = 1
    difference = module.subtract_measurement(
        module.m6_prime(counts, 50.0),
        module.m6_prime(np.zeros((4, 3), dtype=np.int64), 50.0),
    )
    assert difference["per_neuron_mean_hz"][0] == pytest.approx(20.0 / 3.0)
    assert difference["per_neuron_mean_hz"][1:] == pytest.approx([0.0, 0.0, 0.0])


def test_per_neuron_scalar_is_independent_per_neuron():
    first_counts = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 2, 0], [0, 0, 3]], dtype=np.int64
    )
    difference = module.subtract_measurement(
        module.m6_prime(first_counts, 50.0),
        module.m6_prime(np.zeros((4, 3), dtype=np.int64), 50.0),
    )
    assert difference["per_neuron_mean_hz"] == pytest.approx(
        [0.0, 20.0 / 3.0, 40.0 / 3.0, 20.0]
    )
    assert len(set(difference["per_neuron_mean_hz"])) == 4


def test_m6_prime_does_not_gain_a_per_neuron_scalar():
    value = module.m6_prime(np.ones((4, 3), dtype=np.int64), 50.0)
    assert set(value) == {"value_hz", "per_bin_hz", "per_neuron_hz"}
    assert value["value_hz"] == pytest.approx(20.0)


def test_subtract_measurement_rejects_missing_per_neuron_rows():
    valid = _measurement([[0, 0, 0]] * 4)
    broken = {"value_hz": 0.0, "per_bin_hz": [0.0, 0.0, 0.0]}
    with pytest.raises(ValueError, match="per_neuron_hz"):
        module.subtract_measurement(valid, broken)


def test_subtract_measurement_rejects_empty_rows():
    with pytest.raises(ValueError, match="no per-neuron rows"):
        module.subtract_measurement(
            _measurement([[0, 0, 0]] * 4), _measurement([])
        )


def test_subtract_measurement_rejects_ragged_rows():
    broken = _measurement([[0, 0, 0], [0, 0], [0, 0, 0], [0, 0, 0]])
    with pytest.raises(ValueError, match="ragged"):
        module.subtract_measurement(_measurement([[0, 0, 0]] * 4), broken)


def test_subtract_measurement_rejects_bin_count_mismatch():
    broken = {
        "value_hz": 0.0,
        "per_bin_hz": [0.0, 0.0],
        "per_neuron_hz": [[0, 0, 0]] * 4,
    }
    with pytest.raises(ValueError, match="bin counts disagree"):
        module.subtract_measurement(_measurement([[0, 0, 0]] * 4), broken)


def test_subtract_measurement_rejects_neuron_count_mismatch():
    with pytest.raises(ValueError, match="neuron count"):
        module.subtract_measurement(
            _measurement([[0, 0, 0]] * 4), _measurement([[0, 0, 0]] * 3)
        )


def test_subtract_measurement_rejects_bin_width_mismatch_between_inputs():
    wide = _measurement([[0, 0, 0]] * 4)
    narrow = {
        "value_hz": 0.0,
        "per_bin_hz": [0.0, 0.0],
        "per_neuron_hz": [[0, 0]] * 4,
    }
    with pytest.raises(ValueError, match="bin count"):
        module.subtract_measurement(wide, narrow)


def test_analyse_seed_exposes_four_per_neuron_scalars(protocol, bundle):
    runs = _empty_raw_runs(protocol)
    groups = bundle["groups"]
    center = [int(value) for value in groups["center"]]
    add_spikes(runs["C1"], [center[0]] * 3, [200.0, 250.0, 300.0])
    add_spikes(runs["C2"], [center[1]] * 2, [200.0, 210.0])
    analysis = module.analyse_seed(runs, protocol, groups)
    means = analysis["primary"]["per_neuron_mean_hz"]
    assert len(means) == 4
    assert means[0] == pytest.approx(20.0)
    assert means[1] == pytest.approx(-40.0 / 3.0)
    assert means[2] == pytest.approx(0.0)
    assert means[3] == pytest.approx(0.0)
    matrix = analysis["primary"]["per_neuron_hz"]
    assert len(matrix) == 4
    assert all(len(row) == 3 for row in matrix)


def test_rendered_report_shows_four_per_neuron_scalars():
    analysis = {
        "primary": {
            "per_neuron_hz": [[1.0, 2.0, 3.0]] * 4,
            "per_neuron_mean_hz": [2.0, 2.0, 2.0, 2.0],
        }
    }
    lines = module._primary_per_neuron_lines(analysis)
    assert "| Neuron pin | s=0 | s=1 | s=2 | Delta_C(i) Hz |" in lines
    rows = [
        line
        for line in lines
        if line.startswith("| ") and not line.startswith("| Neuron")
        and not line.startswith("|---")
    ]
    assert len(rows) == 4
    assert rows[3] == "| 3 | 1.000000 | 2.000000 | 3.000000 | 2.000000 |"


def test_state_relative_bins_start_at_center_onset():
    times = np.array([149.999, 150.0, 199.999, 200.0, 249.999, 250.0])
    indices = np.zeros(times.size, dtype=np.int64)
    counts = module.state_relative_counts(times, indices, [0], 150.0)
    assert counts.tolist() == [[2, 2, 1]]


def test_measure_condition_records_per_neuron_bin_counts(protocol, bundle):
    raw = _empty_raw_runs(protocol)["C1"]
    neuron = int(bundle["groups"]["center"][0])
    add_spikes(raw, [neuron], [200.0])
    measurement = module.measure_condition(
        raw, protocol_condition(protocol, "C1"), bundle["groups"], protocol
    )
    matrix = measurement["absolute_bins"]["by_lane"]["center"][
        "per_neuron_counts"
    ]
    n_bins = len(measurement["absolute_bins"]["edges_ms"]) - 1
    assert len(matrix) == 4
    assert all(len(row) == n_bins for row in matrix)
    assert matrix[0][4] == 1
    assert sum(sum(row) for row in matrix) == 1


# --------------------------------------------------------------------------
# 9. K_C reference calculation
# --------------------------------------------------------------------------


def test_kc_is_the_constant_center_onset(protocol, scheduler_audits, bundle):
    condition = protocol_condition(protocol, "K_C")
    assert module.center_onset_ms(condition["sequence"]) == 0.0
    assert scheduler_audits["K_C"]["audit"]["active_indices"] == sorted(
        int(value) for value in bundle["groups"]["center"]
    )


def test_kc_auxiliary_uses_center_population_only(protocol, bundle):
    runs = _empty_raw_runs(protocol)
    groups = bundle["groups"]
    for index in range(6):
        add_spikes(runs["K_C"], [int(groups["center"][index % 4])], [10.0])
    for index in range(60):
        add_spikes(
            runs["K_C"], [int(groups["left"][index % 4])], [10.0 + index * 0.1]
        )
    analysis = module.analyse_seed(runs, protocol, groups)
    auxiliary = analysis["auxiliary"]
    assert auxiliary["K_C"]["value_hz"] == pytest.approx(10.0)
    assert auxiliary["C1_minus_K_C"]["value_hz"] == pytest.approx(-10.0)
    assert auxiliary["C2_minus_K_C"]["value_hz"] == pytest.approx(-10.0)
    assert analysis["conditions"]["K_C"]["center_state_relative"]["onset_ms"] == 0.0


# --------------------------------------------------------------------------
# 10. R200 and R150 calculations
# --------------------------------------------------------------------------


def test_reference_membership_matches_predecessor_class(protocol):
    by_id = module.conditions_by_id(protocol)
    for reference, expected in (
        ("r200", {"pred_left": "left", "pred_right": "right", "no_predecessor": None}),
        ("r150", {"pred_left": "left", "pred_right": "right", "no_predecessor": None}),
    ):
        block = protocol["references"][reference]
        for key, predecessor in expected.items():
            for condition_id in block[key]:
                assert (
                    module._sequence_predecessor(by_id[condition_id]["sequence"])
                    == predecessor
                )
    assert len(protocol["references"]["r200"]["all_condition_ids"]) == 6
    assert len(protocol["references"]["r150"]["all_condition_ids"]) == 12
    assert len(protocol["references"]["r150"]["pred_left"]) == 5
    assert len(protocol["references"]["r150"]["pred_right"]) == 2
    assert len(protocol["references"]["r150"]["no_predecessor"]) == 3


def test_r200_values_come_from_the_six_permutations(protocol, bundle):
    runs = _empty_raw_runs(protocol)
    groups = bundle["groups"]
    counts = {
        "C1": 6,
        "C2": 12,
        "R200_CLR": 18,
        "R200_CRL": 24,
        "R200_LRC": 30,
        "R200_RLC": 36,
    }
    by_id = module.conditions_by_id(protocol)
    for condition_id, n_spikes in counts.items():
        onset = module.center_onset_ms(by_id[condition_id]["sequence"])
        for index in range(n_spikes):
            add_spikes(
                runs[condition_id], [int(groups["center"][index % 4])], [onset + 10.0]
            )
    analysis = module.analyse_seed(runs, protocol, groups)
    reference = analysis["references"]["r200"]
    for condition_id, n_spikes in counts.items():
        assert reference["values_hz"][condition_id] == pytest.approx(
            n_spikes / 0.6
        )
    assert reference["pred_left"] == pytest.approx(60.0)
    assert reference["pred_right"] == pytest.approx(50.0)
    assert reference["no_predecessor"] == pytest.approx([30.0, 40.0])
    assert reference["separated"] == "pred_left_above_pred_right"
    assert reference["degenerate"] is False


def test_r150_values_come_from_the_twelve_sequences(protocol, bundle):
    runs = _empty_raw_runs(protocol)
    groups = bundle["groups"]
    block = protocol["references"]["r150"]
    by_id = module.conditions_by_id(protocol)
    counts = {}
    for offset, condition_id in enumerate(block["pred_left"]):
        counts[condition_id] = 24 + offset
    for offset, condition_id in enumerate(block["pred_right"]):
        counts[condition_id] = 6 + offset
    for offset, condition_id in enumerate(block["no_predecessor"]):
        counts[condition_id] = 12 + offset
    for condition_id, n_spikes in counts.items():
        onset = module.center_onset_ms(by_id[condition_id]["sequence"])
        for index in range(n_spikes):
            add_spikes(
                runs[condition_id], [int(groups["center"][index % 4])], [onset + 10.0]
            )
    analysis = module.analyse_seed(runs, protocol, groups)
    reference = analysis["references"]["r150"]
    assert reference["pred_left"] == pytest.approx(
        [counts[condition_id] / 0.6 for condition_id in block["pred_left"]]
    )
    assert reference["pred_right"] == pytest.approx(
        [counts[condition_id] / 0.6 for condition_id in block["pred_right"]]
    )
    assert reference["no_predecessor"] == pytest.approx(
        [counts[condition_id] / 0.6 for condition_id in block["no_predecessor"]]
    )
    assert reference["separated"] == "pred_left_above_pred_right"
    assert reference["degenerate"] is False


def test_separation_helpers_are_descriptive():
    assert module.separated_pair(2.0, 1.0) == "pred_left_above_pred_right"
    assert module.separated_pair(1.0, 2.0) == "pred_right_above_pred_left"
    assert module.separated_pair(1.0, 1.0) is None
    assert module.separated_ranges([2.0, 3.0], [0.0, 1.0]) == (
        "pred_left_above_pred_right"
    )
    assert module.separated_ranges([2.0, 3.0], [3.0, 4.0]) is None
    assert module.focal_pair(2.0, 1.0, 2.5, 0.5, 2.0, "pred_left_above_pred_right")
    assert not module.focal_pair(2.0, 1.0, 1.5, 0.5, 1.0, None)


# --------------------------------------------------------------------------
# 11. seed and metadata handling
# --------------------------------------------------------------------------


def test_mapping_seeds_produce_distinct_populations(graph, base_config):
    seeds = module.EXPECTED["main_seeds"] + [module.EXPECTED["pilot_seed"]]
    signatures = {}
    for seed in seeds:
        mapping, _ = module.build_mapping(graph, base_config, seed)
        signatures[seed] = module.mapping_signature(mapping)
        repeat, _ = module.build_mapping(graph, base_config, seed)
        assert module.mapping_signature(repeat) == signatures[seed]
    assert len(set(signatures.values())) == len(seeds)


def test_pilot_seed_is_excluded_from_main(protocol):
    assert protocol["seeds"]["pilot"] == 20261107
    assert 20261107 not in protocol["seeds"]["main"]
    assert protocol["seeds"]["pilot_excluded_from_main"] is True


def test_campaign_paths_do_not_collide():
    main = module.campaign_paths("main")
    pilot = module.campaign_paths("pilot")
    determinism = module.campaign_paths("determinism")
    assert main["json"].name == "p3_3c5_lane_encoding.json"
    assert pilot["json"].name == "p3_3c5_lane_encoding_pilot.json"
    assert determinism["json"].name == "p3_3c5_lane_encoding_determinism.json"
    assert determinism["spikes"] is None
    assert len({main["json"], pilot["json"], determinism["json"]}) == 3


def test_source_and_protected_hashes_are_recorded(protocol):
    hashes = module.assert_prereg_hashes(protocol)
    assert hashes["preregistration"]["actual"] == module.EXPECTED["prereg_sha256"]
    assert hashes["amendment_record"]["actual"] == module.EXPECTED["amendment_sha256"]
    assert module.sha256(module.PREREG_PATH) == module.EXPECTED["prereg_sha256"]
    sources = module.source_hashes()
    assert sources["experiments/phase_3c/p3_3c5_lane_encoding.py"] is not None
    assert all(value is not None for value in sources.values())
    protected = module.protected_hashes()
    assert all(item["expected"] == item["actual"] for item in protected.values())


def test_git_metadata_shape():
    state = module.git_state()
    assert len(state["head"]) == 40
    assert state["branch"]
    assert isinstance(state["status_porcelain"], list)


# --------------------------------------------------------------------------
# 12. determinism-repeat scheduling
# --------------------------------------------------------------------------


def test_determinism_matrix_is_six_conditions_by_three_seeds(protocol):
    plan = module.plan_campaign(protocol, "determinism")
    assert plan["conditions"] == ["C1", "C2", "C3", "C4", "N0", "K_C"]
    assert plan["seeds"] == protocol["seeds"]["main"]
    assert plan["determinism_repeat_instances"] == 18
    assert plan["executed_instances_in_campaign"] == 18
    assert plan["parent_result_required"].endswith("p3_3c5_lane_encoding.json")
    assert plan["execution_authorised_by_this_call"] is False


def test_determinism_repeats_require_authorisation(protocol):
    with pytest.raises(module.ExecutionNotAuthorised):
        module.determinism_repeats(protocol, 20261104, {}, False)


def test_determinism_campaign_needs_a_parent_result(
    tmp_path, monkeypatch, protocol
):
    monkeypatch.setattr(module, "JSON_PATH", tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        module._run_determinism_campaign(protocol, {}, True, write=False)


# --------------------------------------------------------------------------
# 13. pilot and main separation
# --------------------------------------------------------------------------


def test_campaign_plans_keep_the_frozen_counts(protocol):
    main = module.plan_campaign(protocol, "main")
    pilot = module.plan_campaign(protocol, "pilot")
    assert main["seeds"] == protocol["seeds"]["main"]
    assert main["n_conditions"] == 42
    assert main["distinct_instances"] == 126
    assert main["determinism_repeat_instances"] == 18
    assert main["executed_instances_in_campaign"] == 144
    assert pilot["seeds"] == [protocol["seeds"]["pilot"]]
    assert pilot["n_conditions"] == 42
    assert pilot["distinct_instances"] == 42
    assert pilot["determinism_repeat_instances"] == 0
    assert pilot["executed_instances_in_campaign"] == 42
    assert (
        main["distinct_instances"]
        + main["determinism_repeat_instances"]
        + pilot["distinct_instances"]
        == module.EXPECTED["planned_instances"]
    )


def test_pilot_and_main_do_not_share_a_seed(protocol):
    pilot = module.plan_campaign(protocol, "pilot")
    main = module.plan_campaign(protocol, "main")
    assert set(pilot["seeds"]).isdisjoint(main["seeds"])


def test_pilot_execution_requires_authorisation(protocol):
    with pytest.raises(module.ExecutionNotAuthorised):
        module.run_campaign(
            "pilot", acknowledged=False, existing_tests_passed=True, write=False
        )


# --------------------------------------------------------------------------
# 14. withdrawn E11 is not enforced
# --------------------------------------------------------------------------


def test_e11_is_absent_from_the_gate_set(protocol):
    assert "E11" not in module.APPLICABLE_GATES
    assert module.APPLICABLE_GATES == (
        "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10",
        "E12", "E13", "E14", "E15", "E16",
    )
    assert protocol["gates"]["applicable"] == list(module.APPLICABLE_GATES)
    assert protocol["gates"]["withdrawn"] == ["E11"]
    assert protocol["gates"]["replacement_for_e11"] == "none"


def test_no_e11_replacement_exists_in_source():
    source = (
        module.PROJECT_ROOT
        / "experiments"
        / "phase_3c"
        / "p3_3c5_lane_encoding.py"
    ).read_text(encoding="utf-8")
    assert "E11_prime" not in source
    assert "E11′" not in source


def test_run_gates_emits_no_e11(protocol):
    raw, condition_map, static, measurements = gate_inputs(protocol)
    result = module.run_gates(
        protocol,
        20261104,
        raw,
        condition_map,
        static,
        {},
        {"campaign": "pilot", "existing_tests_passed": True},
        measurements,
    )
    assert "E11" not in result["gates"]
    assert set(result["gates"]) == set(module.APPLICABLE_GATES)


# --------------------------------------------------------------------------
# 15. gates E8, E9, E10, E14, E16 (static and synthetic)
# --------------------------------------------------------------------------


def test_static_gates_cover_groups_reversal_pools_and_hashes(static):
    for gate_id in ("E6", "E7", "E8", "E13", "E15"):
        assert static[gate_id]["passed"], (gate_id, static[gate_id])
    assert static["E6"]["detail"]["lane_group_order"] == ["left", "center", "right"]
    assert static["E7"]["detail"]["disjoint_total_12"] is True
    assert all(
        item["inside"] for item in static["E7"]["detail"]["pools"].values()
    )
    assert static["E8"]["detail"]["C2_reverse_C1"] is True
    assert static["E8"]["detail"]["C4_reverse_C3"] is True
    assert (
        static["E8"]["detail"]["C1_sha256"]
        != static["E8"]["detail"]["C2_sha256"]
    )
    assert static["E8"]["detail"]["C1_multiset"] == static["E8"]["detail"][
        "C2_multiset"
    ]


def test_synthetic_gate_evaluation_passes_and_excludes_e11(protocol):
    raw, condition_map, static, measurements = gate_inputs(protocol)
    result = module.run_gates(
        protocol,
        20261104,
        raw,
        condition_map,
        static,
        {},
        {"campaign": "pilot", "existing_tests_passed": True},
        measurements,
    )
    assert result["passed"], result["failed"]
    assert result["gates"]["E9"]["passed"] is True
    assert result["gates"]["E16"]["passed"] is True
    assert result["gates"]["E10"]["passed"] is True
    assert result["gates"]["E14"]["passed"] is True


def test_e9_detects_a_changed_prefix(protocol):
    raw, condition_map, static, measurements = gate_inputs(protocol)
    add_spikes(raw["C4"], [11], [10.0])
    result = module.run_gates(
        protocol,
        20261104,
        raw,
        condition_map,
        static,
        {},
        {"campaign": "pilot", "existing_tests_passed": True},
        measurements,
    )
    assert result["gates"]["E9"]["passed"] is False


def test_e16_detects_a_changed_prefix(protocol):
    raw, condition_map, static, measurements = gate_inputs(protocol)
    add_spikes(raw["T200_RC"], [11], [399.0])
    result = module.run_gates(
        protocol,
        20261104,
        raw,
        condition_map,
        static,
        {},
        {"campaign": "pilot", "existing_tests_passed": True},
        measurements,
    )
    assert result["gates"]["E16"]["passed"] is False


def test_main_without_determinism_fails_e10(protocol):
    raw, condition_map, static, measurements = gate_inputs(protocol)
    result = module.run_gates(
        protocol,
        20261104,
        raw,
        condition_map,
        static,
        {},
        {"campaign": "main", "existing_tests_passed": True},
        measurements,
    )
    assert result["gates"]["E10"]["passed"] is False
    assert "E10" in result["failed"]


def test_e14_requires_reported_outside_activity(protocol):
    raw, condition_map, static, measurements = gate_inputs(protocol)
    assert module.e14_reported(measurements) is True
    measurements["C1"]["outside"] = {"spikes": 0}
    assert module.e14_reported(measurements) is False


# --------------------------------------------------------------------------
# outcome classification and descriptive-only reporting
# --------------------------------------------------------------------------


def test_outcome_order_is_frozen(protocol):
    assert tuple(protocol["decision"]["outcome_order"]) == module.OUTCOME_ORDER
    assert len(module.OUTCOME_ORDER) == 11


def test_outcome_classifier_selects_the_first_triggered_class(protocol):
    passing = dict(
        primary=1.0,
        dwell=1.0,
        sep200="pred_left_above_pred_right",
        focal200=True,
        dwell_consistency=True,
    )
    analyses = {seed: seed_analysis(**passing) for seed in (1, 2, 3)}

    assert classify(protocol, analyses)["outcome"] == "HISTORY_EFFECT_PRESENT"

    silent = {seed: seed_analysis(**passing, silent=seed != 3) for seed in (1, 2, 3)}
    assert classify(protocol, silent)["outcome"] == "INCONCLUSIVE_SILENT_C"

    invalid = {seed: seed_analysis(**passing) for seed in (1, 2, 3)}
    assert (
        classify(protocol, invalid, failed={1})["outcome"] == "INVALID_EXECUTION"
    )

    degenerate = {
        seed: seed_analysis(**passing, degenerate=seed != 3) for seed in (1, 2, 3)
    }
    assert (
        classify(protocol, degenerate)["outcome"]
        == "INCONCLUSIVE_REFERENCE_DEGENERATE"
    )

    dwell_dependent = {
        seed: seed_analysis(
            primary=1.0,
            dwell=1.0,
            sep200="pred_left_above_pred_right",
            focal200=True,
            dwell_consistency=False,
        )
        for seed in (1, 2, 3)
    }
    assert (
        classify(protocol, dwell_dependent)["outcome"]
        == "HISTORY_EFFECT_DWELL_DEPENDENT"
    )

    negative = {seed: seed_analysis(dwell=1.0) for seed in (1, 2, 3)}
    assert (
        classify(protocol, negative)["outcome"]
        == "NEGATIVE_PRIMARY_DWELL_DEPENDENT"
    )

    transition = {
        seed: seed_analysis(transition=seed != 3) for seed in (1, 2, 3)
    }
    assert classify(protocol, transition)["outcome"] == "TRANSITION_ONSET_ONLY"

    route = {seed: seed_analysis(delta_r=1.0) for seed in (1, 2, 3)}
    assert classify(protocol, route)["outcome"] == "ROUTE_ONLY"

    endpoint = {seed: seed_analysis(endpoint=seed != 3) for seed in (1, 2, 3)}
    assert classify(protocol, endpoint)["outcome"] == "ENDPOINT_EXPLAINED"

    quiet = {seed: seed_analysis() for seed in (1, 2, 3)}
    result = classify(protocol, quiet)
    assert result["outcome"] == "NO_HISTORY_EFFECT"
    assert [item["outcome"] for item in result["trace"]] == list(
        module.OUTCOME_ORDER
    )
    assert [item["order"] for item in result["trace"]] == list(range(1, 12))


def test_replication_helpers_are_two_of_three():
    assert module.replicated_sign([1.0, 1.0, 0.0]) == 1
    assert module.replicated_sign([-1.0, -1.0, 1.0]) == -1
    assert module.replicated_sign([1.0, -1.0, 0.0]) == 0
    assert module.replicated_sign([1.0, 1.0, -1.0], required=2) == 1
    assert (
        module.replicated_direction(
            ["pred_left_above_pred_right", None, "pred_left_above_pred_right"]
        )
        == "pred_left_above_pred_right"
    )
    assert module.replicated_direction(["pred_left_above_pred_right", None, None]) is None


def test_analysis_contains_no_inferential_statistics(protocol, bundle):
    runs = _empty_raw_runs(protocol)
    analysis = module.analyse_seed(runs, protocol, bundle["groups"])

    def keys(payload):
        if isinstance(payload, dict):
            for key, value in payload.items():
                yield key
                yield from keys(value)
        elif isinstance(payload, list):
            for value in payload:
                yield from keys(value)

    serialized_keys = " ".join(str(key) for key in keys(analysis))
    assert "p_value" not in serialized_keys
    assert "confidence" not in serialized_keys
    assert "standard_error" not in serialized_keys
    assert protocol["decision"]["significance_claims"] is False
    assert protocol["decision"]["confidence_intervals"] is False
    assert protocol["decision"]["p_values"] is False
    assert all("Descriptive, not inferential" in item for item in module.LIMITATIONS[:1])


# --------------------------------------------------------------------------
# execution guard
# --------------------------------------------------------------------------


def test_execution_requires_acknowledgement_and_a_known_campaign():
    with pytest.raises(module.ExecutionNotAuthorised):
        module._require_execution_authorisation(False, "main", True)
    with pytest.raises(module.ExecutionNotAuthorised):
        module._require_execution_authorisation(True, "unapproved", True)
    with pytest.raises(module.ExecutionNotAuthorised):
        module._require_execution_authorisation(True, "main", False)


def test_execute_single_requires_acknowledgement(tmp_path):
    with pytest.raises(module.ExecutionNotAuthorised):
        module.run_execute_single(
            tmp_path / "request.json", tmp_path / "response.json", acknowledged=False
        )


def test_cli_execute_is_refused_without_authorisation(protocol):
    with pytest.raises(module.ExecutionNotAuthorised):
        module.main(["--execute", "--campaign", "main"])
    assert not (module.RESULTS_DIR / "p3_3c5_lane_encoding.json").exists()


# --------------------------------------------------------------------------
# simulation-dependent tests: NOT RUN — EXECUTION NOT AUTHORISED
# --------------------------------------------------------------------------


@pytest.mark.skip(
    reason="NOT RUN — EXECUTION NOT AUTHORISED: requires 126 main instances"
)
def test_main_campaign_end_to_end_not_run():
    raise AssertionError("must not execute without authorisation")


@pytest.mark.skip(
    reason="NOT RUN — EXECUTION NOT AUTHORISED: requires 42 pilot instances"
)
def test_pilot_campaign_end_to_end_not_run():
    raise AssertionError("must not execute without authorisation")


@pytest.mark.skip(
    reason="NOT RUN — EXECUTION NOT AUTHORISED: requires 18 determinism repeats"
)
def test_determinism_repeats_end_to_end_not_run():
    raise AssertionError("must not execute without authorisation")
