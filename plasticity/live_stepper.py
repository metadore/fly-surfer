"""Live plastic BANC stepper for Phase 8 conditions B and D.

SCIENTIFIC STATUS
    This module adds a pathway, not a claim. A learned weight is a model
    variable changed by the declared three-factor rule; a nonzero update is not
    evidence of learning, and a decoder label is not a biological motor
    command.

``LivePlasticStepper`` is an additive subclass of
``environment.live_loop.LiveBancStepper``. The fixed-weight per-step order, the
current dtype and the RNG call order are inherited unchanged: the subclass only

1. replaces ``self.synapses`` with
   :class:`~plasticity.plastic_synapses.PlasticSignedSynapses`, whose weight
   arrays are the owned effective layers of a
   :class:`~plasticity.weights.WeightState`;
2. installs a :class:`~plasticity.engine.PlasticityEngine` and observes each
   step through the parent's default-off ``step_observer`` hook;
3. exposes ``learn(delta_t)`` so the closed loop can apply a reward-event
   update without resetting the network.

With ``eta = 0`` the effective layers are bit-identical copies of the policy
arrays, so every delivered current and every recorded spike is identical to the
fixed-weight ``LiveBancStepper`` for the same seed and inputs. That identity is
a structural property of the code path, not an assumption.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from environment.live_loop import LiveBancStepper

from .engine import PlasticityEngine
from .plastic_synapses import PlasticSignedSynapses
from .rules import RuleConfig, ThreeFactorRule, UpdateReport
from .traces import TraceConfig
from .weights import WeightBounds, WeightState

PLASTICITY_LIMITATIONS = [
    "A learned weight is a model output of a declared computational rule, not "
    "a biological measurement.",
    "Eligibility traces are short-lived model tags, not measured synaptic "
    "tags.",
    "The reward prediction error is the error of a declared value model or an "
    "external task scalar, not a dopamine, octopamine or serotonin measurement.",
    "Conditions B and D change synapses only; A and C hold the same weights "
    "fixed and make no learning claim.",
]


class LivePlasticStepper(LiveBancStepper):
    """Advance a live BANC network whose weights may change between updates."""

    def __init__(
        self,
        graph: Any,
        policy: Any,
        *,
        weight_state: WeightState | None = None,
        bounds: WeightBounds | None = None,
        rule: ThreeFactorRule | None = None,
        rule_config: RuleConfig | None = None,
        trace_config: TraceConfig | None = None,
        enable_traces: bool = True,
        prune_interval_steps: int | None = None,
        tau_exc_ms: float = 5.0,
        tau_inh_ms: float = 8.0,
        delay_ms: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            graph,
            policy,
            tau_exc_ms=tau_exc_ms,
            tau_inh_ms=tau_inh_ms,
            delay_ms=delay_ms,
            **kwargs,
        )
        if weight_state is None:
            weight_state = WeightState(graph, policy, bounds)
        elif not isinstance(weight_state, WeightState):
            raise ValueError("weight_state must be a WeightState")
        if weight_state.n_edges != int(graph.n_edges):
            raise ValueError("weight state and graph edge counts differ")
        self.weight_state = weight_state

        if rule is None:
            rule = ThreeFactorRule(
                rule_config or RuleConfig(eta=0.0), weight_state
            )
        elif not isinstance(rule, ThreeFactorRule):
            raise ValueError("rule must be a ThreeFactorRule")
        if rule.weight_state is not weight_state:
            raise ValueError("rule and stepper must share one weight state")
        self.rule = rule

        self.synapses = PlasticSignedSynapses(
            graph,
            policy,
            weight_state,
            self.dt_ms,
            tau_exc_ms=tau_exc_ms,
            tau_inh_ms=tau_inh_ms,
            delay_ms=delay_ms,
        )
        self.engine = PlasticityEngine(
            graph,
            weight_state,
            rule,
            trace_config,
            dt_ms=self.dt_ms,
            delay_steps=self.synapses.delay_steps,
            enable_traces=enable_traces,
            prune_interval_steps=prune_interval_steps,
        )
        self.step_observer = self._observe_plastic_step
        self._reports: list[UpdateReport] = []

    # -- elastic coupling --------------------------------------------------

    @property
    def eta(self) -> float:
        return float(self.rule.eta)

    @property
    def update_reports(self) -> tuple[UpdateReport, ...]:
        return tuple(self._reports)

    def reset(self) -> None:
        super().reset()
        self.engine.reset()
        self._reports = []

    def _observe_plastic_step(self, step: int, spikes: np.ndarray) -> None:
        self.engine.observe_step(
            step, spikes, self.synapses.last_active_edges
        )

    def learn(
        self, delta_t: float, *, step: int | None = None
    ) -> UpdateReport | None:
        """Apply one declared three-factor update to the touched edges.

        ``step`` defaults to the step that was just simulated. The engine only
        tags edges that were touched; with ``eta = 0`` this returns a report
        with zero applied updates and changes no weight.
        """
        target = self._step_index - 1 if step is None else int(step)
        if target < 0:
            raise ValueError("no simulated step is available to learn from")
        report = self.engine.learn(target, delta_t)
        if report is not None:
            self._reports.append(report)
        return report

    # -- reporting ---------------------------------------------------------

    def describe(self) -> dict:
        payload = super().describe()
        payload.update(
            {
                "kind": "live_plastic_stepper",
                "pathway": "plastic_three_factor",
                "eta": self.eta,
                "n_plastic_edges": int(self.weight_state.n_plastic),
                "traces_enabled": bool(self.engine.traces_enabled),
                "n_weight_updates": int(self.weight_state.n_update_calls),
                "reset_policy": (
                    "once per episode for membrane, synapses, recorder, traces "
                    "and delay line; the network is never restarted between "
                    "game updates"
                ),
                "limitations": PLASTICITY_LIMITATIONS,
            }
        )
        return payload
