"""Per-update plasticity hook for conditions B and D.

SCIENTIFIC STATUS
    The hook applies the declared three-factor rule ``delta_w = eta * M(t) * e``
    exactly once per game update. It adds no reward model: the modulation input
    is the Phase 5 ``ModulationRewardProvider`` fed by the deliveries the
    adapter's own ``GameRewardFunction`` already recorded (REV4 §3.4 row 8,
    §9 table row "Reward handling"). No reward value is recomputed, delayed or
    reshaped here.

    A nonzero applied update is a model event, not evidence of learning. An
    ``eta = 0`` hook still executes the rule and reports
    ``mode = "rule_executed_zero_delta"``; it never takes a shortcut that
    would hide an arithmetic divergence from the fixed pathway.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from plasticity.modulation import (
    ModulationConfig,
    ModulationRewardProvider,
    RewardDelivery,
    RewardModulation,
    RewardStream,
)

from .base import ConditionError, is_plastic_stepper

PLASTICITY_MODES = ("rule_executed_zero_delta", "short_circuited")


class AppendedRewardStream(RewardStream):
    """A ``RewardStream`` that grows while an episode is live.

    Deliveries must arrive in non-decreasing time order, which the adapter
    guarantees because game time advances monotonically.
    """

    def __init__(self, *, provenance: str = "") -> None:
        super().__init__((), provenance=provenance)
        self._last_time = -math.inf

    def append(self, delivery: RewardDelivery) -> None:
        if not isinstance(delivery, RewardDelivery):
            raise TypeError("only a RewardDelivery can be appended")
        if delivery.time_ms < self._last_time:
            raise ConditionError(
                "reward deliveries must be time ordered: "
                f"{delivery.time_ms} after {self._last_time}"
            )
        self.deliveries = (*self.deliveries, delivery)
        self._last_time = float(delivery.time_ms)


class PlasticityUpdateHook:
    """Callable ``post_update`` hook: one reward-event update per game step.

    Reward deliveries are timestamped on the game clock (``k * game_dt_ms``)
    while the loop reports neural time. ``ClockSync.target_step`` picks the
    nearest neural grid point, so the two timestamps differ by at most half a
    neural step (REV4 §9 item 20: "residual rounding error is bounded at half
    a neural step and does not accumulate"). The hook therefore accepts a
    delivery within ``max_delivery_lag_ms`` of the consuming step and evaluates
    the modulation at the delivery time, so the reward is credited to its own
    update rather than silently deferred to the next one.
    """

    def __init__(
        self,
        stepper: Any,
        *,
        modulation_config: ModulationConfig | None = None,
        provenance: str = "",
        max_delivery_lag_ms: float | None = None,
    ) -> None:
        if not is_plastic_stepper(stepper):
            raise ConditionError(
                "the plasticity hook needs a stepper with engine, weight_state "
                "and learn()"
            )
        self.stepper = stepper
        self.stream = AppendedRewardStream(
            provenance=provenance
            or "adapter GameRewardFunction deliveries; values not recomputed"
        )
        self.modulation = RewardModulation(modulation_config)
        self.provider = ModulationRewardProvider(self.stream, self.modulation)
        self.neural_dt_ms = float(getattr(stepper, "dt_ms", 0.0))
        if not math.isfinite(self.neural_dt_ms) or self.neural_dt_ms <= 0:
            raise ConditionError(
                "the plasticity hook needs the stepper's positive dt_ms to "
                "bound game/neural clock rounding"
            )
        if max_delivery_lag_ms is None:
            lag = 0.5 * self.neural_dt_ms
        else:
            lag = float(max_delivery_lag_ms)
        if not math.isfinite(lag) or lag < 0:
            raise ValueError("max_delivery_lag_ms must be finite and non-negative")
        if lag > self.neural_dt_ms:
            raise ValueError(
                "max_delivery_lag_ms cannot exceed one neural step; a larger "
                "lag means the clocks are not on adjacent grid points"
            )
        self.max_delivery_lag_ms = lag
        self.calls = 0
        self.applied = 0

    @property
    def eta(self) -> float:
        return float(self.stepper.eta)

    def reset(self) -> None:
        self.stream = AppendedRewardStream(provenance=self.stream.provenance)
        self.modulation = RewardModulation(self.modulation.config)
        self.provider = ModulationRewardProvider(self.stream, self.modulation)
        self.calls = 0
        self.applied = 0

    def __call__(self, context: dict) -> dict:
        if not isinstance(context, dict):
            raise TypeError("the post-update hook receives a context mapping")
        try:
            update = int(context["update"])
            neural_time_ms = float(context["neural_time_ms"])
            step_reward = context["step_reward"]
        except (KeyError, TypeError, ValueError):
            raise ConditionError(
                "the post-update context needs update, neural_time_ms and "
                "step_reward"
            ) from None

        deliveries = tuple(getattr(step_reward, "deliveries", ()))
        for delivery in deliveries:
            lag = abs(float(delivery.time_ms) - neural_time_ms)
            if lag > self.max_delivery_lag_ms + 1e-9:
                raise ConditionError(
                    "a reward delivery is more than half a neural step away "
                    f"from the step that consumes it ({delivery.time_ms} ms vs "
                    f"{neural_time_ms} ms, lag {lag:.6f} ms > "
                    f"{self.max_delivery_lag_ms:.6f} ms); the game and neural "
                    "clocks are not synchronised"
                )
        for delivery in deliveries:
            self.stream.append(delivery)

        # Evaluate the reward clock at the delivery timestamp so this update's
        # reward is applied by this update (the delivery may sit up to half a
        # neural step ahead of the grid point). Later updates are always
        # later in game time, so the provider clock stays monotonic.
        provider_time = neural_time_ms
        for delivery in deliveries:
            provider_time = max(provider_time, float(delivery.time_ms))
        modulation = self.provider.step(update, provider_time)
        self.calls += 1
        report = None
        if modulation is not None:
            report = self.stepper.learn(float(modulation))
            self.applied += 1
        return {
            "mode": (
                "rule_executed_zero_delta"
                if self.eta == 0.0
                else "rule_executed"
            ),
            "eta": self.eta,
            "n_deliveries": len(deliveries),
            "modulation": (
                None if modulation is None else round(float(modulation), 9)
            ),
            "applied": report is not None,
            "report": None if report is None else report.as_dict(),
        }

    def describe(self) -> dict:
        return {
            "kind": "plasticity_update_hook",
            "mode": (
                "rule_executed_zero_delta" if self.eta == 0.0 else "rule_executed"
            ),
            "eta": self.eta,
            "calls": self.calls,
            "reward_events_applied": self.applied,
            "modulation_config": self.modulation.config.describe(),
            "provider": type(self.provider).__name__,
            "reward_source": "adapter GameRewardFunction deliveries",
            "neural_dt_ms": self.neural_dt_ms,
            "max_delivery_lag_ms": self.max_delivery_lag_ms,
            "delivery_time_rule": (
                "a delivery must lie within max_delivery_lag_ms (half a neural "
                "step, the ClockSync.target_step rounding bound) of the "
                "consuming step; the modulation is evaluated at the delivery "
                "time so the reward is applied by its own update; a larger "
                "mismatch is a hard error"
            ),
            "limitations": [
                "the modulation scalar is a computational reward signal, not a "
                "dopamine, octopamine or serotonin measurement",
                "eligibility traces are model tags of coincident activity",
            ],
        }


def zero_delta_arrays(weight_state: Any) -> dict[str, bool]:
    """Whether both learned arrays are exactly zero (control diagnostics)."""
    return {
        "delta_exc_all_zero": bool(np.all(weight_state.delta_exc == 0.0)),
        "delta_inh_all_zero": bool(np.all(weight_state.delta_inh == 0.0)),
    }


__all__ = [
    "AppendedRewardStream",
    "PLASTICITY_MODES",
    "PlasticityUpdateHook",
    "zero_delta_arrays",
]
