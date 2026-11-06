"""Deterministic mapping from sensory features to neuron populations.

Populations are selected from FlyWire *predicted* annotations carried by the
validated connectome artifact (super-class, class, side, neurotransmitter).
Selecting a `class=visual` neuron does not establish that it carries the
feature assigned to it here. Every population is therefore reported as an
experimental input population drawn from a predicted annotation pool.

Selection is seeded and allocation is disjoint by default: each neuron index
belongs to at most one feature population. No root IDs are hard-coded.
"""

from __future__ import annotations

import numpy as np

FILTER_FIELDS = {
    "super_class": ("super_class_code", "super_class"),
    "class": ("class_code", "class"),
    "side": ("side_code", "side"),
    "nt_type": ("nt_code", "nt_type"),
}

CLASSIFICATION = (
    "experimental input population drawn from predicted FlyWire annotations; "
    "the feature assignment is not an anatomically verified sensory pathway"
)

LIMITATIONS = (
    "Predicted cell-type annotations, not verified connectivity or physiology. "
    "The mapping is an experimental interface for delivering structured input, "
    "not a claim about how the fly encodes this feature."
)


class AnnotationFilter:
    """AND across fields, OR within a field's label list."""

    def __init__(self, payload: dict) -> None:
        if not isinstance(payload, dict) or not payload:
            raise ValueError("a pool filter must be a non-empty mapping")
        unknown = set(payload) - set(FILTER_FIELDS)
        if unknown:
            raise ValueError(
                f"unknown annotation fields {sorted(unknown)}; "
                f"expected {sorted(FILTER_FIELDS)}"
            )
        self.payload = {
            field: [str(label) for label in labels]
            for field, labels in payload.items()
        }
        for field, labels in self.payload.items():
            if not labels:
                raise ValueError(f"annotation field {field!r} has no labels")

    def mask(self, graph) -> np.ndarray:
        mask = np.ones(graph.n_nodes, dtype=bool)
        for field, labels in self.payload.items():
            code_attr, vocabulary_key = FILTER_FIELDS[field]
            vocabulary = graph.vocabulary.get(vocabulary_key, [])
            codes = []
            for label in labels:
                if label not in vocabulary:
                    raise ValueError(
                        f"unknown {field} label {label!r}; "
                        f"available labels are {sorted(vocabulary)}"
                    )
                codes.append(vocabulary.index(label))
            mask &= np.isin(getattr(graph, code_attr), codes)
        return mask

    def describe(self) -> dict:
        return dict(self.payload)


class PopulationPlan:
    """How one feature's neurons are allocated from annotation pools."""

    def __init__(self, feature: str, payload: dict) -> None:
        if not isinstance(payload, dict):
            raise ValueError(f"population {feature!r} must be a mapping")
        self.feature = feature
        if "lane_pools" in payload:
            lane_pools = payload["lane_pools"]
            if not isinstance(lane_pools, dict):
                raise ValueError("lane_pools must be a mapping")
            if len(lane_pools) < 2:
                raise ValueError("lane_pools must define at least two groups")
            self.neurons_per_lane = int(payload.get("neurons_per_lane", 0))
            if self.neurons_per_lane < 1:
                raise ValueError("neurons_per_lane must be positive")
            # Group order is lane-code order: the i-th entry feeds encoder lane i.
            self.groups = [
                (str(name), str(pool), self.neurons_per_lane)
                for name, pool in lane_pools.items()
            ]
            self.kind = "lane"
        else:
            pool = payload.get("pool")
            n_neurons = int(payload.get("n_neurons", 0))
            if not pool or n_neurons < 1:
                raise ValueError(
                    f"population {feature!r} requires pool and n_neurons"
                )
            self.groups = [("default", str(pool), n_neurons)]
            self.kind = "scalar"

    @property
    def size(self) -> int:
        return sum(count for _, _, count in self.groups)

    def describe(self) -> dict:
        if self.kind == "lane":
            return {
                "kind": self.kind,
                "lane_pools": {name: pool for name, pool, _ in self.groups},
                "neurons_per_lane": self.neurons_per_lane,
                "n_neurons": self.size,
            }
        return {
            "kind": self.kind,
            "pool": self.groups[0][1],
            "n_neurons": self.size,
        }


class NeuralPopulation:
    """Selected local indices and root IDs for one feature."""

    def __init__(
        self,
        feature: str,
        plan: PopulationPlan,
        groups: dict[str, np.ndarray],
        pool_filters: dict[str, AnnotationFilter],
        graph,
    ) -> None:
        self.feature = feature
        self.plan = plan
        self.groups = groups
        self.pool_filters = pool_filters
        self.root_ids = {
            name: graph.root_ids[indices] for name, indices in groups.items()
        }
        self._indices = np.concatenate(
            [groups[name] for name, _, _ in plan.groups]
        )

    @property
    def indices(self) -> np.ndarray:
        return self._indices

    def size(self) -> int:
        return int(self._indices.size)

    def evidence(self, graph) -> dict:
        evidence = {}
        for name, indices in self.groups.items():
            evidence[name] = _annotation_counts(graph, indices)
        return evidence

    def report(self, graph) -> dict:
        payload = {
            "feature": self.feature,
            "planned_size": self.plan.size,
            "selected_size": self.size(),
            "plan": self.plan.describe(),
            "pool_filters": {
                pool: self.pool_filters[pool].describe()
                for pool in sorted({pool for _, pool, _ in self.plan.groups})
            },
            "selection_method": (
                "seeded permutation of the annotation pool; first unused indices "
                "in permutation order; disjoint across features unless allowed"
            ),
            "classification": CLASSIFICATION,
            "evidence": self.evidence(graph),
            "limitations": LIMITATIONS,
            "groups": {
                name: {
                    "pool": pool,
                    "n_neurons": int(len(self.groups[name])),
                    "root_ids": [int(value) for value in self.root_ids[name]],
                }
                for name, pool, _ in self.plan.groups
            },
        }
        return payload


