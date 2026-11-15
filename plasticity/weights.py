"""Separated weight layers for three-factor plasticity.

SCIENTIFIC STATUS
    A weight here is a transformed structural synapse count in pA, not a
    conductance and not a measurement. The learned delta is a model variable.
    ``lower_factor`` and ``upper_factor`` are declared modelling choices fixed
    before any learning experiment; they are not fitted.

Five layers with strict write permissions:

    structural_count   int32    read-only   integer synapse count from the graph
    initial_pa         float32  read-only   copy of the transformed policy weights
    learned_delta_pa   float32  writable    additive learned change
    effective_pa       float32  writable    bounded initial + learned delta
    sign_class         int8     read-only   +1 excitatory, -1 inhibitory, 0 none

Only verified-sign edges carry an initial weight and may be updated. Unknown
edges stay at exactly zero for the whole run.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields
from typing import Mapping

import numpy as np


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _non_negative(value, name: str) -> float:
    number = _finite(value, name)
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


@dataclass(frozen=True)
class WeightBounds:
    """Declared weight limits around the initial structural weight."""

    lower_factor: float = 0.5
    upper_factor: float = 2.0
    absolute_min_pa: float | None = None
    absolute_max_pa: float | None = None
    max_abs_update_pa: float | None = None

    def __post_init__(self) -> None:
        lower = _finite(self.lower_factor, "lower_factor")
        upper = _finite(self.upper_factor, "upper_factor")
        if lower < 0:
            raise ValueError("lower_factor must be non-negative")
        if upper <= 0:
            raise ValueError("upper_factor must be positive")
        if lower > 1.0:
            raise ValueError("lower_factor must not exceed 1")
        if upper < 1.0:
            raise ValueError("upper_factor must be at least 1")
        object.__setattr__(self, "lower_factor", lower)
        object.__setattr__(self, "upper_factor", upper)
        minimum = (
            None
            if self.absolute_min_pa is None
            else _non_negative(self.absolute_min_pa, "absolute_min_pa")
        )
        maximum = (
            None
            if self.absolute_max_pa is None
            else _non_negative(self.absolute_max_pa, "absolute_max_pa")
        )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("absolute_min_pa must not exceed absolute_max_pa")
        if self.max_abs_update_pa is not None:
            clip = _finite(self.max_abs_update_pa, "max_abs_update_pa")
            if clip <= 0:
                raise ValueError("max_abs_update_pa must be positive")
            object.__setattr__(self, "max_abs_update_pa", clip)
        object.__setattr__(self, "absolute_min_pa", minimum)
        object.__setattr__(self, "absolute_max_pa", maximum)

    @classmethod
    def from_config(cls, payload: Mapping) -> "WeightBounds":
        values = {
            field.name: payload[field.name]
            for field in fields(cls)
            if field.name in payload
        }
        return cls(**values)

    def describe(self) -> dict:
        return {
            "lower_factor": self.lower_factor,
            "upper_factor": self.upper_factor,
            "absolute_min_pa": self.absolute_min_pa,
            "absolute_max_pa": self.absolute_max_pa,
            "max_abs_update_pa": self.max_abs_update_pa,
            "interpretation": (
                "relative bounds are a declared modelling choice around the "
                "initial structural weight; they are not fitted"
            ),
        }

    def lower_for(self, initial: np.ndarray) -> np.ndarray:
        lower = np.asarray(initial, dtype=np.float64) * self.lower_factor
        if self.absolute_min_pa is not None:
            lower = np.maximum(lower, self.absolute_min_pa)
        return lower

    def upper_for(self, initial: np.ndarray) -> np.ndarray:
        upper = np.asarray(initial, dtype=np.float64) * self.upper_factor
        if self.absolute_max_pa is not None:
            upper = np.minimum(upper, self.absolute_max_pa)
        return upper


def _digest_arrays(arrays: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in sorted(arrays):
        array = np.ascontiguousarray(arrays[name])
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("utf-8"))
        digest.update(str(array.shape).encode("utf-8"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def graph_signature(graph) -> str:
    """Digest of the structural arrays a weight state is bound to."""
    return _digest_arrays(
        {
            "root_ids": np.asarray(graph.root_ids),
            "out_indptr": np.asarray(graph.out_indptr),
            "edge_src": np.asarray(graph.edge_src),
            "edge_dst": np.asarray(graph.edge_dst),
            "edge_weight": np.asarray(graph.edge_weight),
            "threshold": np.asarray(int(graph.threshold), dtype=np.int64),
        }
    )


class WeightState:
    """Owned initial, learned and effective weight layers over CSR edges."""

    def __init__(self, graph, policy, bounds: WeightBounds | None = None) -> None:
        if int(policy.n_neurons) != int(graph.n_nodes):
            raise ValueError("policy and graph node counts differ")
        if int(policy.n_edges) != int(graph.n_edges):
            raise ValueError("policy and graph edge counts differ")
        if int(getattr(graph, "threshold", -1)) != int(policy.threshold):
            raise ValueError("policy threshold does not match the graph")
        self.bounds = bounds or WeightBounds()
        self.n_edges = int(graph.n_edges)
        self.n_neurons = int(graph.n_nodes)
        self._graph_signature = graph_signature(graph)

        structural = np.asarray(graph.edge_weight)
        if structural.shape != (self.n_edges,):
            raise ValueError("graph edge_weight must have one entry per edge")
        if np.any(structural < 1):
            raise ValueError("structural edge counts must be positive")
        self.structural_count = structural.astype(np.int32, copy=True)
        self.structural_count.flags.writeable = False

        initial_exc = np.asarray(policy.edge_exc_weight, dtype=np.float32)
        initial_inh = np.asarray(policy.edge_inh_weight, dtype=np.float32)
        if initial_exc.shape != (self.n_edges,) or initial_inh.shape != (
            self.n_edges,
        ):
            raise ValueError("policy edge arrays must match the graph edge count")
        if np.any((initial_exc > 0) & (initial_inh > 0)):
            raise ValueError("an edge cannot be both excitatory and inhibitory")
        self.initial_exc = initial_exc.copy()
        self.initial_inh = initial_inh.copy()
        self.initial_exc.flags.writeable = False
        self.initial_inh.flags.writeable = False

        self.delta_exc = np.zeros(self.n_edges, dtype=np.float32)
        self.delta_inh = np.zeros(self.n_edges, dtype=np.float32)
        self.effective_exc = self.initial_exc.copy()
        self.effective_inh = self.initial_inh.copy()

        self.plastic = (self.initial_exc > 0) | (self.initial_inh > 0)
        self.sign_class = np.zeros(self.n_edges, dtype=np.int8)
        self.sign_class[self.initial_exc > 0] = 1
        self.sign_class[self.initial_inh > 0] = -1
        self.sign_class.flags.writeable = False
        self._plastic_positions = np.flatnonzero(self.plastic).astype(np.int64)
        self._plastic_positions.flags.writeable = False

        initial = self.initial_magnitude
        for sign, label in ((1, "excitatory"), (-1, "inhibitory")):
            mask = self.sign_class == sign
            if not mask.any():
                continue
            lower = self.bounds.lower_for(initial[mask])
            upper = self.bounds.upper_for(initial[mask])
            if np.any(lower > upper):
                raise ValueError(
                    f"declared bounds are infeasible for {label} edges: "
                    "a lower bound exceeds the upper bound"
                )
        self._cumulative_clamps = 0
        self._cumulative_update_clips = 0
        self._n_update_calls = 0

    @classmethod
    def from_policy(
        cls, graph, policy, bounds: WeightBounds | None = None
    ) -> "WeightState":
        return cls(graph, policy, bounds)

    # -- read-only views ---------------------------------------------------

    @property
    def n_plastic(self) -> int:
        return int(self._plastic_positions.size)

    @property
    def plastic_positions(self) -> np.ndarray:
        """CSR edge indices that carry a verified sign."""
        return self._plastic_positions

    @property
    def graph_signature(self) -> str:
        return self._graph_signature

    @property
    def initial_magnitude(self) -> np.ndarray:
        return self.initial_exc + self.initial_inh

    @property
    def effective_magnitude(self) -> np.ndarray:
        return self.effective_exc + self.effective_inh

    @property
    def clamp_hits_total(self) -> int:
        return int(self._cumulative_clamps)

    @property
    def update_clip_hits_total(self) -> int:
        return int(self._cumulative_update_clips)

    @property
    def n_update_calls(self) -> int:
        return int(self._n_update_calls)

    @property
    def memory_bytes(self) -> int:
        return int(
            self.structural_count.nbytes
            + self.initial_exc.nbytes
            + self.initial_inh.nbytes
            + self.delta_exc.nbytes
            + self.delta_inh.nbytes
            + self.effective_exc.nbytes
            + self.effective_inh.nbytes
            + self.sign_class.nbytes
            + self.plastic.nbytes
            + self._plastic_positions.nbytes
        )

    # -- updates -----------------------------------------------------------

    def _check_slots(self, slots) -> np.ndarray:
        values = np.asarray(slots, dtype=np.int64).ravel()
        if values.size and (values.min() < 0 or values.max() >= self.n_edges):
            raise ValueError("slots contain edges outside the graph")
        if values.size > 1:
            ordered = np.sort(values)
            if np.any(ordered[1:] == ordered[:-1]):
                raise ValueError("slots must not contain duplicate edges")
        return values

    def _empty_update(self) -> dict:
        return {
            "n_slots": 0,
            "n_updates": 0,
            "sum_applied_pa": 0.0,
            "sum_abs_applied_pa": 0.0,
            "max_abs_applied_pa": 0.0,
            "clamp_hits": 0,
            "update_clip_hits": 0,
            "sign_violations": 0,
        }

    def apply_update(self, slots, dw) -> dict:
        """Add one bounded update per slot to the matching sign channel."""
        edges = self._check_slots(slots)
        updates = np.asarray(dw, dtype=np.float64).ravel()
        if updates.size != edges.size:
            raise ValueError("dw must have one entry per slot")
        if edges.size == 0:
            return self._empty_update()
        if not np.all(np.isfinite(updates)):
            raise ValueError("dw must be finite")
        if self.bounds.max_abs_update_pa is not None:
            clip = self.bounds.max_abs_update_pa
            clipped = np.clip(updates, -clip, clip)
            update_clips = int(np.count_nonzero(clipped != updates))
            updates = clipped
        else:
            update_clips = 0
        signs = self.sign_class[edges]
        if np.any(signs == 0):
            raise ValueError("cannot update an edge without a verified sign")

        clamp_hits = 0
        sign_violations = 0
        applied = np.zeros(edges.size, dtype=np.float64)
        for sign, delta_array, effective_array, initial_array in (
            (1, self.delta_exc, self.effective_exc, self.initial_exc),
            (-1, self.delta_inh, self.effective_inh, self.initial_inh),
        ):
            mask = signs == sign
            if not mask.any():
                continue
            selected = edges[mask]
            current = delta_array[selected].astype(np.float64)
            proposed = current + updates[mask]
            initial = initial_array[selected].astype(np.float64)
            # Bounds constrain the effective weight, so shift them into delta
            # space before clipping the learned change.
            lower = self.bounds.lower_for(initial) - initial
            upper = self.bounds.upper_for(initial) - initial
            bounded = np.clip(proposed, lower, upper)
            clamp_hits += int(np.count_nonzero(bounded != proposed))
            stored_delta = bounded.astype(np.float32)
            # Derive the effective layer from the stored float32 delta so the
            # layer identity survives rounding over repeated updates.
            effective_array[selected] = initial_array[selected] + stored_delta
            if not np.all(np.isfinite(stored_delta)) or not np.all(
                np.isfinite(effective_array[selected])
            ):
                raise FloatingPointError("weight update produced a non-finite value")
            sign_violations += int(
                np.count_nonzero(effective_array[selected] < 0)
            )
            applied[mask] = stored_delta.astype(np.float64) - current
            delta_array[selected] = stored_delta

        self._cumulative_clamps += clamp_hits
        self._cumulative_update_clips += update_clips
        self._n_update_calls += 1
        return {
            "n_slots": int(edges.size),
            "n_updates": int(np.count_nonzero(applied)),
            "sum_applied_pa": float(applied.sum()),
            "sum_abs_applied_pa": float(np.abs(applied).sum()),
            "max_abs_applied_pa": float(np.abs(applied).max()),
            "clamp_hits": int(clamp_hits),
            "update_clip_hits": int(update_clips),
            "sign_violations": int(sign_violations),
        }

    def decay_learned(self, factor: float) -> int:
        """Multiply every nonzero learned delta by ``factor`` in [0, 1]."""
        factor = _finite(factor, "factor")
        if not 0.0 <= factor <= 1.0:
            raise ValueError("decay factor must lie in [0, 1]")
        if factor == 1.0:
            return 0
        changed = 0
        for delta_array, effective_array, initial_array in (
            (self.delta_exc, self.effective_exc, self.initial_exc),
            (self.delta_inh, self.effective_inh, self.initial_inh),
        ):
            touched = np.flatnonzero(delta_array)
            if touched.size == 0:
                continue
            decayed = (delta_array[touched].astype(np.float64) * factor).astype(
                np.float32
            )
            delta_array[touched] = decayed
            effective_array[touched] = initial_array[touched] + decayed
            changed += int(touched.size)
        return changed

    def restore_deltas(self, delta_exc, delta_inh) -> None:
        """Replace the learned layer and recompute the effective layer."""
        exc = np.asarray(delta_exc, dtype=np.float32)
        inh = np.asarray(delta_inh, dtype=np.float32)
        if exc.shape != (self.n_edges,) or inh.shape != (self.n_edges,):
            raise ValueError("restored deltas must match the edge count")
        if not np.all(np.isfinite(exc)) or not np.all(np.isfinite(inh)):
            raise ValueError("restored deltas must be finite")
        if np.any(exc[~self.plastic]) or np.any(inh[~self.plastic]):
            raise ValueError("non-plastic edges must keep a zero delta")
        if np.any((exc != 0) & (self.sign_class != 1)):
            raise ValueError("excitatory deltas exist on non-excitatory edges")
        if np.any((inh != 0) & (self.sign_class != -1)):
            raise ValueError("inhibitory deltas exist on non-inhibitory edges")
        relative_slack = 8.0 * float(np.finfo(np.float32).eps)
        for delta, initial in (
            (exc, self.initial_exc),
            (inh, self.initial_inh),
        ):
            proposed = initial.astype(np.float64) + delta.astype(np.float64)
            lower = self.bounds.lower_for(initial)
            upper = self.bounds.upper_for(initial)
            slack = relative_slack * np.maximum(
                1.0, np.maximum(np.abs(lower), np.abs(upper))
            )
            if np.any(proposed < lower - slack) or np.any(proposed > upper + slack):
                raise ValueError("restored delta lies outside the declared bounds")
        self.delta_exc[:] = exc
        self.delta_inh[:] = inh
        self.recompute_effective()

    def recompute_effective(self) -> None:
        self.effective_exc[:] = self.initial_exc + self.delta_exc
        self.effective_inh[:] = self.initial_inh + self.delta_inh

    # -- verification ------------------------------------------------------

    def assert_invariants(self) -> dict:
        """Check every declared invariant and raise on the first failure."""
        checks = {
            "deltas_finite": bool(
                np.all(np.isfinite(self.delta_exc))
                and np.all(np.isfinite(self.delta_inh))
            ),
            "effective_finite": bool(
                np.all(np.isfinite(self.effective_exc))
                and np.all(np.isfinite(self.effective_inh))
            ),
            "deltas_zero_off_plastic": bool(
                not np.any(self.delta_exc[~self.plastic])
                and not np.any(self.delta_inh[~self.plastic])
            ),
            "excitatory_channel_only": bool(
                np.all(self.delta_inh[self.sign_class != -1] == 0)
                and np.all(self.initial_inh[self.sign_class != -1] == 0)
                and np.all(self.effective_inh[self.sign_class != -1] == 0)
            ),
            "inhibitory_channel_only": bool(
                np.all(self.delta_exc[self.sign_class != 1] == 0)
                and np.all(self.initial_exc[self.sign_class != 1] == 0)
                and np.all(self.effective_exc[self.sign_class != 1] == 0)
            ),
            "effective_non_negative": bool(
                np.all(self.effective_exc >= 0) and np.all(self.effective_inh >= 0)
            ),
        }
        expected_exc = (self.initial_exc + self.delta_exc).astype(np.float32)
        expected_inh = (self.initial_inh + self.delta_inh).astype(np.float32)
        checks["effective_matches_layers"] = bool(
            np.array_equal(self.effective_exc, expected_exc)
            and np.array_equal(self.effective_inh, expected_inh)
        )
        within_bounds = True
        # The effective layer is stored in float32, so a value at a declared
        # bound can round by at most a few ulps across the bound.
        relative_slack = 8.0 * float(np.finfo(np.float32).eps)
        for delta, effective, initial in (
            (self.delta_exc, self.effective_exc, self.initial_exc),
            (self.delta_inh, self.effective_inh, self.initial_inh),
        ):
            mask = self.plastic
            if not mask.any():
                continue
            lower = self.bounds.lower_for(initial[mask])
            upper = self.bounds.upper_for(initial[mask])
            stored = effective[mask].astype(np.float64)
            slack = relative_slack * np.maximum(
                1.0, np.maximum(np.abs(lower), np.abs(upper))
            )
            within_bounds = within_bounds and bool(
                np.all(stored >= lower - slack)
                and np.all(stored <= upper + slack)
            )
        checks["within_declared_bounds"] = within_bounds
        failures = [name for name, ok in checks.items() if not ok]
        if failures:
            raise ValueError(f"weight-state invariant failures: {failures}")
        return checks

    # -- digests -----------------------------------------------------------

    def structural_digest(self) -> str:
        return _digest_arrays({"structural_count": self.structural_count})

    def initial_digest(self) -> str:
        return _digest_arrays(
            {"initial_exc": self.initial_exc, "initial_inh": self.initial_inh}
        )

    def delta_digest(self) -> str:
        return _digest_arrays(
            {"delta_exc": self.delta_exc, "delta_inh": self.delta_inh}
        )

    def effective_digest(self) -> str:
        return _digest_arrays(
            {"effective_exc": self.effective_exc, "effective_inh": self.effective_inh}
        )

    def digest(self) -> str:
        """Digest of the learned layer; the state that must survive a checkpoint."""
        return self.delta_digest()

    def describe(self) -> dict:
        delta_sum = float(
            self.delta_exc.sum(dtype=np.float64)
            + self.delta_inh.sum(dtype=np.float64)
        )
        delta_abs_sum = float(
            np.abs(self.delta_exc).sum(dtype=np.float64)
            + np.abs(self.delta_inh).sum(dtype=np.float64)
        )
        delta_max_abs = float(
            max(
                np.abs(self.delta_exc).max(initial=0.0),
                np.abs(self.delta_inh).max(initial=0.0),
            )
        )
        changed_mask = (self.delta_exc != 0) | (self.delta_inh != 0)
        changed = int(np.count_nonzero(changed_mask))
        if changed:
            touched_delta = (
                self.delta_exc[changed_mask].astype(np.float64)
                + self.delta_inh[changed_mask].astype(np.float64)
            )
            touched_initial = self.initial_magnitude[changed_mask].astype(
                np.float64
            )
            relative = touched_delta / np.maximum(touched_initial, 1e-12)
            relative_stats = {
                "mean": round(float(relative.mean()), 9),
                "min": round(float(relative.min()), 9),
                "max": round(float(relative.max()), 9),
            }
        else:
            relative_stats = {"mean": 0.0, "min": 0.0, "max": 0.0}
        saturated = 0
        for delta_array, initial_array in (
            (self.delta_exc, self.initial_exc),
            (self.delta_inh, self.initial_inh),
        ):
            mask = delta_array != 0
            if mask.any():
                proposed = initial_array[mask].astype(np.float64) + delta_array[
                    mask
                ].astype(np.float64)
                upper = self.bounds.upper_for(initial_array[mask])
                lower = self.bounds.lower_for(initial_array[mask])
                saturated += int(
                    np.count_nonzero(
                        np.isclose(proposed, upper) | np.isclose(proposed, lower)
                    )
                )
        return {
            "model": "separated_structural_initial_learned_effective_weights",
            "bounds": self.bounds.describe(),
            "n_edges": self.n_edges,
            "n_plastic": self.n_plastic,
            "n_excitatory": int(np.count_nonzero(self.sign_class == 1)),
            "n_inhibitory": int(np.count_nonzero(self.sign_class == -1)),
            "n_unknown": int(np.count_nonzero(self.sign_class == 0)),
            "structural_synapses": int(self.structural_count.sum(dtype=np.int64)),
            "initial_sum_pa": round(float(self.initial_magnitude.sum(dtype=np.float64)), 6),
            "effective_sum_pa": round(
                float(self.effective_magnitude.sum(dtype=np.float64)), 6
            ),
            "delta_sum_pa": round(delta_sum, 9),
            "delta_abs_sum_pa": round(delta_abs_sum, 9),
            "delta_max_abs_pa": round(delta_max_abs, 9),
            "n_changed_edges": changed,
            "changed_edge_share": round(changed / max(1, self.n_plastic), 9),
            "saturated_edges": int(saturated),
            "relative_delta": relative_stats,
            "cumulative_clamp_hits": self.clamp_hits_total,
            "cumulative_update_clips": self.update_clip_hits_total,
            "n_update_calls": self.n_update_calls,
            "digests": {
                "structural": self.structural_digest(),
                "initial": self.initial_digest(),
                "learned_delta": self.delta_digest(),
                "effective": self.effective_digest(),
            },
            "classification": (
                "computational weight state; pA values are transformed synapse "
                "counts, not conductances"
            ),
        }
