"""Phase 5C: sparse edge-indexed eligibility traces and the delay line."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from plasticity.traces import (
    EligibilityStore,
    SparseDelayLine,
    coincident_edges,
    load_trace_config,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "plasticity.yaml"


def store(n: int = 8, **kwargs) -> EligibilityStore:
    options = {"tau_e_ms": 20.0, "dt_ms": 0.5}
    options.update(kwargs)
    return EligibilityStore(n, **options)


# -- construction -----------------------------------------------------------


@pytest.mark.parametrize("n", [0, -1, 1.5, True])
def test_store_rejects_invalid_trace_count(n):
    with pytest.raises(ValueError):
        store(n)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tau_e_ms": 0.0},
        {"tau_e_ms": -5.0},
        {"tau_e_ms": float("nan")},
        {"dt_ms": 0.0},
        {"dt_ms": -0.5},
        {"prune_threshold": -1e-3},
        {"dtype": np.int32},
    ],
)
def test_store_rejects_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        store(4, **kwargs)


def test_decay_per_step_matches_the_closed_form():
    instance = store(10)
    assert instance.decay_per_step == pytest.approx(math.exp(-0.5 / 20.0), rel=1e-15)
    assert instance.clock == 0
    assert instance.n_touched == 0


def test_initial_store_is_empty_and_zero():
    instance = store(16)
    assert instance.value(0) == 0.0
    assert instance.value(np.arange(16)).tolist() == [0.0] * 16
    report = instance.sparsity_report()
    assert report["n_touched"] == 0
    assert report["nonzero_fraction"] == 0.0
    assert report["storage"] == "lazy edge-indexed float arrays"


# -- accumulation and decay -------------------------------------------------


def test_accumulate_marks_only_named_edges():
    instance = store(10)
    assert instance.accumulate([3, 5]) == 2
    assert instance.value(3) == pytest.approx(1.0)
    assert instance.value(5) == pytest.approx(1.0)
    assert instance.value(4) == 0.0
    assert instance.active_edges.tolist() == [3, 5]


def test_accumulation_is_additive_with_lazy_decay():
    instance = store(4)
    instance.accumulate([1])
    instance.advance(3)
    instance.accumulate([1])
    expected = instance.decay_per_step**3 + 1.0
    assert instance.value(1) == pytest.approx(expected, rel=1e-6)


def test_closed_form_decay_over_many_steps():
    instance = store(4)
    instance.accumulate([2])
    instance.advance(10)
    assert instance.value(2) == pytest.approx(instance.decay_per_step**10, rel=1e-6)
    assert instance.value(2, step=instance.clock + 5) == pytest.approx(
        instance.decay_per_step**15, rel=1e-6
    )


def test_value_in_the_past_is_rejected():
    instance = store(4)
    instance.accumulate([1])
    instance.advance(2)
    with pytest.raises(ValueError):
        instance.value(1, step=instance.clock - 1)


def test_decay_requires_a_whole_number_of_steps():
    instance = store(4)
    instance.decay(1.5)
    assert instance.clock == 3
    instance.decay(0.0)
    assert instance.clock == 3
    with pytest.raises(ValueError):
        instance.decay(0.3)
    with pytest.raises(ValueError):
        instance.decay(-0.5)


def test_advance_rejects_negative_and_non_integer_steps():
    instance = store(4)
    with pytest.raises(ValueError):
        instance.advance(-1)
    with pytest.raises(ValueError):
        instance.advance(1.5)  # type: ignore[arg-type]


def test_reset_clears_values_and_clock():
    instance = store(4)
    instance.accumulate([0, 2])
    instance.advance(7)
    instance.reset()
    assert instance.clock == 0
    assert instance.n_touched == 0
    assert instance.value(0) == 0.0
    assert instance.value(2) == 0.0


def test_duplicate_and_out_of_range_edges_are_rejected():
    instance = store(6)
    with pytest.raises(ValueError):
        instance.accumulate([1, 1])
    with pytest.raises(ValueError):
        instance.accumulate([6])
    with pytest.raises(ValueError):
        instance.accumulate([-1])


def test_increment_can_be_an_array_and_must_match_edges():
    instance = store(6)
    instance.accumulate([1, 2], increment=[0.5, 2.0])
    assert instance.value(1) == pytest.approx(0.5)
    assert instance.value(2) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        instance.accumulate([1, 2], increment=[1.0])


@pytest.mark.parametrize("increment", [float("nan"), float("inf"), -1.0])
def test_increment_must_be_finite_and_non_negative(increment):
    instance = store(4)
    with pytest.raises(ValueError):
        instance.accumulate([1], increment=increment)


def test_trace_overflow_is_rejected_and_previous_value_kept():
    instance = store(2)
    for _ in range(3):
        instance.accumulate([0], increment=1.0e38)
    with pytest.raises(FloatingPointError):
        instance.accumulate([0], increment=1.0e38)
    assert math.isfinite(instance.value(0))


def test_prune_drops_decayed_entries_below_the_threshold():
    instance = store(4)
    instance.accumulate([0, 1])
    instance.advance(400)  # lambda**400 ~ 4e-5 < 1e-4
    assert instance.prune() == 2
    assert instance.n_touched == 0
    assert instance.value(0) == 0.0


def test_prune_keeps_values_above_the_threshold():
    instance = store(4)
    instance.accumulate([0])
    assert instance.prune() == 0
    assert instance.value(0) == pytest.approx(1.0)


def test_prune_threshold_is_inclusive_and_keeps_larger_values():
    instance = store(4, prune_threshold=0.5)
    instance.accumulate([0], increment=0.6)
    assert instance.prune() == 0
    instance.accumulate([1], increment=0.4)
    assert instance.prune() == 1
    assert instance.active_edges.tolist() == [0]


def test_lazy_decay_matches_a_manual_simulation():
    rng = np.random.default_rng(11)
    edge_count = 12
    instance = store(edge_count)
    manual: dict[int, tuple[float, int]] = {}
    lam = instance.decay_per_step
    clock = 0
    for iteration in range(40):
        chosen = np.unique(rng.integers(0, edge_count, size=3))
        instance.accumulate(chosen)
        for edge in chosen:
            previous, stamp = manual.get(int(edge), (0.0, clock))
            manual[int(edge)] = (previous * lam ** (clock - stamp) + 1.0, clock)
        advance = 2 if iteration % 7 == 0 else 0
        instance.advance(advance)
        clock += advance
    assert instance.clock == clock
    for edge, (value, stamp) in manual.items():
        expected = value * lam ** (instance.clock - stamp)
        assert instance.value(edge) == pytest.approx(expected, rel=2e-6)


# -- coincidence ------------------------------------------------------------


def test_pre_only_activity_has_no_coincidence():
    active = np.array([0, 2, 4])
    destinations = np.array([0, 1, 1, 2, 3, 4])
    post = np.zeros(5, dtype=bool)
    assert coincident_edges(active, post, destinations).tolist() == []


def test_post_only_activity_has_no_coincidence():
    destinations = np.array([0, 1, 1, 2, 3, 4])
    post = np.ones(5, dtype=bool)
    assert coincident_edges(np.empty(0, dtype=int), post, destinations).size == 0


def test_coincident_activity_selects_matching_edges():
    active = np.array([0, 1, 2, 3])
    destinations = np.array([0, 1, 2, 3])
    post = np.array([False, True, False, True])
    assert coincident_edges(active, post, destinations).tolist() == [1, 3]


def test_coincidence_validates_index_tables():
    with pytest.raises(ValueError):
        coincident_edges([5], np.ones(3, dtype=bool), np.array([0, 1, 2]))
    with pytest.raises(ValueError):
        coincident_edges([0], np.ones(2, dtype=bool), np.array([0, 4]))


# -- delay line -------------------------------------------------------------


def test_zero_delay_line_returns_edges_in_the_same_step():
    line = SparseDelayLine(0)
    line.push(0, [3, 4])
    assert line.pop_ready(0).tolist() == [3, 4]
    assert line.pop_ready(0).size == 0


def test_two_step_delay_line_delivers_after_two_steps():
    line = SparseDelayLine(2)
    line.push(0, [1, 2])
    assert line.pop_ready(0).size == 0
    assert line.pop_ready(1).size == 0
    assert line.pop_ready(2).tolist() == [1, 2]
    assert line.pending_packets == 0


def test_delay_line_raises_when_a_delivery_step_is_missed():
    line = SparseDelayLine(2)
    line.push(0, [1])
    with pytest.raises(ValueError):
        line.pop_ready(3)


def test_delay_line_requires_non_decreasing_steps():
    line = SparseDelayLine(1)
    line.push(2, [1])
    with pytest.raises(ValueError):
        line.push(1, [2])
    with pytest.raises(ValueError):
        line.push(3, [-1])


def test_delay_line_tracks_pending_memory_and_resets():
    line = SparseDelayLine(3)
    line.push(0, [1, 2, 3])
    line.push(1, np.empty(0, dtype=int))
    assert line.pending_packets == 1
    assert line.pending_edges == 3
    assert line.memory_bytes == 3 * np.dtype(np.int64).itemsize
    described = line.describe()
    assert described["delay_steps"] == 3
    assert described["edges_pushed"] == 3
    line.reset()
    assert line.pending_packets == 0
    assert line.pop_ready(10).size == 0


def test_delay_matched_trace_pairs_presynaptic_and_postsynaptic_spikes():
    # Two-neuron hand case: pre neuron 0, post neuron 1, one edge 0 -> 1.
    line = SparseDelayLine(2)
    destinations = np.array([1])
    line.push(0, [0])  # presynaptic spike at step 0
    post_step_2 = np.array([False, True])
    store_instance = store(1)
    assert coincident_edges(line.pop_ready(0), post_step_2, destinations).size == 0
    store_instance.advance(1)
    assert coincident_edges(line.pop_ready(1), post_step_2, destinations).size == 0
    store_instance.advance(1)
    matched = coincident_edges(line.pop_ready(2), post_step_2, destinations)
    assert matched.tolist() == [0]
    store_instance.accumulate(matched)
    assert store_instance.value(0) == pytest.approx(1.0)
    store_instance.advance(5)
    assert store_instance.value(0) == pytest.approx(
        store_instance.decay_per_step**5, rel=1e-6
    )


# -- storage ----------------------------------------------------------------


def test_memory_is_linear_in_edges():
    n = 200_000
    instance = store(n)
    expected = EligibilityStore.capacity_bytes(n)
    assert expected == n * (np.dtype(np.float32).itemsize + 4)
    assert instance.memory_bytes == expected
    assert instance.memory_bytes < 2 * 1024 * 1024
    assert all(array.ndim == 1 for array in (instance._value, instance._stamp, instance._active))


def test_digest_is_deterministic_and_content_sensitive():
    first = store(6)
    second = store(6)
    first.accumulate([1, 4])
    second.accumulate([1, 4])
    assert first.digest() == second.digest()
    second.accumulate([2])
    assert first.digest() != second.digest()


def test_digest_sees_decay():
    instance = store(4)
    instance.accumulate([0])
    before = instance.digest()
    instance.advance(1)
    assert instance.digest() != before


# -- configuration ----------------------------------------------------------


def test_config_loads_the_declared_trace_section():
    config = load_trace_config(CONFIG_PATH)
    assert config.tau_e_ms == pytest.approx(20.0)
    assert config.dt_ms == pytest.approx(0.5)
    assert config.prune_threshold == pytest.approx(1e-4)
    assert config.prune_interval_steps == 50
    assert config.coincidence == "delay_matched"
    assert config.dtype == "float32"
    described = config.describe()
    assert described["decay_per_step"] == pytest.approx(math.exp(-0.025), rel=1e-12)
    benchmark = config.benchmark
    assert 683100 in benchmark["sizes"] and 1535710 in benchmark["sizes"]
    assert benchmark["n_steps"] == 600
    assert config.banc["enabled"] is True


def test_config_builds_a_store_with_declared_parameters():
    config = load_trace_config(CONFIG_PATH)
    instance = config.build(1000)
    assert instance.n_traces == 1000
    assert instance.tau_e_ms == pytest.approx(20.0)
    assert instance.prune_threshold == pytest.approx(1e-4)


def _write_config(tmp_path: Path, traces: dict) -> Path:
    path = tmp_path / "plasticity.yaml"
    path.write_text(yaml.safe_dump({"traces": traces}), encoding="utf-8")
    return path


def test_config_rejects_unknown_coincidence(tmp_path):
    with pytest.raises(ValueError):
        load_trace_config(
            _write_config(
                tmp_path,
                {"tau_e_ms": 10.0, "dt_ms": 0.5, "coincidence": "mystery"},
            )
        )


def test_config_rejects_bad_prune_interval_and_dtype(tmp_path):
    with pytest.raises(ValueError):
        load_trace_config(
            _write_config(
                tmp_path,
                {"tau_e_ms": 10.0, "dt_ms": 0.5, "prune_interval_steps": 0},
            )
        )
    with pytest.raises(ValueError):
        load_trace_config(
            _write_config(
                tmp_path,
                {"tau_e_ms": 10.0, "dt_ms": 0.5, "dtype": "int32"},
            )
        )


def test_config_requires_the_traces_section(tmp_path):
    path = tmp_path / "plasticity.yaml"
    path.write_text(yaml.safe_dump({"reward": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_trace_config(path)