def _annotation_counts(graph, indices: np.ndarray) -> dict:
    payload = {}
    for field, (code_attr, vocabulary_key) in FILTER_FIELDS.items():
        vocabulary = graph.vocabulary.get(vocabulary_key, [])
        codes = np.asarray(getattr(graph, code_attr))[indices]
        counts: dict[str, int] = {}
        for code in np.unique(codes):
            label = (
                vocabulary[int(code)]
                if 0 <= int(code) < len(vocabulary)
                else "unlabeled"
            )
            counts[label] = int(np.count_nonzero(codes == code))
        payload[field] = counts
    return payload


class SensoryMapping:
    """Build and validate every feature population for one graph."""

    def __init__(self, graph, config: dict) -> None:
        if not isinstance(config, dict):
            raise ValueError("mapping configuration must be a mapping")
        self.graph = graph
        self.seed = int(config.get("seed", 0))
        self.allow_duplicates = bool(config.get("allow_duplicates", False))
        pools = config.get("pools")
        populations = config.get("populations")
        if not isinstance(pools, dict) or not pools:
            raise ValueError("mapping.pools must be a non-empty mapping")
        if not isinstance(populations, dict) or not populations:
            raise ValueError("mapping.populations must be a non-empty mapping")
        self.pools = {
            name: AnnotationFilter(payload) for name, payload in pools.items()
        }
        self._pool_masks: dict[str, np.ndarray] = {}
        self._pool_orders: dict[str, np.ndarray] = {}
        self._rng = np.random.default_rng(self.seed)
        self._used: set[int] = set()

        self.populations: dict[str, NeuralPopulation] = {}
        for feature, payload in populations.items():
            plan = PopulationPlan(feature, payload)
            for _, pool, _ in plan.groups:
                if pool not in self.pools:
                    raise ValueError(
                        f"population {feature!r} references unknown pool {pool!r}"
                    )
            groups = {
                name: self._choose(pool, count)
                for name, pool, count in plan.groups
            }
            self.populations[feature] = NeuralPopulation(
                feature, plan, groups, self.pools, graph
            )
        self.validate()

    def _pool(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        if name not in self._pool_masks:
            mask = self.pools[name].mask(self.graph)
            if not mask.any():
                raise ValueError(f"annotation pool {name!r} selects no neurons")
            indices = np.flatnonzero(mask)
            self._pool_masks[name] = indices
            self._pool_orders[name] = self._rng.permutation(len(indices))
        return self._pool_masks[name], self._pool_orders[name]

    def _choose(self, pool: str, count: int) -> np.ndarray:
        indices, order = self._pool(pool)
        candidates = indices[order]
        if not self.allow_duplicates:
            candidates = np.array(
                [index for index in candidates if int(index) not in self._used],
                dtype=np.int64,
            )
        if candidates.size < count:
            raise ValueError(
                f"annotation pool {pool!r} has {candidates.size} unused neurons; "
                f"requested {count}"
            )
        chosen = np.asarray(candidates[:count], dtype=np.int64)
        if not self.allow_duplicates:
            self._used.update(int(index) for index in chosen)
        return chosen

    def validate(self) -> None:
        if not self.allow_duplicates:
            seen: set[int] = set()
            for population in self.populations.values():
                for index in population.indices:
                    key = int(index)
                    if key in seen:
                        raise ValueError(
                            f"neuron index {key} assigned to multiple features "
                            "without allow_duplicates"
                        )
                    seen.add(key)
        for population in self.populations.values():
            if population.size() != population.plan.size:
                raise ValueError(
                    f"population {population.feature!r} has {population.size()} "
                    f"neurons; plan requires {population.plan.size}"
                )
            if population.indices.min() < 0 or population.indices.max() >= self.graph.n_nodes:
                raise ValueError("mapped index outside the graph")

    def indices(self, feature: str) -> np.ndarray:
        return self.populations[feature].indices

    def size(self, feature: str) -> int:
        return self.populations[feature].size()

    def stimulated_indices(self) -> np.ndarray:
        chunks = [population.indices for population in self.populations.values()]
        return np.unique(np.concatenate(chunks))

    def report(self) -> dict:
        return {
            "seed": self.seed,
            "allow_duplicates": self.allow_duplicates,
            "n_features": len(self.populations),
            "n_stimulated_neurons": int(self.stimulated_indices().size),
            "populations": {
                feature: population.report(self.graph)
                for feature, population in self.populations.items()
            },
        }
