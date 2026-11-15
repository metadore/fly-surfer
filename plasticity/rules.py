"""Three-factor synaptic update rule and its declared constraints.

SCIENTIFIC STATUS
    ``delta_w = eta * delta_t * e`` is a computational rule. It is not a
    biological learning law, and a nonzero update is not evidence of learning.

The rule consumes an eligibility value and a reward prediction error. It does
not import the reward provider, the motor decoder or the simulator; the caller
supplies the prediction error. Updates are applied to the learned delta layer
of a :class:`~plasticity.weights.WeightState` and are bounded and sign-clipped
by that state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Mapping

import numpy as np

from .weights import WeightState


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


CADENCES = ("reward_event", "every_step")
NORMALIZATIONS = ("none",)


@dataclass(frozen=True)
class RuleConfig:
    """Declared parameters of the three-factor update."""

    eta: float = 0.01
    update_cadence: str = "reward_event"
    weight_decay_per_ms: float = 0.0
    normalization: str = "none"
    abort_on_sign_flip: bool = True

    def __post_init__(self) -> None:
        eta = _finite(self.eta, "eta")
        if eta < 0:
            raise ValueError("eta must be non-negative")
        object.__setattr__(self, "eta", eta)
        if self.update_cadence not in CADENCES:
            raise ValueError(f"update_cadence must be one of {CADENCES}")
        decay = _finite(self.weight_decay_per_ms, "weight_decay_per_ms")
        if decay < 0:
            raise ValueError("weight_decay_per_ms must be non-negative")
        object.__setattr__(self, "weight_decay_per_ms", decay)
        if self.normalization not in NORMALIZATIONS:
            raise ValueError(
                "normalization is a declared exclusion in Phase 5D; only "
                f"{NORMALIZATIONS} is implemented"
            )
        if not isinstance(self.abort_on_sign_flip, (bool, np.bool_)):
            raise ValueError("abort_on_sign_flip must be a boolean")
        object.__setattr__(self, "abort_on_sign_flip", bool(self.abort_on_sign_flip))

    @classmethod
    def from_config(cls, payload: Mapping) -> "RuleConfig":
        values = {
            field.name: payload[field.name]
            for field in fields(cls)
            if field.name in payload
        }
        return cls(**values)

    def describe(self) -> dict:
        return {
            "eta": self.eta,
            "update_cadence": self.update_cadence,
            "weight_decay_per_ms": self.weight_decay_per_ms,
            "normalization": self.normalization,
            "abort_on_sign_flip": bool(self.abort_on_sign_flip),
            "rule": "delta_w = eta * delta_t * e_ij",
            "normalization_status": (
                "declared exclusion: normalization would couple edges and "
                "change the eta = 0 contract, so it is not implemented"
            ),
        }


@dataclass(frozen=True)
class UpdateReport:
    """One reward-event update, with every counter needed by diagnostics."""

    step: int
    eta: float
    delta_t: float
    n_slots: int
    n_updates: int
    sum_applied_pa: float
    sum_abs_applied_pa: float
    max_abs_applied_pa: float
    mean_eligibility: float
    max_eligibility: float
    clamp_hits: int
    update_clip_hits: int
    sign_violations: int
    decayed_edges: int

    def as_dict(self) -> dict:
        return {
            "step": int(self.step),
            "eta": float(self.eta),
            "delta_t": round(float(self.delta_t), 9),
            "n_slots": int(self.n_slots),
            "n_updates": int(self.n_updates),
            "sum_applied_pa": round(float(self.sum_applied_pa), 12),
            "sum_abs_applied_pa": round(float(self.sum_abs_applied_pa), 12),
            "max_abs_applied_pa": round(float(self.max_abs_applied_pa), 12),
            "mean_eligibility": round(float(self.mean_eligibility), 9),
            "max_eligibility": round(float(self.max_eligibility), 9),
            "clamp_hits": int(self.clamp_hits),
            "update_clip_hits": int(self.update_clip_hits),
            "sign_violations": int(self.sign_violations),
            "decayed_edges": int(self.decayed_edges),
        }


class ThreeFactorRule:
    """Apply ``eta * delta_t * e`` to the learned weight layer."""

    def __init__(self, config: RuleConfig, weight_state: WeightState) -> None:
        if not isinstance(weight_state, WeightState):
            raise ValueError("weight_state must be a WeightState")
        self.config = config
        self.weight_state = weight_state

    @property
    def eta(self) -> float:
        return self.config.eta

    def apply(
        self,
        step: int,
        slots,
        eligibility,
        delta_t: float,
        *,
        dt_ms: float = 0.5,
    ) -> UpdateReport:
        rpe = _finite(delta_t, "delta_t")
        dt = _finite(dt_ms, "dt_ms")
        if dt <= 0:
            raise ValueError("dt_ms must be positive")
        edges = np.asarray(slots, dtype=np.int64).ravel()
        traces = np.asarray(eligibility, dtype=np.float64).ravel()
        if traces.size != edges.size:
            raise ValueError("eligibility must have one entry per slot")
        if not np.all(np.isfinite(traces)):
            raise ValueError("eligibility must be finite")
        if np.any(traces < 0):
            raise ValueError("eligibility must be non-negative")

        mean_eligibility = float(traces.mean()) if traces.size else 0.0
        max_eligibility = float(traces.max()) if traces.size else 0.0

        if self.config.eta == 0.0 or edges.size == 0:
            return UpdateReport(
                step=int(step),
                eta=self.config.eta,
                delta_t=rpe,
                n_slots=int(edges.size),
                n_updates=0,
                sum_applied_pa=0.0,
                sum_abs_applied_pa=0.0,
                max_abs_applied_pa=0.0,
                mean_eligibility=mean_eligibility,
                max_eligibility=max_eligibility,
                clamp_hits=0,
                update_clip_hits=0,
                sign_violations=0,
                decayed_edges=0,
            )

        decayed = 0
        if self.config.weight_decay_per_ms > 0:
            factor = math.exp(-self.config.weight_decay_per_ms * dt)
            decayed = self.weight_state.decay_learned(factor)

        dw = self.config.eta * rpe * traces
        if not np.all(np.isfinite(dw)):
            raise FloatingPointError("the update produced a non-finite delta_w")
        result = self.weight_state.apply_update(edges, dw)
        if result["sign_violations"] and self.config.abort_on_sign_flip:
            raise FloatingPointError("a weight update changed a synaptic sign")
        return UpdateReport(
            step=int(step),
            eta=self.config.eta,
            delta_t=rpe,
            n_slots=int(result["n_slots"]),
            n_updates=int(result["n_updates"]),
            sum_applied_pa=float(result["sum_applied_pa"]),
            sum_abs_applied_pa=float(result["sum_abs_applied_pa"]),
            max_abs_applied_pa=float(result["max_abs_applied_pa"]),
            mean_eligibility=mean_eligibility,
            max_eligibility=max_eligibility,
            clamp_hits=int(result["clamp_hits"]),
            update_clip_hits=int(result["update_clip_hits"]),
            sign_violations=int(result["sign_violations"]),
            decayed_edges=int(decayed),
        )

    def describe(self) -> dict:
        return self.config.describe()
