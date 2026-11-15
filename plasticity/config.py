"""Validated loading of the Phase 5D ``weights``/``rule`` configuration.

SCIENTIFIC STATUS
    The bounds and rates here are declared modelling choices. Loading them
    does not fit them to data; every value is fixed before an experiment runs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

from .rules import RuleConfig
from .traces import TraceConfig
from .weights import WeightBounds, WeightState

DEFAULT_SIMULATION = {
    "dt_ms": 0.5,
    "duration_ms": 100.0,
    "tau_exc_ms": 5.0,
    "tau_inh_ms": 8.0,
    "delay_ms": 1.0,
    "background_current_pa": 0.0,
    "noise_std_pa": 0.0,
    "max_recorded_spikes": 2_000_000,
}

_POSITIVE = ("dt_ms", "duration_ms", "tau_exc_ms", "tau_inh_ms", "max_recorded_spikes")
_NON_NEGATIVE = ("delay_ms", "noise_std_pa")


@dataclass(frozen=True)
class PlasticityConfig:
    """The validated Phase 5D sections of ``configs/plasticity.yaml``."""

    traces: TraceConfig
    bounds: WeightBounds
    rule: RuleConfig
    simulation: dict
    fixed_mode_eta: float
    primary_threshold: int
    raw: dict

    def weight_state(self, graph, policy) -> WeightState:
        return WeightState(graph, policy, self.bounds)

    def describe(self) -> dict:
        return {
            "weights": {
                "bounds": self.bounds.describe(),
                "fixed_mode_eta": self.fixed_mode_eta,
                "primary_threshold": self.primary_threshold,
            },
            "rule": self.rule.describe(),
            "simulation": dict(self.simulation),
            "traces": self.traces.describe(),
        }


def _mapping(value, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def _number(value, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if positive and number <= 0:
        raise ValueError(f"{name} must be positive")
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


def load_plasticity_config(path: str | Path) -> PlasticityConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    root = _mapping(raw, "plasticity config")

    traces = TraceConfig(root)
    weights_section = _mapping(root.get("weights", {}), "weights")
    bounds = WeightBounds.from_config(
        _mapping(weights_section.get("bounds", {}), "weights.bounds")
    )
    fixed_mode_eta = _number(
        weights_section.get("fixed_mode_eta", 0.0), "weights.fixed_mode_eta"
    )
    if fixed_mode_eta != 0.0:
        raise ValueError(
            "weights.fixed_mode_eta must be exactly 0.0; the eta = 0 contract "
            "cannot be weakened"
        )
    primary_threshold = int(weights_section.get("primary_threshold", 5))
    if primary_threshold < 1:
        raise ValueError("weights.primary_threshold must be positive")

    rule_section = _mapping(root.get("rule", {}), "rule")
    rule = RuleConfig.from_config(rule_section)

    raw_simulation = _mapping(root.get("simulation", {}), "simulation")
    simulation = dict(DEFAULT_SIMULATION)
    for key, value in raw_simulation.items():
        if key not in DEFAULT_SIMULATION:
            raise ValueError(f"unknown simulation key: {key}")
        simulation[key] = value
    for key in _POSITIVE:
        simulation[key] = _number(
            simulation[key], f"simulation.{key}", positive=True
        )
    for key in _NON_NEGATIVE:
        simulation[key] = _number(simulation[key], f"simulation.{key}")
    background = simulation["background_current_pa"]
    if isinstance(background, bool) or not isinstance(background, (int, float)):
        raise ValueError("simulation.background_current_pa must be a number")
    if not math.isfinite(float(background)):
        raise ValueError("simulation.background_current_pa must be finite")
    simulation["background_current_pa"] = float(background)
    if simulation["max_recorded_spikes"] != int(simulation["max_recorded_spikes"]):
        raise ValueError("simulation.max_recorded_spikes must be an integer")
    simulation["max_recorded_spikes"] = int(simulation["max_recorded_spikes"])

    return PlasticityConfig(
        traces=traces,
        bounds=bounds,
        rule=rule,
        simulation=simulation,
        fixed_mode_eta=fixed_mode_eta,
        primary_threshold=primary_threshold,
        raw=root,
    )
