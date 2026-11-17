"""Live closed-loop bridge between the controlled game and the BANC network.

This module only connects already-implemented pieces. It does not replace the
simulator, the neuron model, the synapse model, the Phase 3 encoders, the
Phase 4 decoder or the Phase 7 environment.

``LiveBancStepper``
    A ``BancSimulator`` subclass that exposes the simulator's documented
    per-step order as an incremental call. ``BancSimulator.run()`` calls
    ``reset()`` before simulating, so it cannot be used once per game update:
    the stepper advances an already-live network and never resets it between
    updates. The neuron population, synapse model and spike recorder are the
    existing objects constructed by ``BancSimulator``.

``LiveSensoryDrive``
    An input schedule (``apply(step, time_ms, current_pa)`` plus
    ``stimulated_indices``) that holds the Phase 3 encoding of the most recent
    ``GameState`` on the Phase 4H.4 feature-to-BANC populations. Activations are
    dimensionless and multiplied by the configured per-feature current in pA,
    matching ``sensory.input_scheduler.SensoryInputScheduler``.

``NeuralClosedLoop``
    Observation -> ``GameState`` -> Phase 3 encoding -> BANC current -> spikes
    -> Phase 4 decoder -> Phase 7 action adapter -> game update. Game and
    neural time are synchronised through the absolute game clock, never through
    wall-clock time.

No plasticity module is imported or invoked, so the synaptic weights cannot
change during an episode. Every decoded state is recorded with the action that
was actually executed and the reason for any fallback.

The feature-to-population assignment is the Phase 4H.4 hypothesis or
convention, not a measured sensory pathway, and a decoder label is not a
biological motor command.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from brain.banc_simulator import BancSimulator
from environment.motor_activity import motor_activity_window
from environment.reward_function import REWARD_COMPONENTS
from motor.populations import ACTION_POPULATIONS
from sensory.game_state import GameState
from sensory.population_encoder import encode_state

NEURAL_SCHEDULE_INTERFACE = (
    "apply(step, time_ms, current_pa) plus stimulated_indices"
)

RECORD_FIELDS = (
    "update",
    "game_time_ms",
    "neural_time_ms",
    "neural_steps",
    "spikes_this_update",
    "total_spikes",
    "features",
    "feature_currents_pa",
    "total_sensory_current_pa",
    "decoder",
    "mapping",
    "executed_action",
    "reward_total",
    "reward_components",
    "reward_event_types",
    "reward_provenance",
    "terminated",
    "truncated",
    "termination_reason",
    "game",
)

PHASE_8_RECORD_FIELDS = (
    *RECORD_FIELDS,
    "motor_activity",
    "readout",
)

LIMITATIONS = [
    "The feature-to-BANC population assignment is a labelled hypothesis or "
    "convention (Phase 4H.4), not a measured sensory pathway.",
    "Distances are normalised game-world units, not metric distances.",
    "The decoder labels LEFT/RIGHT/JUMP are decoder labels, not identified "
    "biological motor commands; UNMAPPED and DUCK execute NO_ACTION.",
    "Rewards are the synthetic task rewards defined by the game rules; they "
    "are not a biological dopamine, octopamine or serotonin measurement.",
    "This is a fixed-weight control demonstration: no learning or plasticity "
    "is performed and Phase 8 owns training.",
]


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _positive(value: Any, name: str) -> float:
    number = _finite(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def encoder_output_size(encoder: Any) -> int:
    """Number of activation values an existing Phase 3 encoder emits."""
    spec = getattr(encoder, "spec", None)
    size = getattr(spec, "output_size", None)
    if size is None:
        size = len(encoder.baseline_response())
    return int(size)


@dataclass(frozen=True)
class ClockSync:
    """Map the absolute game clock onto the neural timestep grid."""

    neural_dt_ms: float
    game_dt_s: float

    def __post_init__(self) -> None:
        _positive(self.neural_dt_ms, "neural_dt_ms")
        _positive(self.game_dt_s, "game_dt_s")

    @property
    def game_dt_ms(self) -> float:
        return float(self.game_dt_s) * 1000.0

    def target_step(self, game_time_s: float) -> int:
        """Neural step index whose time is closest to an absolute game time.

        The absolute game time is used directly, so per-update rounding cannot
        accumulate into drift.
        """
        value = _finite(game_time_s, "game_time_s")
        if value < 0:
            raise ValueError("game_time_s cannot be negative")
        return int(round(value * 1000.0 / self.neural_dt_ms))

    def neural_time_ms(self, step: int) -> float:
        return float(step) * float(self.neural_dt_ms)

    def describe(self) -> dict:
        return {
            "neural_dt_ms": float(self.neural_dt_ms),
            "game_dt_ms": round(self.game_dt_ms, 6),
            "rule": "target_step = round(absolute_game_time_ms / neural_dt_ms)",
            "steps_per_update": round(self.game_dt_ms / self.neural_dt_ms, 6),
            "wall_clock_used": False,
            "drift_policy": (
                "absolute game time; rounding error is bounded at half a "
                "neural step and does not accumulate"
            ),
        }


class LiveBancStepper(BancSimulator):
    """Incrementally advance an already-live ``BancSimulator``.

    The per-step order mirrors ``BancSimulator.run`` exactly: deliver and decay
    synaptic currents, build the input current, apply the input schedule,
    integrate the LIF membrane, record spikes, then route spikes into the delay
    buffer. ``reset`` is called once per episode, never per game update.

    ``step_observer`` is an optional ``callable(step, spikes)`` invoked after
    propagation. It defaults to ``None``, so the fixed-weight pathway runs the
    same code whether or not a subclass observes the step.
    """

    step_observer: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._rng = np.random.default_rng(self.seed)
        self._step_index = 0
        self._transmitted = 0
        self._max_abs_current_pa = 0.0
        self._resets = 0

    def reset(self) -> None:
        super().reset()
        self._rng = np.random.default_rng(self.seed)
        self._step_index = 0
        self._transmitted = 0
        self._max_abs_current_pa = 0.0
        self._resets += 1

    @property
    def step_index(self) -> int:
        return self._step_index

    @property
    def time_ms(self) -> float:
        return self._step_index * self.dt_ms

    @property
    def transmitted_spikes(self) -> int:
        return self._transmitted

    @property
    def resets(self) -> int:
        """Number of times the neural state was cleared this object's life."""
        return self._resets

    def advance_to_step(self, target_step: int) -> int:
        """Advance to an absolute neural step index; return steps run."""
        if isinstance(target_step, bool) or not isinstance(
            target_step, (int, np.integer)
        ):
            raise ValueError("target_step must be an integer")
        target = int(target_step)
        if target < self._step_index:
            raise ValueError(
                f"neural time cannot move backwards: step {self._step_index} "
                f"-> {target}"
            )
        count = target - self._step_index
        for _ in range(count):
            self._advance_one()
        return count

    def _advance_one(self) -> None:
        step = self._step_index
        self.synapses.advance()
        if self.noise_std_pa > 0:
            current = self._rng.normal(
                0.0, self.noise_std_pa, self.n_neurons
            )
        else:
            current = np.zeros(self.n_neurons, dtype=np.float64)
        current += self.background_current_pa
        current += self.synapses.synaptic_current_pa
        if self.stimulation is not None:
            start = int(np.ceil(self.stimulation.start_ms / self.dt_ms))
            end = int(np.ceil(self.stimulation.end_ms / self.dt_ms))
            if start <= step < end:
                current[self.stimulation.indices] += self.stimulation.current_pa
        if self.input_schedule is not None:
            self.input_schedule.apply(step, step * self.dt_ms, current)
        self._max_abs_current_pa = max(
            self._max_abs_current_pa, float(np.abs(current).max())
        )
        spikes = self.neurons.step(current)
        self.recorder.record(step, spikes, self.dt_ms)
        self._transmitted += self.synapses.propagate(spikes)
        if self.step_observer is not None:
            self.step_observer(step, spikes)
        self._step_index = step + 1
        if self._step_index % self.diagnostics_interval_steps == 0:
            self._check_finite()

    def activity_summary(self) -> dict:
        duration = max(self.time_ms, self.dt_ms)
        return self.recorder.summary(duration)

    def weight_fingerprint(self) -> dict:
        """Digest of the synapse weight arrays that must not change."""
        digest = hashlib.sha256()
        for array in (
            self.synapses.edge_exc_weight,
            self.synapses.edge_inh_weight,
        ):
            contiguous = np.ascontiguousarray(array)
            digest.update(str(contiguous.dtype).encode("ascii"))
            digest.update(str(contiguous.shape).encode("ascii"))
            digest.update(contiguous.tobytes())
        return {
            "sha256": digest.hexdigest(),
            "n_edges": int(self.synapses.n_edges),
            "excitatory_edges": int(
                np.count_nonzero(self.synapses.edge_exc_weight)
            ),
            "inhibitory_edges": int(
                np.count_nonzero(self.synapses.edge_inh_weight)
            ),
        }

    def describe(self) -> dict:
        return {
            "kind": "live_banc_stepper",
            "interface": "advance_to_step(target_step)",
            "dt_ms": float(self.dt_ms),
            "seed": int(self.seed),
            "n_neurons": int(self.n_neurons),
            "background_current_pa": float(self.background_current_pa),
            "noise_std_pa": float(self.noise_std_pa),
            "diagnostics_interval_steps": int(self.diagnostics_interval_steps),
            "input_schedule": (
                None
                if self.input_schedule is None
                else type(self.input_schedule).__name__
            ),
            "reset_policy": (
                "once per episode; the network is never restarted between "
                "game updates"
            ),
        }


