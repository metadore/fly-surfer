"""Per-decision motor-population activity over the decoder window.

SCIENTIFIC STATUS
    These are counts and rates of spikes on annotated motor populations in a
    model simulation. They are not a measured motor command and a ``sufficient``
    flag is a threshold on model activity, not evidence that the animal would
    move.

The block is produced from the ``SpikeRecorder`` alone, so it exists whether
or not the fixed-threshold decoder is called. It uses the same half-open window
``[end - window_ms, end)`` as the decoder, which makes the block comparable
across Phase 8 conditions.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from motor.populations import ACTION_POPULATIONS

WINDOW_RULE = "[start, end)"

DEFAULT_MIN_SPIKES = 5
DEFAULT_MIN_ACTIVE_NEURONS = 3


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _as_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    if int(value) < 0:
        raise ValueError(f"{name} must be non-negative")
    return int(value)


def _counts_in_window(
    recorder: Any, start_ms: float, end_ms: float
) -> np.ndarray:
    times = np.asarray(recorder.spike_times_ms)
    indices = np.asarray(recorder.spike_neuron_indices)
    lo = int(np.searchsorted(times, start_ms, side="left"))
    hi = int(np.searchsorted(times, end_ms, side="left"))
    return np.bincount(
        indices[lo:hi], minlength=int(recorder.n_neurons)
    ).astype(np.int64)


def motor_activity_window(
    recorder: Any,
    populations: Any,
    end_ms: float,
    window_ms: float,
    *,
    min_spikes: int = DEFAULT_MIN_SPIKES,
    min_active_neurons: int = DEFAULT_MIN_ACTIVE_NEURONS,
) -> dict:
    """Describe LEFT/RIGHT/JUMP activity in ``[end - window, end)``."""
    end = _finite(end_ms, "end_ms")
    window = _finite(window_ms, "window_ms")
    if window <= 0:
        raise ValueError("window_ms must be positive")
    if end < 0:
        raise ValueError("end_ms cannot be negative")
    min_spikes = _as_int(min_spikes, "min_spikes")
    min_active = _as_int(min_active_neurons, "min_active_neurons")
    if int(getattr(populations, "n_neurons", -1)) != int(
        getattr(recorder, "n_neurons", -2)
    ):
        raise ValueError("recorder and populations neuron counts differ")

    start = max(0.0, end - window) if end > 0 else 0.0
    counts = _counts_in_window(recorder, start, end)
    seconds = (end - start) / 1000.0

    block: dict[str, Any] = {
        "window_start_ms": round(start, 6),
        "window_end_ms": round(end, 6),
        "window_ms": round(window, 6),
        "window_rule": WINDOW_RULE,
        "source": "recorder",
        "total_spikes": int(counts.sum()),
        "any_motor_spike": False,
        "populations_with_spikes": [],
    }
    motor_spikes = 0
    with_spikes: list[str] = []
    for action in ACTION_POPULATIONS:
        mask = np.asarray(populations.mask(action), dtype=bool)
        size = int(np.count_nonzero(mask))
        spikes = int(counts[mask].sum())
        active = int(np.count_nonzero(counts[mask]))
        fraction = active / size if size else 0.0
        rate = spikes / size / seconds if size and seconds > 0 else 0.0
        reasons: list[str] = []
        if size == 0:
            reasons.append("empty_population")
        else:
            if spikes < min_spikes:
                reasons.append("spikes_below_minimum")
            if active < min_active:
                reasons.append("active_neurons_below_minimum")
        block[action] = {
            "spikes": spikes,
            "active_neurons": active,
            "active_fraction": round(float(fraction), 6),
            "mean_rate_hz": round(float(rate), 6),
            "sufficient": not reasons,
            "reason": "ok" if not reasons else "+".join(reasons),
        }
        motor_spikes += spikes
        if spikes:
            with_spikes.append(action)
    block["total_motor_spikes"] = int(motor_spikes)
    block["any_motor_spike"] = bool(motor_spikes > 0)
    block["populations_with_spikes"] = with_spikes
    return block


def motor_activity_from_decoder(
    motor_activity: dict, decoder_output: dict | None
) -> dict:
    """Attach the fixed decoder's per-population evidence when both exist.

    The block stays authoritative: it is produced from the recorder, and the
    decoder evidence is added only for cross-checking the two agree.
    """
    if decoder_output is None:
        return motor_activity
    evidence = decoder_output.get("evidence") or {}
    block = dict(motor_activity)
    block["decoder_evidence"] = {
        action: dict(values) for action, values in evidence.items()
    }
    block["decoder_evidence_matches"] = all(
        int(evidence[action]["spikes"]) == int(motor_activity[action]["spikes"])
        for action in ACTION_POPULATIONS
        if action in evidence
    )
    return block
