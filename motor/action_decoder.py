"""Structured game-action interface over the deterministic motor decoder.

The interface does not decide which neurons mean which action. It consumes the
population definitions in :mod:`motor.populations` and the decision logic in
:mod:`motor.motor_decoder` unchanged:

``LEFT``
    maps to the Phase 4F LEFT population (left leg-effector motor neurons);
``RIGHT``
    maps to the Phase 4F RIGHT population;
``JUMP``
    maps to the Phase 4F JUMP population (tergotrochanter extensor candidates,
    not a jump command);
``ROLL``
    has no published BANC annotation in this export and therefore returns the
    explicit ``UNMAPPED`` state instead of a fabricated score;
``NO_ACTION``
    is returned when the decoder finds insufficient evidence.

Every output carries the activation scores, the primary and simultaneous
channels, the population evidence and the unresolved channels. There is no
dependency on a game engine: the interface only returns structured records.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

import numpy as np

from motor.motor_decoder import ActionDecision, DecoderConfig, MotorDecoder
from motor.populations import (
    ACTION_POPULATIONS,
    UNSUPPORTED_ACTIONS,
    MotorPopulations,
)

NO_ACTION = "NO_ACTION"
UNMAPPED = "UNMAPPED"
GAME_ACTION_CHANNELS = (*ACTION_POPULATIONS, "ROLL", NO_ACTION)

# Each supported channel uses the population with the same name. The mapping is
# the annotation-derived population itself, not an assignment of individual
# neurons to actions.
CHANNEL_POPULATION = {action: action for action in ACTION_POPULATIONS}

_UNSUPPORTED_CHANNELS = {
    name: UNSUPPORTED_ACTIONS[name] for name in ("ROLL", "DUCK")
}


@dataclass(frozen=True)
class MotorOutput:
    """One game-action record for one time window."""

    window_start_ms: float
    window_end_ms: float
    state: str
    action: str | None
    supported: bool
    confidence: float | None
    activation_scores: Mapping[str, float]
    raw_activation_scores: Mapping[str, float]
    active_channels: tuple[str, ...]
    simultaneous: bool
    unresolved_channels: Mapping[str, str]
    reason: str
    evidence: Mapping[str, dict]
    requested_channel: str | None = None

    @property
    def neutral(self) -> bool:
        return self.state == NO_ACTION

    @property
    def unmapped(self) -> bool:
        return self.state == UNMAPPED

    def as_dict(self) -> dict:
        return {
            "window_start_ms": round(float(self.window_start_ms), 4),
            "window_end_ms": round(float(self.window_end_ms), 4),
            "state": self.state,
            "action": self.action,
            "supported": bool(self.supported),
            "neutral": self.neutral,
            "unmapped": self.unmapped,
            "confidence": (
                None
                if self.confidence is None
                else round(float(self.confidence), 6)
            ),
            "activation_scores": {
                key: round(float(value), 6)
                for key, value in self.activation_scores.items()
            },
            "raw_activation_scores": {
                key: round(float(value), 6)
                for key, value in self.raw_activation_scores.items()
            },
            "active_channels": list(self.active_channels),
            "simultaneous": bool(self.simultaneous),
            "unresolved_channels": dict(self.unresolved_channels),
            "reason": self.reason,
            "evidence": {
                key: dict(value) for key, value in self.evidence.items()
            },
            "requested_channel": self.requested_channel,
        }


class GameActionDecoder:
    """Convert motor-population decisions into game-action records."""

    def __init__(
        self,
        populations: MotorPopulations,
        config: DecoderConfig | None = None,
        *,
        confidence_threshold: float = 0.0,
    ) -> None:
        value = float(confidence_threshold)
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("confidence_threshold must be in [0, 1]")
        self.populations = populations
        self.config = config or DecoderConfig()
        self.confidence_threshold = value
        self.decoder = MotorDecoder(populations, self.config)

    @property
    def n_neurons(self) -> int:
        return self.decoder.n_neurons

    def reset(self) -> None:
        self.decoder.reset()

    def describe(self) -> dict:
        sizes = self.populations.sizes
        return {
            "interface": "game_action_v1",
            "states": [*ACTION_POPULATIONS, *_UNSUPPORTED_CHANNELS, NO_ACTION, UNMAPPED],
            "supported_channels": {
                action: {
                    "population": CHANNEL_POPULATION[action],
                    "size": int(sizes[action]),
                    "mapping_basis": (
                        "population members are defined by published BANC "
                        "effector annotations; no individual neuron is assigned "
                        "to an action by hand"
                    ),
                }
                for action in ACTION_POPULATIONS
            },
            "unsupported_channels": dict(_UNSUPPORTED_CHANNELS),
            "neutral_state": NO_ACTION,
            "unmapped_state": UNMAPPED,
            "confidence": (
                "active fraction of the primary population inside the window"
            ),
            "confidence_threshold": float(self.confidence_threshold),
            "decoder": self.decoder.describe(),
        }

    # ------------------------------------------------------------------
    # decoding
    # ------------------------------------------------------------------

    def _convert(self, decision: ActionDecision) -> MotorOutput:
        scores = {
            action: float(decision.scores[action]) for action in ACTION_POPULATIONS
        }
        raw = {
            action: float(decision.raw_scores[action])
            for action in ACTION_POPULATIONS
        }
        evidence = {
            action: decision.evidence[action].as_dict()
            for action in ACTION_POPULATIONS
        }
        primary = decision.primary_action
        if primary is None:
            state = NO_ACTION
            action = None
            supported = True
            confidence = 0.0
            reason = decision.reason
        elif primary not in ACTION_POPULATIONS:
            state = UNMAPPED
            action = primary
            supported = False
            confidence = None
            reason = f"no annotated population maps to {primary}"
        else:
            confidence = scores[primary]
            if confidence < self.confidence_threshold:
                state = NO_ACTION
                action = None
                supported = True
                reason = "confidence_below_threshold"
            else:
                state = primary
                action = primary
                supported = True
                reason = decision.reason

        active = tuple(
            channel
            for channel in decision.active_actions
            if channel in ACTION_POPULATIONS
        )
        return MotorOutput(
            window_start_ms=float(decision.window_start_ms),
            window_end_ms=float(decision.window_end_ms),
            state=state,
            action=action,
            supported=supported,
            confidence=confidence,
            activation_scores=scores,
            raw_activation_scores=raw,
            active_channels=active,
            simultaneous=len(active) > 1,
            unresolved_channels=dict(_UNSUPPORTED_CHANNELS),
            reason=reason,
            evidence=evidence,
        )

    def decode_window(
        self,
        spike_times_ms: np.ndarray,
        spike_neuron_indices: np.ndarray,
        start_ms: float,
        end_ms: float,
    ) -> MotorOutput:
        decision = self.decoder.decode_window(
            spike_times_ms, spike_neuron_indices, start_ms, end_ms
        )
        return self._convert(decision)

    def decode_series(
        self,
        spike_times_ms: np.ndarray,
        spike_neuron_indices: np.ndarray,
        start_ms: float,
        end_ms: float,
        *,
        include_partial: bool = True,
    ) -> list[MotorOutput]:
        decisions = self.decoder.decode_series(
            spike_times_ms,
            spike_neuron_indices,
            start_ms,
            end_ms,
            include_partial=include_partial,
        )
        return [self._convert(decision) for decision in decisions]

    def decode_recorder(
        self,
        recorder,
        start_ms: float,
        end_ms: float,
        *,
        include_partial: bool = True,
    ) -> list[MotorOutput]:
        decisions = self.decoder.decode_recorder(
            recorder, start_ms, end_ms, include_partial=include_partial
        )
        return [self._convert(decision) for decision in decisions]

    def decode_requested(
        self,
        channel: str,
        spike_times_ms: np.ndarray,
        spike_neuron_indices: np.ndarray,
        start_ms: float,
        end_ms: float,
    ) -> MotorOutput:
        """Decode a window and report the requested channel's support.

        A channel without an annotated population (currently ``ROLL``) returns
        ``UNMAPPED`` with the decoder evidence attached. Other channels return
        the ordinary window output and record which channel was requested.
        """
        name = str(channel).strip().upper()
        expected = tuple(dict.fromkeys((*GAME_ACTION_CHANNELS, *_UNSUPPORTED_CHANNELS)))
        if name not in expected:
            raise ValueError(
                f"unknown channel {channel!r}; expected one of {expected}"
            )
        output = self.decode_window(
            spike_times_ms, spike_neuron_indices, start_ms, end_ms
        )
        if name in _UNSUPPORTED_CHANNELS:
            return replace(
                output,
                state=UNMAPPED,
                action=name,
                supported=False,
                confidence=None,
                active_channels=(),
                simultaneous=False,
                reason=_UNSUPPORTED_CHANNELS[name],
                requested_channel=name,
            )
        return replace(output, requested_channel=name)
