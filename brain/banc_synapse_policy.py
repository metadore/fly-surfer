"""Transmitter-sign and edge-weight policy for the BANC simulation pathway.

BANC ships verified and predicted transmitter annotations but no per-edge sign,
no ``nt_code`` and no ``vocabulary``. This module turns node annotations into an
explicit, auditable sign prior and turns integer synapse counts into synaptic
current weights.

Nothing here is physiological: a sign is a modelling prior, and a weight is a
transformation of a structural synapse count, not a conductance.

Primary policy (see ``configs/banc_synapse_policy.yaml``):

* only verified transmitter labels may carry a sign;
* acetylcholine and glutamate are excitatory priors, GABA and glycine are
  inhibitory priors;
* verified labels that contain both classes are a conflict and stay unknown;
* verified labels that contain only neuromodulators (dopamine, serotonin,
  octopamine, tyramine, histamine, nitric oxide) stay unknown;
* predicted labels are a sensitivity condition, never part of the primary
  policy;
* edges from unknown-sign neurons are excluded from the primary simulation and
  counted explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

# Sign classes. Codes are persisted in results, so they must stay stable.
UNANNOTATED = 0
VERIFIED_EXCITATORY = 1
VERIFIED_INHIBITORY = 2
VERIFIED_CONFLICT = 3
VERIFIED_MODULATOR_ONLY = 4
PREDICTED_EXCITATORY = 5
PREDICTED_INHIBITORY = 6
PREDICTED_CONFLICT = 7
PREDICTED_MODULATOR_ONLY = 8

CLASS_NAMES = {
    UNANNOTATED: "unannotated",
    VERIFIED_EXCITATORY: "verified_excitatory",
    VERIFIED_INHIBITORY: "verified_inhibitory",
    VERIFIED_CONFLICT: "verified_conflict",
    VERIFIED_MODULATOR_ONLY: "verified_modulator_only",
    PREDICTED_EXCITATORY: "predicted_excitatory",
    PREDICTED_INHIBITORY: "predicted_inhibitory",
    PREDICTED_CONFLICT: "predicted_conflict",
    PREDICTED_MODULATOR_ONLY: "predicted_modulator_only",
}

DEFAULT_EXCITATORY = ("acetylcholine", "glutamate")
DEFAULT_INHIBITORY = ("gaba", "glycine")
DEFAULT_MODULATORS = (
    "dopamine",
    "serotonin",
    "octopamine",
    "tyramine",
    "histamine",
    "nitric_oxide",
)
_TRANSFORMS = ("power", "linear", "log1p")
_UNKNOWN_POLICIES = ("exclude", "zero")


@dataclass(frozen=True)
class SignPolicy:
    """Explicit rules that map a transmitter label to a sign prior."""

    verified_excitatory: tuple[str, ...] = DEFAULT_EXCITATORY
    verified_inhibitory: tuple[str, ...] = DEFAULT_INHIBITORY
    modulators: tuple[str, ...] = DEFAULT_MODULATORS
    conflict_policy: str = "unknown"
    modulator_only_policy: str = "unknown"
    predicted_fallback: bool = False
    unknown_edge_policy: str = "exclude"

    def __post_init__(self) -> None:
        for name in (
            "verified_excitatory",
            "verified_inhibitory",
            "modulators",
        ):
            values = tuple(str(value).strip().lower() for value in getattr(self, name))
            if not values or any(not value for value in values):
                raise ValueError(f"{name} must be a non-empty list of labels")
            object.__setattr__(self, name, values)
        overlap = set(self.verified_excitatory) & set(self.verified_inhibitory)
        if overlap:
            raise ValueError(
                f"a transmitter cannot be both excitatory and inhibitory: {sorted(overlap)}"
            )
        if self.conflict_policy != "unknown":
            raise ValueError("conflict_policy must be 'unknown'")
        if self.modulator_only_policy != "unknown":
            raise ValueError("modulator_only_policy must be 'unknown'")
        if not isinstance(self.predicted_fallback, (bool, np.bool_)):
            raise ValueError("predicted_fallback must be a boolean")
        object.__setattr__(self, "predicted_fallback", bool(self.predicted_fallback))
        if self.unknown_edge_policy not in _UNKNOWN_POLICIES:
            raise ValueError(
                f"unknown_edge_policy must be one of {_UNKNOWN_POLICIES}"
            )

    @classmethod
    def from_config(cls, payload: Mapping) -> "SignPolicy":
        values = {
            key: value
            for key, value in payload.items()
            if key in cls.__dataclass_fields__
        }
        for name in ("verified_excitatory", "verified_inhibitory", "modulators"):
            if name in values:
                values[name] = tuple(str(value) for value in values[name])
        return cls(**values)

    def describe(self) -> dict:
        return {
            "verified_excitatory": list(self.verified_excitatory),
            "verified_inhibitory": list(self.verified_inhibitory),
            "modulators_without_fixed_sign": list(self.modulators),
            "conflict_policy": self.conflict_policy,
            "modulator_only_policy": self.modulator_only_policy,
            "predicted_fallback": bool(self.predicted_fallback),
            "unknown_edge_policy": self.unknown_edge_policy,
            "interpretation": (
                "excitatory and inhibitory are modelling priors applied to the "
                "presynaptic neuron; they are not established postsynaptic "
                "effects at every target"
            ),
        }


@dataclass(frozen=True)
class WeightPolicy:
    """Structural count to synaptic current weight transformation."""

    transform: str = "power"
    exponent: float = 0.75
    scale_pa: float = 5.0
    cap_pa: float | None = 300.0

    def __post_init__(self) -> None:
        if self.transform not in _TRANSFORMS:
            raise ValueError(f"transform must be one of {_TRANSFORMS}")
        if not np.isfinite(self.exponent) or self.exponent <= 0:
            raise ValueError("exponent must be positive and finite")
        if not np.isfinite(self.scale_pa) or self.scale_pa < 0:
            raise ValueError("scale_pa must be non-negative and finite")
        if self.cap_pa is not None:
            cap = float(self.cap_pa)
            if not np.isfinite(cap) or cap <= 0:
                raise ValueError("cap_pa must be positive and finite")
            object.__setattr__(self, "cap_pa", cap)

    @classmethod
    def from_config(cls, payload: Mapping) -> "WeightPolicy":
        return cls(**dict(payload))

    def describe(self) -> dict:
        return {
            "transform": self.transform,
            "exponent": float(self.exponent),
            "scale_pa": float(self.scale_pa),
            "cap_pa": None if self.cap_pa is None else float(self.cap_pa),
            "weight_source": "integer synapse count (`count`); `norm` is never used",
            "interpretation": (
                "weights are structural synapse counts raised to a monotone "
                "transform and scaled to pA; they are not conductances"
            ),
        }

    def apply(self, counts: np.ndarray) -> np.ndarray:
        base = np.asarray(counts, dtype=np.float32)
        if self.transform == "power":
            weights = np.power(base, np.float32(self.exponent))
        elif self.transform == "log1p":
            weights = np.log1p(base)
        else:
            weights = base.copy()
        weights *= np.float32(self.scale_pa)
        if self.cap_pa is not None:
            np.minimum(weights, np.float32(self.cap_pa), out=weights)
        return weights


def _tokens(label) -> tuple[str, ...]:
    if label is None:
        return ()
    try:
        if pd.isna(label):
            return ()
    except (TypeError, ValueError):
        pass
    text = str(label).strip().lower()
    if not text or text in {"nan", "none", "<na>", "unknown"}:
        return ()
    return tuple(
        sorted({part.strip() for part in text.split(",") if part.strip()})
    )


def _sign_of(tokens: tuple[str, ...], policy: SignPolicy) -> int:
    excitatory = set(tokens) & set(policy.verified_excitatory)
    inhibitory = set(tokens) & set(policy.verified_inhibitory)
    if excitatory and inhibitory:
        return 0
    if excitatory:
        return 1
    if inhibitory:
        return -1
    return 0


def classify_labels(
    verified: pd.Series, predicted: pd.Series, policy: SignPolicy
) -> np.ndarray:
    """Return one sign class code per neuron."""
    verified = verified.astype("string")
    predicted = predicted.astype("string")
    codes = np.full(len(verified), UNANNOTATED, dtype=np.int8)
    for index in range(len(codes)):
        verified_tokens = _tokens(verified.iloc[index])
        predicted_tokens = _tokens(predicted.iloc[index])
        if verified_tokens:
            sign = _sign_of(verified_tokens, policy)
            if sign > 0:
                codes[index] = VERIFIED_EXCITATORY
            elif sign < 0:
                codes[index] = VERIFIED_INHIBITORY
            elif set(verified_tokens) & (
                set(policy.verified_excitatory) | set(policy.verified_inhibitory)
            ):
                codes[index] = VERIFIED_CONFLICT
            else:
                codes[index] = VERIFIED_MODULATOR_ONLY
            continue
        if not policy.predicted_fallback or not predicted_tokens:
            continue
        sign = _sign_of(predicted_tokens, policy)
        if sign > 0:
            codes[index] = PREDICTED_EXCITATORY
        elif sign < 0:
            codes[index] = PREDICTED_INHIBITORY
        elif set(predicted_tokens) & (
            set(policy.verified_excitatory) | set(policy.verified_inhibitory)
        ):
            codes[index] = PREDICTED_CONFLICT
        else:
            codes[index] = PREDICTED_MODULATOR_ONLY
    return codes


def sign_values(codes: np.ndarray, policy: SignPolicy) -> np.ndarray:
    """Map sign classes to +1, -1 or 0, honouring the predicted fallback."""
    signs = np.zeros(len(codes), dtype=np.int8)
    signs[codes == VERIFIED_EXCITATORY] = 1
    signs[codes == VERIFIED_INHIBITORY] = -1
    if policy.predicted_fallback:
        signs[codes == PREDICTED_EXCITATORY] = 1
        signs[codes == PREDICTED_INHIBITORY] = -1
    return signs


@dataclass
class BancSynapsePolicy:
    """Signed edge weights for one threshold graph under one policy."""

    threshold: int
    sign_policy: SignPolicy
    weight_policy: WeightPolicy
    neuron_codes: np.ndarray
    neuron_signs: np.ndarray
    edge_exc_weight: np.ndarray
    edge_inh_weight: np.ndarray
    coverage: dict
    provenance: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.neuron_codes)
        m = len(self.edge_exc_weight)
        if self.neuron_signs.shape != (n,):
            raise ValueError("neuron_signs must match neuron_codes")
        if self.edge_inh_weight.shape != (m,):
            raise ValueError("excitatory and inhibitory edge arrays must match")
        if not np.all(np.isfinite(self.edge_exc_weight)):
            raise ValueError("non-finite excitatory weights")
        if not np.all(np.isfinite(self.edge_inh_weight)):
            raise ValueError("non-finite inhibitory weights")
        if np.any(self.edge_exc_weight < 0) or np.any(self.edge_inh_weight < 0):
            raise ValueError("edge weights cannot be negative")

    @property
    def n_neurons(self) -> int:
        return int(len(self.neuron_codes))

    @property
    def n_edges(self) -> int:
        return int(len(self.edge_exc_weight))

    @property
    def signed_edges(self) -> int:
        return int(
            np.count_nonzero(self.edge_exc_weight)
            + np.count_nonzero(self.edge_inh_weight)
        )

    @property
    def memory_bytes(self) -> int:
        return int(
            self.neuron_codes.nbytes
            + self.neuron_signs.nbytes
            + self.edge_exc_weight.nbytes
            + self.edge_inh_weight.nbytes
        )

    def describe(self) -> dict:
        return {
            "graph_threshold": int(self.threshold),
            "sign_policy": self.sign_policy.describe(),
            "weight_policy": self.weight_policy.describe(),
            "coverage": self.coverage,
            "edge_arrays": {
                "excitatory_edges": int(np.count_nonzero(self.edge_exc_weight)),
                "inhibitory_edges": int(np.count_nonzero(self.edge_inh_weight)),
                "signed_edges": int(self.signed_edges),
                "excluded_edges": int(self.n_edges - self.signed_edges),
                "excitatory_weight_sum_pa": round(
                    float(self.edge_exc_weight.sum(dtype=np.float64)), 4
                ),
                "inhibitory_weight_sum_pa": round(
                    float(self.edge_inh_weight.sum(dtype=np.float64)), 4
                ),
                "max_edge_weight_pa": round(
                    float(
                        max(
                            self.edge_exc_weight.max(initial=0.0),
                            self.edge_inh_weight.max(initial=0.0),
                        )
                    ),
                    4,
                ),
                "memory_bytes": int(self.memory_bytes),
            },
            "provenance": self.provenance,
        }


def build_synapse_policy(
    graph,
    node_table: pd.DataFrame,
    sign_policy: SignPolicy,
    weight_policy: WeightPolicy,
) -> BancSynapsePolicy:
    """Build signed edge weights without changing the graph artifact."""
    n = int(graph.n_nodes)
    if len(node_table) != n:
        raise ValueError("node table and graph node counts differ")
    if "neurotransmitter_verified" not in node_table.columns:
        raise ValueError("node table has no neurotransmitter_verified column")
    if "neurotransmitter_predicted" not in node_table.columns:
        raise ValueError("node table has no neurotransmitter_predicted column")
    table_ids = node_table["banc_888_id"].to_numpy().astype(np.int64)
    if not np.array_equal(table_ids, np.asarray(graph.root_ids, dtype=np.int64)):
        raise ValueError(
            "node table banc_888_id order does not match the graph root_ids"
        )

    codes = classify_labels(
        node_table["neurotransmitter_verified"],
        node_table["neurotransmitter_predicted"],
        sign_policy,
    )
    signs = sign_values(codes, sign_policy)

    counts = np.asarray(graph.edge_weight)
    weights = weight_policy.apply(counts)
    edge_signs = signs[np.asarray(graph.edge_src, dtype=np.int64)]
    exc = np.where(edge_signs > 0, weights, np.float32(0.0)).astype(np.float32)
    inh = np.where(edge_signs < 0, weights, np.float32(0.0)).astype(np.float32)
    if sign_policy.unknown_edge_policy == "zero":
        # Numerically identical to exclusion: unknown edges carry zero current.
        pass

    edge_codes = codes[np.asarray(graph.edge_src, dtype=np.int64)]
    total_edges = int(graph.n_edges)
    total_synapses = int(np.asarray(graph.edge_weight, dtype=np.int64).sum())
    by_class = {}
    for code, name in CLASS_NAMES.items():
        mask = edge_codes == code
        edges = int(np.count_nonzero(mask))
        synapses = int(np.asarray(graph.edge_weight, dtype=np.int64)[mask].sum())
        neurons = int(np.count_nonzero(codes == code))
        by_class[name] = {
            "neurons": neurons,
            "edges": edges,
            "synapses": synapses,
            "edge_share": round(edges / total_edges, 6) if total_edges else 0.0,
            "synapse_share": (
                round(synapses / total_synapses, 6) if total_synapses else 0.0
            ),
        }
    signed_mask = edge_signs != 0
    coverage = {
        "declared_policy": "verified-only" if not sign_policy.predicted_fallback else "verified-then-predicted",
        "total_neurons": n,
        "total_edges": total_edges,
        "total_synapses": total_synapses,
        "signed_edges": int(np.count_nonzero(signed_mask)),
        "signed_synapses": int(
            np.asarray(graph.edge_weight, dtype=np.int64)[signed_mask].sum()
        ),
        "excluded_edges": int(total_edges - np.count_nonzero(signed_mask)),
        "excluded_synapses": int(
            np.asarray(graph.edge_weight, dtype=np.int64)[~signed_mask].sum()
        ),
        "signed_edge_share": round(
            float(np.count_nonzero(signed_mask)) / max(1, total_edges), 6
        ),
        "signed_synapse_share": round(
            float(
                np.asarray(graph.edge_weight, dtype=np.int64)[signed_mask].sum()
            )
            / max(1, total_synapses),
            6,
        ),
        "by_class": by_class,
    }
    provenance = {
        "graph_threshold": int(getattr(graph, "threshold", -1)),
        "node_table": "datasets/processed/banc_v888/banc_nodes.csv.gz",
        "node_order": "ascending banc_888_id, identical to graph root_ids",
        "edges_modified": False,
        "unknown_edges": (
            "excluded from propagation; they contribute zero current"
            if sign_policy.unknown_edge_policy == "exclude"
            else "retained with zero current"
        ),
    }
    return BancSynapsePolicy(
        threshold=int(getattr(graph, "threshold", -1)),
        sign_policy=sign_policy,
        weight_policy=weight_policy,
        neuron_codes=codes,
        neuron_signs=signs,
        edge_exc_weight=exc,
        edge_inh_weight=inh,
        coverage=coverage,
        provenance=provenance,
    )