class LiveSensoryDrive:
    """Hold encoded ``GameState`` activations on mapped BANC populations.

    The drive is a zero-order hold: the encoding of the most recent observation
    is applied on every neural step until the next observation arrives. It adds
    current and never overwrites other input, matching the existing
    ``SensoryInputScheduler`` and ``BancEventDrive`` contract.
    """

    def __init__(
        self,
        mapping: Any,
        encoders: Mapping[str, Any],
        *,
        current_pa: Mapping[str, float] | None = None,
        unmapped_features: Mapping[str, str] | None = None,
        label: str = "live_sensory_drive",
    ) -> None:
        if not encoders:
            raise ValueError("at least one encoder is required")
        if not str(label):
            raise ValueError("label must be a non-empty string")
        self.mapping = mapping
        self.encoders = dict(encoders)
        self.label = str(label)
        self.populations = getattr(mapping, "populations", {})
        missing = [name for name in self.encoders if name not in self.populations]
        if missing:
            raise ValueError(f"mapping is missing features {missing}")

        currents = dict(current_pa or {})
        self.current_pa: dict[str, float] = {}
        for feature in self.encoders:
            value = _finite(currents.get(feature, 0.0), f"current_pa[{feature!r}]")
            if value < 0:
                raise ValueError(f"current_pa[{feature!r}] must be non-negative")
            self.current_pa[feature] = value

        sizes: dict[str, int] = {}
        slices: dict[str, slice] = {}
        indices: list[np.ndarray] = []
        offset = 0
        for feature, encoder in self.encoders.items():
            size = encoder_output_size(encoder)
            mapped = int(mapping.size(feature))
            if size != mapped:
                raise ValueError(
                    f"encoder {feature!r} returns {size} values but the "
                    f"mapping has {mapped} neurons"
                )
            sizes[feature] = size
            slices[feature] = slice(offset, offset + size)
            indices.append(np.asarray(mapping.indices(feature), dtype=np.int64))
            offset += size
        self.sizes = sizes
        self._slices = slices
        self._indices = np.concatenate(indices)
        if np.unique(self._indices).size != self._indices.size:
            raise ValueError("mapped populations overlap; the drive is ambiguous")
        self._stimulated_indices = self._indices.copy()
        self.unmapped_features = dict(unmapped_features or {})

        self._current: np.ndarray | None = None
        self._features: dict[str, Any] | None = None
        self._feature_currents = {feature: 0.0 for feature in self.encoders}
        self._state_time_ms: float | None = None
        self.n_updates = 0

    # -- input-schedule contract ------------------------------------------
    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._stimulated_indices

    def set_state(self, state: GameState) -> dict:
        """Encode one ``GameState`` and hold it until the next call."""
        if not isinstance(state, GameState):
            raise ValueError("state must be a sensory.game_state.GameState")
        features = state.features()
        responses = encode_state(features, self.encoders)
        current = np.zeros(self._indices.size, dtype=np.float64)
        totals: dict[str, float] = {}
        for feature in self.encoders:
            response = np.asarray(responses[feature], dtype=np.float64)
            current[self._slices[feature]] = response * self.current_pa[feature]
            totals[feature] = float(response.sum() * self.current_pa[feature])
        self._current = current
        self._features = dict(features)
        self._feature_currents = totals
        self._state_time_ms = float(state.time_ms)
        self.n_updates += 1
        return {
            "time_ms": self._state_time_ms,
            "feature_currents_pa": dict(totals),
            "total_current_pa": float(sum(totals.values())),
        }

    def apply(self, step: int, time_ms: float, current_pa: np.ndarray) -> None:
        if self._current is None:
            return
        current_pa[self._indices] += self._current

    def reset(self) -> None:
        self._current = None
        self._features = None
        self._feature_currents = {feature: 0.0 for feature in self.encoders}
        self._state_time_ms = None
        self.n_updates = 0

    # -- reporting ---------------------------------------------------------
    @property
    def state_time_ms(self) -> float | None:
        return self._state_time_ms

    def last_features(self) -> dict[str, Any]:
        return {} if self._features is None else dict(self._features)

    def feature_currents(self) -> dict[str, float]:
        return dict(self._feature_currents)

    def signature(self) -> dict:
        return {
            "feature_order": list(self.encoders),
            "indices": self._indices.astype(np.int64),
            "current_pa": np.asarray(
                [self.current_pa[feature] for feature in self.encoders]
            ),
        }

    def signature_sha256(self) -> str:
        signature = self.signature()
        digest = hashlib.sha256()
        digest.update("|".join(signature["feature_order"]).encode("utf-8"))
        digest.update(b"|")
        digest.update(
            np.ascontiguousarray(signature["indices"]).tobytes()
        )
        digest.update(b"|")
        digest.update(
            np.ascontiguousarray(signature["current_pa"]).tobytes()
        )
        return digest.hexdigest()

    def describe(self) -> dict:
        return {
            "kind": "live_sensory_drive",
            "label": self.label,
            "hold": "zero_order_hold",
            "n_features": len(self.encoders),
            "features": list(self.encoders),
            "n_stimulated_neurons": int(self._stimulated_indices.size),
            "mapped_populations": dict(self.sizes),
            "current_pa": {
                feature: float(value) for feature, value in self.current_pa.items()
            },
            "unmapped_features": dict(self.unmapped_features),
            "signature_sha256": self.signature_sha256(),
            "policy": {
                "interface": NEURAL_SCHEDULE_INTERFACE,
                "semantics": (
                    "activation * current_pa is added to the mapped neurons on "
                    "every neural step; the drive never overwrites other input"
                ),
                "update_rule": (
                    "the encoding of the most recent observation is held until "
                    "the next game update updates it"
                ),
                "targets": (
                    "mapped non-motor sensory populations only; the mapping "
                    "excludes the motor and LEFT/RIGHT/JUMP masks"
                ),
            },
            "limitations": LIMITATIONS,
        }


