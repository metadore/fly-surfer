"""Deterministic discretisation of archived variables.

Every transform is a pure function of its inputs: identical values always
produce identical codes, edges and labels. Missing observations become the
sentinel ``MISSING`` and are excluded by every estimator.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MISSING = -1


@dataclass(frozen=True)
class Discretized:
    """Coded variable plus the declaration that produced it."""

    codes: np.ndarray
    labels: tuple[str, ...]
    spec: dict
    n_missing: int

    @property
    def n_bins(self) -> int:
        return len(self.labels)

    @property
    def n(self) -> int:
        return int(np.count_nonzero(self.codes >= 0))

    def summary(self) -> dict:
        counts = np.bincount(self.codes[self.codes >= 0], minlength=self.n_bins)
        return {
            "name": self.spec.get("name"),
            "kind": self.spec.get("kind"),
            "n_bins": self.n_bins,
            "n": self.n,
            "n_missing": self.n_missing,
            "labels": list(self.labels),
            "counts": [int(c) for c in counts],
            "empty_bins": [self.labels[i] for i, c in enumerate(counts) if c == 0],
            "spec": self.spec,
        }


def _as_float_array(values) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _numeric_missing(values) -> np.ndarray:
    arr = _as_float_array(values)
    return ~np.isfinite(arr)


def _object_missing(values) -> np.ndarray:
    return np.array(
        [v is None or (isinstance(v, float) and not np.isfinite(v)) or v == "" for v in values],
        dtype=bool,
    )


def _check_non_empty(mask: np.ndarray, name: str) -> None:
    if int(np.count_nonzero(~mask)) == 0:
        raise ValueError(f"variable {name!r} has no usable observations")


def categorical(values, name: str, order: list[str] | None = None) -> Discretized:
    """Map labels to codes using a declared or sorted order."""
    seq = list(values)
    if len(seq) == 0:
        raise ValueError(f"variable {name!r} is empty")
    missing = _object_missing(seq)
    _check_non_empty(missing, name)
    present = [v for v, m in zip(seq, missing) if not m]
    labels = tuple(order) if order is not None else tuple(sorted(set(present)))
    unknown = sorted(set(present) - set(labels))
    if unknown:
        raise ValueError(f"variable {name!r} contains undeclared labels {unknown}")
    index = {label: i for i, label in enumerate(labels)}
    codes = np.array([MISSING if m else index[v] for v, m in zip(seq, missing)], dtype=np.int64)
    spec = {"name": name, "kind": "categorical", "declared_order": list(labels)}
    return Discretized(codes, labels, spec, int(missing.sum()))


def ordinal_thresholds(values, thresholds, name: str) -> Discretized:
    """Split a numeric variable at declared cut points.

    ``thresholds`` are upper bounds: code 0 means ``x <= thresholds[0]``.
    """
    arr = _as_float_array(values)
    missing = ~np.isfinite(arr)
    _check_non_empty(missing, name)
    cuts = [float(t) for t in thresholds]
    if cuts != sorted(cuts) or len(set(cuts)) != len(cuts):
        raise ValueError("thresholds must be strictly increasing")
    codes = np.full(arr.shape, MISSING, dtype=np.int64)
    usable = ~missing
    codes[usable] = np.searchsorted(np.asarray(cuts), arr[usable], side="left")
    labels = [f"<= {cuts[0]:g}"]
    for lower, upper in zip(cuts[:-1], cuts[1:]):
        labels.append(f"({lower:g}, {upper:g}]")
    labels.append(f"> {cuts[-1]:g}")
    spec = {"name": name, "kind": "ordinal_thresholds", "thresholds": cuts}
    return Discretized(codes, tuple(labels), spec, int(missing.sum()))


def equal_width(values, bins: int, name: str, low=None, high=None) -> Discretized:
    """Equal-width binning on the observed range or a declared range."""
    if int(bins) < 2:
        raise ValueError("equal_width needs at least two bins")
    arr = _as_float_array(values)
    missing = ~np.isfinite(arr)
    _check_non_empty(missing, name)
    usable = arr[~missing]
    lo = float(usable.min()) if low is None else float(low)
    hi = float(usable.max()) if high is None else float(high)
    if not hi > lo:
        raise ValueError(f"variable {name!r} has a degenerate range")
    edges = np.linspace(lo, hi, int(bins) + 1)
    codes = np.full(arr.shape, MISSING, dtype=np.int64)
    inner = np.clip(np.searchsorted(edges, arr[~missing], side="right") - 1, 0, int(bins) - 1)
    codes[~missing] = inner
    last = int(bins) - 1
    labels = tuple(
        f"[{edges[i]:.6g}, {edges[i + 1]:.6g}{']' if i == last else ')'}"
        for i in range(int(bins))
    )
    spec = {
        "name": name,
        "kind": "equal_width",
        "bins": int(bins),
        "range": [lo, hi],
        "edges": [float(e) for e in edges],
    }
    return Discretized(codes, labels, spec, int(missing.sum()))


def quantile(values, bins: int, name: str) -> Discretized:
    """Quantile binning with ties assigned to the lower bin."""
    if int(bins) < 2:
        raise ValueError("quantile binning needs at least two bins")
    arr = _as_float_array(values)
    missing = ~np.isfinite(arr)
    _check_non_empty(missing, name)
    usable = arr[~missing]
    edges = np.unique(np.quantile(usable, np.linspace(0.0, 1.0, int(bins) + 1)))
    if edges.size < 3:
        raise ValueError(f"variable {name!r} has too few distinct values for {bins} bins")
    codes = np.full(arr.shape, MISSING, dtype=np.int64)
    codes[~missing] = np.clip(np.searchsorted(edges, arr[~missing], side="right") - 1, 0, edges.size - 2)
    labels = tuple(f"q{i}" for i in range(edges.size - 1))
    spec = {
        "name": name,
        "kind": "quantile",
        "requested_bins": int(bins),
        "effective_bins": int(edges.size - 1),
        "edges": [float(e) for e in edges],
    }
    return Discretized(codes, labels, spec, int(missing.sum()))


def count_capped(values, cap: int, name: str) -> Discretized:
    """Ordinal count code where every value >= cap shares the top bin."""
    if int(cap) < 1:
        raise ValueError("cap must be at least one")
    arr = _as_float_array(values)
    missing = ~np.isfinite(arr)
    _check_non_empty(missing, name)
    codes = np.full(arr.shape, MISSING, dtype=np.int64)
    codes[~missing] = np.clip(arr[~missing], 0, int(cap)).astype(np.int64)
    labels = [str(i) for i in range(int(cap))] + [f">= {int(cap)}"]
    spec = {"name": name, "kind": "count_capped", "cap": int(cap)}
    return Discretized(codes, labels, spec, int(missing.sum()))


def declared(codes, labels, name: str) -> Discretized:
    """Wrap already-coded values with a declared level list.

    Needed when a code comes straight from an archived label column rather
    than from a transform here; the declared order keeps ``k`` fixed so that
    an unobserved level still counts toward the maximum entropy.
    """
    arr = np.asarray(codes, dtype=np.int64)
    unknown = int(arr[arr >= len(labels)].max()) if np.any(arr >= len(labels)) else -1
    if unknown >= 0:
        raise ValueError(f"variable {name!r} has code {unknown} outside declared levels")
    mask = arr >= 0
    return Discretized(
        arr,
        tuple(labels),
        {"name": name, "kind": "declared"},
        int(arr.size - np.count_nonzero(mask)),
    )
