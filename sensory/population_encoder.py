"""Population coding of environment features.

Each encoder converts a scalar or categorical feature into a vector of
dimensionless activations in ``[baseline, amplitude]``. An activation is an
experimental input drive, not a firing rate and not a current: the sensory
scheduler multiplies it by a configured current amplitude in pA.

Gaussian coding follows ``r_i(x) = baseline + (A - baseline) *
exp(-(x - mu_i)^2 / (2 sigma^2))`` with preferred stimuli spread across the
feature range. Lane and boolean features use dedicated categorical
populations instead of being forced through the same formula.

Nothing here claims to reproduce a fly sensory code. The tuning width,
amplitude and preferred stimuli are configured assumptions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

SUPPORTED_KINDS = ("gaussian", "lane", "boolean")


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _level(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number in [0, 1]")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return number


@dataclass(frozen=True)
class EncoderSpec:
    """Validated encoder parameters shared by every coding scheme."""

    kind: str
    n_neurons: int | None = None
    minimum: float = 0.0
    maximum: float = 1.0
    sigma_fraction: float = 0.25
    amplitude: float = 1.0
    baseline: float = 0.0
    lanes: int = 3
    neurons_per_lane: int = 4

    def __post_init__(self) -> None:
        if self.kind not in SUPPORTED_KINDS:
            raise ValueError(
                f"unknown encoder kind {self.kind!r}; expected {SUPPORTED_KINDS}"
            )
        amplitude = _level(self.amplitude, "amplitude")
        baseline = _level(self.baseline, "baseline")
        if baseline > amplitude:
            raise ValueError("baseline must not exceed amplitude")
        if self.kind == "gaussian":
            if self.n_neurons is None:
                raise ValueError("a gaussian encoder requires n_neurons")
            _positive_int(self.n_neurons, "n_neurons")
            if not math.isfinite(self.minimum) or not math.isfinite(self.maximum):
                raise ValueError("feature range must be finite")
            if self.maximum <= self.minimum:
                raise ValueError("maximum must exceed minimum")
            if not 0.0 < float(self.sigma_fraction) <= 1.0:
                raise ValueError("sigma_fraction must be in (0, 1]")
        elif self.kind == "lane":
            _positive_int(self.lanes, "lanes")
            _positive_int(self.neurons_per_lane, "neurons_per_lane")
        else:
            if self.n_neurons is None:
                raise ValueError("a boolean encoder requires n_neurons")
            _positive_int(self.n_neurons, "n_neurons")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EncoderSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("encoder configuration must be a mapping")
        return cls(
            kind=str(payload.get("kind", "")),
            n_neurons=payload.get("n_neurons"),
            minimum=float(payload.get("minimum", 0.0)),
            maximum=float(payload.get("maximum", 1.0)),
            sigma_fraction=float(payload.get("sigma_fraction", 0.25)),
            amplitude=float(payload.get("amplitude", 1.0)),
            baseline=float(payload.get("baseline", 0.0)),
            lanes=int(payload.get("lanes", 3)),
            neurons_per_lane=int(payload.get("neurons_per_lane", 4)),
        )

    @property
    def output_size(self) -> int:
        if self.kind == "gaussian" or self.kind == "boolean":
            return int(self.n_neurons or 0)
        return int(self.lanes) * int(self.neurons_per_lane)

    def info(self) -> dict:
        payload = {
            "kind": self.kind,
            "output_size": self.output_size,
            "amplitude": self.amplitude,
            "baseline": self.baseline,
        }
        if self.kind == "gaussian":
            payload.update(
                {
                    "n_neurons": self.n_neurons,
                    "minimum": self.minimum,
                    "maximum": self.maximum,
                    "sigma_fraction": self.sigma_fraction,
                }
            )
        elif self.kind == "lane":
            payload.update(
                {"lanes": self.lanes, "neurons_per_lane": self.neurons_per_lane}
            )
        else:
            payload["n_neurons"] = self.n_neurons
        return payload


class GaussianPopulation:
    """Gaussian tuning over an ordered, evenly spaced preferred set."""

    def __init__(self, spec: EncoderSpec) -> None:
        if spec.kind != "gaussian":
            raise ValueError("GaussianPopulation requires a gaussian spec")
        self.spec = spec
        n = int(spec.n_neurons)
        self.preferred = np.linspace(spec.minimum, spec.maximum, n)
        self.sigma = float(spec.sigma_fraction) * (spec.maximum - spec.minimum)

    def encode(self, value: float) -> np.ndarray:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("gaussian input must be a number")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("gaussian input must be finite")
        if not self.spec.minimum <= number <= self.spec.maximum:
            raise ValueError(
                f"gaussian input {number!r} outside "
                f"[{self.spec.minimum}, {self.spec.maximum}]"
            )
        distance = self.preferred - number
        curve = np.exp(-(distance * distance) / (2.0 * self.sigma**2))
        return self.spec.baseline + (self.spec.amplitude - self.spec.baseline) * curve

    def baseline_response(self) -> np.ndarray:
        return np.full(self.spec.output_size, self.spec.baseline, dtype=np.float64)

    def tuning_curves(self, values: Any) -> np.ndarray:
        values = np.asarray(list(values), dtype=np.float64)
        if values.ndim != 1:
            raise ValueError("values must be one-dimensional")
        return np.stack([self.encode(float(value)) for value in values])

    def info(self) -> dict:
        payload = self.spec.info()
        payload.update(
            {
                "preferred": self.preferred.tolist(),
                "sigma": self.sigma,
            }
        )
        return payload


class LanePopulation:
    """One dedicated sub-population per categorical lane."""

    def __init__(self, spec: EncoderSpec) -> None:
        if spec.kind != "lane":
            raise ValueError("LanePopulation requires a lane spec")
        self.spec = spec
        self.preferred_lanes = np.repeat(
            np.arange(spec.lanes, dtype=np.int64), spec.neurons_per_lane
        )

    def encode(self, lane: int) -> np.ndarray:
        if isinstance(lane, bool) or not isinstance(lane, (int, np.integer)):
            raise ValueError("lane input must be an integer")
        lane = int(lane)
        if not 0 <= lane < self.spec.lanes:
            raise ValueError(f"lane {lane} outside [0, {self.spec.lanes - 1}]")
        response = self.baseline_response()
        start = lane * self.spec.neurons_per_lane
        response[start : start + self.spec.neurons_per_lane] = self.spec.amplitude
        return response

    def baseline_response(self) -> np.ndarray:
        return np.full(self.spec.output_size, self.spec.baseline, dtype=np.float64)

    def info(self) -> dict:
        payload = self.spec.info()
        payload["preferred_lanes"] = self.preferred_lanes.tolist()
        return payload


class BooleanPopulation:
    """A state-responsive population that is on or off."""

    def __init__(self, spec: EncoderSpec) -> None:
        if spec.kind != "boolean":
            raise ValueError("BooleanPopulation requires a boolean spec")
        self.spec = spec

    def encode(self, flag: float | bool) -> np.ndarray:
        if isinstance(flag, (bool, np.bool_)):
            active = bool(flag)
        elif isinstance(flag, (int, float)) and float(flag) in (0.0, 1.0):
            active = bool(flag)
        else:
            raise ValueError("boolean input must be a bool or exactly 0/1")
        value = self.spec.amplitude if active else self.spec.baseline
        return np.full(self.spec.output_size, value, dtype=np.float64)

    def baseline_response(self) -> np.ndarray:
        return np.full(self.spec.output_size, self.spec.baseline, dtype=np.float64)

    def info(self) -> dict:
        return self.spec.info()


def build_encoder(payload: Mapping[str, Any]):
    spec = EncoderSpec.from_dict(payload)
    if spec.kind == "gaussian":
        return GaussianPopulation(spec)
    if spec.kind == "lane":
        return LanePopulation(spec)
    return BooleanPopulation(spec)


def build_encoders(features: Mapping[str, Mapping[str, Any]]) -> dict:
    """Build encoders in configuration order."""
    if not isinstance(features, Mapping) or not features:
        raise ValueError("features must be a non-empty mapping")
    encoders = {}
    for name, payload in features.items():
        if not isinstance(name, str) or not name:
            raise ValueError("feature names must be non-empty strings")
        encoders[name] = build_encoder(payload)
    return encoders


def encode_state(
    features: Mapping[str, float | int | None], encoders: Mapping[str, Any]
) -> dict[str, np.ndarray]:
    """Encode one feature dictionary, preserving encoder order.

    ``None`` means the underlying object is absent; the encoder emits its
    baseline response rather than a fabricated lane or distance.
    """
    if not isinstance(features, Mapping):
        raise ValueError("features must be a mapping")
    responses: dict[str, np.ndarray] = {}
    for name, encoder in encoders.items():
        if name not in features:
            raise ValueError(f"state is missing feature {name!r}")
        value = features[name]
        if value is None:
            responses[name] = encoder.baseline_response()
        else:
            responses[name] = encoder.encode(value)
    return responses