def decode_trailing_window(
    action_decoder: Any,
    recorder: Any,
    end_ms: float,
    window_ms: float,
):
    """Decode the half-open window ``[end - window, end)`` with the existing
    Phase 4 decoder.

    Only the spikes inside the window are handed to the decoder, so the result
    is identical to decoding the full recorder over the same window while
    avoiding a full scan of every spike on every game update.
    """
    end = _finite(end_ms, "end_ms")
    window = _positive(window_ms, "window_ms")
    if int(getattr(action_decoder, "n_neurons", -1)) != int(
        getattr(recorder, "n_neurons", -2)
    ):
        raise ValueError(
            "decoder and recorder neuron counts differ"
        )
    if end <= 0:
        return None
    start = max(0.0, end - window)
    times = np.asarray(recorder.spike_times_ms)
    indices = np.asarray(recorder.spike_neuron_indices)
    lo = int(np.searchsorted(times, start, side="left"))
    hi = int(np.searchsorted(times, end, side="left"))
    return action_decoder.decode_window(times[lo:hi], indices[lo:hi], start, end)


def episode_fingerprint(records, recorder) -> dict:
    """Deterministic digest of the neural activity and the control trace."""
    spikes = hashlib.sha256()
    spikes.update(np.ascontiguousarray(recorder.spike_times_ms).tobytes())
    spikes.update(np.ascontiguousarray(recorder.spike_neuron_indices).tobytes())
    trace = hashlib.sha256()
    payload = [
        [
            record["update"],
            record["neural_time_ms"],
            record["executed_action"],
            record["reward_total"],
            list(record["reward_event_types"]),
        ]
        for record in records
    ]
    trace.update(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return {
        "spike_sha256": spikes.hexdigest(),
        "action_reward_sha256": trace.hexdigest(),
    }


class NeuralClosedLoop:
    """Drive the controlled game from live BANC activity with fixed weights.

    ``decision_source`` is optional. When it is ``None`` the loop uses the
    fixed-threshold ``GameActionDecoder`` exactly as in Phase 7. When it is set
    (Phase 8 condition F / Fβ), the readout receives the per-decision motor
    block and returns the action; the fixed decoder is never called, but its
    population registry may still be passed as ``action_decoder`` for summary
    accounting. ``record_motor_activity`` is off by default so Phase 7 records
    keep their exact field set.

    ``post_update`` is optional. It is called after every game update, after
    the adapter has produced the step reward and the next observation, and
    before the record is appended. Phase 8 conditions B and D pass a hook that
    applies one three-factor weight update to the live plastic stepper; the
    default ``None`` keeps the Phase 7 fixed-weight pathway byte-identical.
    """

    def __init__(
        self,
        adapter: Any,
        stepper: LiveBancStepper,
        drive: LiveSensoryDrive,
        action_decoder: Any | None,
        *,
        clock: ClockSync,
        window_ms: float | None = None,
        max_updates: int | None = None,
        decision_source: Any | None = None,
        record_motor_activity: bool = False,
        sufficiency: Any | None = None,
        post_update: Any | None = None,
    ) -> None:
        if action_decoder is None and decision_source is None:
            raise ValueError("an action decoder or a decision source is required")
        populations = getattr(action_decoder, "populations", None)
        if populations is None:
            populations = getattr(decision_source, "populations", None)
        if populations is None:
            raise ValueError("motor populations are required for accounting")
        if int(getattr(populations, "n_neurons", -1)) != int(stepper.n_neurons):
            raise ValueError(
                "decoder and BANC neuron counts differ"
            )
        if decision_source is not None:
            if not record_motor_activity:
                raise ValueError(
                    "a decision source consumes the motor block, so "
                    "record_motor_activity must be True"
                )
            for name in ("reset", "decide"):
                if not callable(getattr(decision_source, name, None)):
                    raise TypeError(
                        f"decision_source must provide {name}()"
                    )
        if int(drive.stimulated_indices.max()) >= int(stepper.n_neurons):
            raise ValueError("sensory drive targets a neuron outside the graph")
        if abs(float(clock.neural_dt_ms) - float(stepper.dt_ms)) > 1e-12:
            raise ValueError("clock neural step does not match the simulator")
        if window_ms is None:
            window_ms = getattr(getattr(action_decoder, "config", None), "window_ms", None)
            if window_ms is None:
                raise ValueError("window_ms is required")
        if max_updates is not None and (
            isinstance(max_updates, bool)
            or not isinstance(max_updates, int)
            or max_updates < 1
        ):
            raise ValueError("max_updates must be a positive integer or None")
        if post_update is not None and not callable(post_update):
            raise TypeError("post_update must be callable or None")
        self.adapter = adapter
        self.stepper = stepper
        self.drive = drive
        self.action_decoder = action_decoder
        self.populations = populations
        self.clock = clock
        self.window_ms = _positive(window_ms, "window_ms")
        self.max_updates = max_updates
        self.decision_source = decision_source
        self.record_motor_activity = bool(record_motor_activity)
        self.sufficiency = sufficiency
        self.post_update = post_update

    def run(self, *, seed: int, max_updates: int | None = None) -> dict:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        limit = self.max_updates if max_updates is None else max_updates
        if limit is None or isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("max_updates must be a positive integer")

        self.adapter.reset(seed=seed)
        self.stepper.reset()
        self.drive.reset()
        if self.action_decoder is not None:
            self.action_decoder.reset()
        if self.decision_source is not None:
            self.decision_source.reset()
        resets_at_start = self.stepper.resets

        state = self.adapter.game.game_state
        self.drive.set_state(state)
        weights_before = self.stepper.weight_fingerprint()

        records: list[dict] = []
        weight_updates: list[dict] = []
        terminated = truncated = False
        termination_reason: str | None = None
        while not (terminated or truncated) and len(records) < limit:
            update = len(records) + 1
            game_time_before_ms = float(state.time_ms)
            features = self.drive.last_features()
            feature_currents = self.drive.feature_currents()
            total_current = float(sum(feature_currents.values()))

            target = self.clock.target_step(update * self.clock.game_dt_s)
            spikes_before = int(self.stepper.recorder.n_spikes)
            steps = self.stepper.advance_to_step(target)
            neural_time_ms = self.stepper.time_ms

            motor_block = None
            if self.record_motor_activity:
                motor_block = motor_activity_window(
                    self.stepper.recorder,
                    self.populations,
                    neural_time_ms,
                    self.window_ms,
                    min_spikes=int(
                        getattr(self.sufficiency, "min_spikes", 5)
                    ),
                    min_active_neurons=int(
                        getattr(self.sufficiency, "min_active_neurons", 3)
                    ),
                )

            readout_record = None
            if self.decision_source is None:
                output = decode_trailing_window(
                    self.action_decoder,
                    self.stepper.recorder,
                    neural_time_ms,
                    self.window_ms,
                )
                decision = output
            else:
                output = None
                decision, readout_record = self.decision_source.decide(
                    motor_block
                )
            step = self.adapter.step(decision)
            if self.decision_source is not None and hasattr(
                self.decision_source, "record_reward"
            ):
                self.decision_source.record_reward(
                    float(step.step_reward.total)
                )
            state = self.adapter.game.game_state
            self.drive.set_state(state)

            weight_update = None
            if self.post_update is not None:
                weight_update = self.post_update(
                    {
                        "update": update,
                        "neural_time_ms": neural_time_ms,
                        "delta_t_ms": float(steps) * float(self.clock.neural_dt_ms),
                        "reward_total": float(step.step_reward.total),
                        "step_reward": step.step_reward,
                        "terminated": bool(step.terminated),
                        "truncated": bool(step.truncated),
                        "motor_block": motor_block,
                        "decision": decision,
                    }
                )
                if weight_update is not None and not isinstance(
                    weight_update, Mapping
                ):
                    raise TypeError(
                        "post_update must return a mapping or None"
                    )

            record = {
                "update": update,
                "game_time_ms": round(game_time_before_ms, 6),
                "neural_time_ms": round(neural_time_ms, 6),
                "neural_steps": int(steps),
                "spikes_this_update": int(self.stepper.recorder.n_spikes)
                - spikes_before,
                "total_spikes": int(self.stepper.recorder.n_spikes),
                "features": {
                    key: (None if value is None else round(float(value), 6))
                    for key, value in features.items()
                },
                "feature_currents_pa": {
                    key: round(float(value), 6)
                    for key, value in feature_currents.items()
                },
                "total_sensory_current_pa": round(total_current, 6),
                "decoder": None if output is None else output.as_dict(),
                "mapping": step.mapping.as_dict(),
                "executed_action": step.mapping.executed_action,
                "reward_total": round(float(step.step_reward.total), 9),
                "reward_components": {
                    key: round(float(value), 9)
                    for key, value in step.step_reward.components.items()
                },
                "reward_event_types": list(step.step_reward.event_types),
                "reward_provenance": step.step_reward.provenance,
                "terminated": bool(step.terminated),
                "truncated": bool(step.truncated),
                "termination_reason": step.step_reward.termination_reason,
                "game": {
                    "step": int(step.observation["environment"]["step"]),
                    "time_s": round(
                        float(step.observation["environment"]["time"]), 6
                    ),
                    "score": float(step.observation["score"]),
                    "coins_collected": int(step.observation["coins_collected"]),
                    "player_lane": int(step.game_state.player.lane),
                    "player_state": str(step.observation["player"]["state"]),
                },
            }
            if motor_block is not None:
                record["motor_activity"] = motor_block
            if self.decision_source is not None:
                record["readout"] = readout_record
            if weight_update is not None:
                weight_updates.append(dict(weight_update))
            records.append(record)
            terminated = bool(step.terminated)
            truncated = bool(step.truncated)
            if step.step_reward.termination_reason:
                termination_reason = step.step_reward.termination_reason

        weights_after = self.stepper.weight_fingerprint()
        summary = self._summarise(
            records,
            seed=seed,
            terminated=terminated,
            truncated=truncated,
            termination_reason=termination_reason,
            weights_before=weights_before,
            weights_after=weights_after,
            resets_at_start=resets_at_start,
        )
        return {
            "seed": seed,
            "records": records,
            "summary": summary,
            "fingerprint": episode_fingerprint(records, self.stepper.recorder),
            # Control/plasticity attestation is kept beside the dynamics
            # records, never inside them: the A/A′ comparison requires the
            # per-decision records to be identical field for field, and only
            # the control runs a hook (REV4 §3.8.3 P5).
            "weight_updates": weight_updates,
        }

    # ------------------------------------------------------------------
    def _summarise(
        self,
        records: list[dict],
        *,
        seed: int,
        terminated: bool,
        truncated: bool,
        termination_reason: str | None,
        weights_before: dict,
        weights_after: dict,
        resets_at_start: int,
    ) -> dict:
        action_counts: Counter = Counter()
        state_counts: Counter = Counter()
        event_counts: Counter = Counter()
        fallbacks: list[dict] = []
        component_totals = {name: 0.0 for name in REWARD_COMPONENTS}
        total_reward = 0.0
        collisions = 0
        max_score = 0.0
        for record in records:
            action_counts[record["executed_action"]] += 1
            state_counts[
                None if record["decoder"] is None else record["decoder"]["state"]
            ] += 1
            mapping = record["mapping"]
            if not mapping["supported"]:
                fallbacks.append(
                    {
                        "update": record["update"],
                        "requested_state": mapping["requested_state"],
                        "executed_action": mapping["executed_action"],
                        "reason": mapping["reason"],
                    }
                )
            total_reward += record["reward_total"]
            for name, value in record["reward_components"].items():
                component_totals[name] = component_totals.get(name, 0.0) + value
            for event in record["reward_event_types"]:
                event_counts[event] += 1
            if "collision" in record["reward_event_types"]:
                collisions += 1
            max_score = max(max_score, record["game"]["score"])

        duration = max(self.stepper.time_ms, self.stepper.dt_ms)
        counts = self.stepper.recorder.spike_counts()
        stimulated = np.zeros(self.stepper.n_neurons, dtype=bool)
        stimulated[self.drive.stimulated_indices] = True
        motor = np.asarray(self.populations.motor_mask, dtype=bool)
        population_spikes = {
            action: int(counts[self.populations.mask(action)].sum())
            for action in ACTION_POPULATIONS
        }
        neural_steps = int(self.stepper.step_index)
        summary = {
            "seed": seed,
            "updates": len(records),
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "termination_reason": termination_reason,
            "neural_steps": neural_steps,
            "neural_time_ms": round(float(self.stepper.time_ms), 6),
            "game_time_ms": round(len(records) * self.clock.game_dt_ms, 6),
            "neural_resets_during_episode": int(self.stepper.resets)
            - int(resets_at_start),
            "mean_steps_per_update": (
                round(neural_steps / len(records), 6) if records else 0.0
            ),
            "total_spikes": int(self.stepper.recorder.n_spikes),
            "stimulated_spikes": int(counts[stimulated].sum()),
            "non_stimulated_spikes": int(counts[~stimulated].sum()),
            "motor_spikes": int(counts[motor].sum()),
            "motor_population_spikes": population_spikes,
            "active_neurons": int(np.count_nonzero(counts)),
            "stimulated_neurons": int(stimulated.sum()),
            "transmitted_spikes": int(self.stepper.transmitted_spikes),
            "activity": self.stepper.recorder.summary(duration),
            "action_counts": dict(sorted(action_counts.items())),
            "decoder_state_counts": {
                str(key): int(value)
                for key, value in sorted(
                    state_counts.items(), key=lambda item: str(item[0])
                )
            },
            "unmapped_or_invalid": len(fallbacks),
            "fallbacks": fallbacks,
            "total_reward": round(total_reward, 9),
            "reward_component_totals": {
                name: round(value, 9) for name, value in component_totals.items()
            },
            "reward_event_counts": dict(sorted(event_counts.items())),
            "collisions": int(collisions),
            "coins_collected": (
                int(records[-1]["game"]["coins_collected"]) if records else 0
            ),
            "max_score": round(max_score, 6),
            "weights_before": weights_before,
            "weights_after": weights_after,
            "weights_unchanged": (
                weights_before["sha256"] == weights_after["sha256"]
            ),
            "max_sensory_current_pa": round(
                max(
                    (record["total_sensory_current_pa"] for record in records),
                    default=0.0,
                ),
                6,
            ),
            "limitations": LIMITATIONS,
        }
        if self.post_update is not None:
            summary["plasticity"] = self._plasticity_summary()
        return summary

    def _plasticity_summary(self) -> dict:
        reports = tuple(getattr(self.stepper, "update_reports", ()))
        state = getattr(self.stepper, "weight_state", None)
        payload = {
            "pathway": "three_factor",
            "eta": float(getattr(self.stepper, "eta", 0.0)),
            "n_update_reports": len(reports),
            "n_touched_slots": int(sum(item.n_slots for item in reports)),
            "n_updates_applied": int(sum(item.n_updates for item in reports)),
            "sum_abs_applied_pa": round(
                sum(item.sum_abs_applied_pa for item in reports), 9
            ),
            "max_abs_applied_pa": round(
                max((item.max_abs_applied_pa for item in reports), default=0.0),
                9,
            ),
            "clamp_hits": int(sum(item.clamp_hits for item in reports)),
            "update_clip_hits": int(
                sum(item.update_clip_hits for item in reports)
            ),
            "sign_violations": int(
                sum(item.sign_violations for item in reports)
            ),
            "weight_update_calls": int(
                getattr(state, "n_update_calls", 0)
            ),
        }
        if state is not None:
            described = state.describe()
            payload.update(
                {
                    "n_plastic_edges": int(state.n_plastic),
                    "structural_digest": state.structural_digest(),
                    "initial_digest": state.initial_digest(),
                    "delta_digest": state.delta_digest(),
                    "effective_digest": state.effective_digest(),
                    "delta_max_abs_pa": float(described["delta_max_abs_pa"]),
                    "n_changed_edges": int(described["n_changed_edges"]),
                    "saturated_edges": int(described["saturated_edges"]),
                }
            )
        return payload
