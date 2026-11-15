"""Phase 4H.4: event-pulsed sensory drive for the BANC simulator.

This module is a standalone bridge between archived perception events and the
unchanged ``BancSimulator`` input-schedule contract
(``apply(step, time_ms, current_pa)`` and ``stimulated_indices``). It does not
modify perception, the Phase 3 sensory pipeline or the simulator.

Two pieces are provided:

``BancSensoryMapping``
    Selects experimental input populations from *published* BANC v888
    annotation columns only. Motor neurons and the LEFT/RIGHT/JUMP masks are
    excluded before selection and the exclusion is asserted. Selection is
    seeded and disjoint across feature groups by default.

``BancEventDrive``
    Turns archived event dictionaries into decaying current pulses. Every
    event that carries feature values contributes an encoded response scaled
    by the feature amplitude and decaying linearly over ``decay_ms``. No held
    per-frame state is used because the archived replay exposes events, not
    per-frame ``GameState`` features. This is recorded as a limitation.

Nothing here claims a measured sensory pathway, a receptive field, or a
biological meaning for a game feature. A visual annotation is not evidence of a
direct visual pathway to motor control, and no FAFB root ID is transferred.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math

import numpy as np

from sensory.population_encoder import encode_state

FILTER_FIELDS = (
    "super_class",
    "cell_class",
    "cell_function",
    "body_part_sensory",
    "peripheral_target_type",
    "region",
    "flow",
    "side",
)
UNASSIGNED_LABEL = "unassigned"
EVENT_KINDS = (
    "appeared",
    "approaching",
    "receding",
    "disappeared",
    "occluded",
    "uncertain",
)
REQUIRED_EVENT_FIELDS = (
    "frame_index",
    "frame_id",
    "track_id",
    "event",
    "class_name",
    "lane",
    "time_ms",
    "confidence",
    "distance_proxy",
    "is_pulse",
    "feature_values",
)
IDENTITY_FIELDS = (
    "frame_index",
    "frame_id",
    "track_id",
    "event",
    "class_name",
    "lane",
    "time_ms",
    "confidence",
    "distance_proxy",
    "is_pulse",
)

CLASSIFICATION = (
    "experimental input population selected from published BANC annotation "
    "columns; the feature assignment is a hypothesis, not a verified sensory "
    "pathway"
)

LIMITATIONS = [
    "Annotation-defined populations, not measured sensory anatomy or "
    "physiology.",
    "The feature assignment is a hypothesis; a visual annotation is not "
    "evidence of a direct visual pathway to motor control.",
    "No held per-frame state exists for the archived events; drive is carried "
    "by discrete event pulses only.",
    "No FAFB root ID is transferred; FAFB and BANC identities are never "
    "merged.",
]


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


def _digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(np.ascontiguousarray(array).tobytes())
        digest.update(b"|")
    return digest.hexdigest()


def canonical_event_metadata(events) -> list:
    """Identity fields of every event, in order, with stable rounding."""
    rows = []
    for event in events:
        row = []
        for field in IDENTITY_FIELDS:
            value = event.get(field)
            if isinstance(value, float):
                value = round(value, 6)
            row.append(value)
        rows.append(row)
    return rows


def event_metadata_digest(events) -> str:
    payload = json.dumps(
        canonical_event_metadata(events), sort_keys=True, allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_events(events, *, features, require_sorted: bool = True) -> list:
    """Copy and validate archived events; never mutate the input."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a list of dictionaries")
    known = set(features)
    validated: list[dict] = []
    previous = None
    for position, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"event {position} is not a dictionary")
        missing = [name for name in REQUIRED_EVENT_FIELDS if name not in event]
        if missing:
            raise ValueError(f"event {position} is missing fields {missing}")
        kind = event["event"]
        if kind not in EVENT_KINDS:
            raise ValueError(
                f"event {position} has unknown kind {kind!r}; "
                f"expected one of {list(EVENT_KINDS)}"
            )
        time_ms = _non_negative(event["time_ms"], f"event {position} time_ms")
        if previous is not None and time_ms < previous - 1e-9:
            if require_sorted:
                raise ValueError(
                    "event timestamps must be non-decreasing; "
                    f"event {position} at {time_ms} follows {previous}"
                )
        previous = max(previous, time_ms) if previous is not None else time_ms
        values = event["feature_values"]
        if not isinstance(values, dict):
            raise ValueError(f"event {position} feature_values must be a mapping")
        unknown = set(values) - known
        if unknown:
            raise ValueError(
                f"event {position} references unknown features {sorted(unknown)}"
            )
        if not isinstance(event["is_pulse"], bool):
            raise ValueError(f"event {position} is_pulse must be a boolean")
        lane = event["lane"]
        if lane is not None and (
            isinstance(lane, bool) or not isinstance(lane, int)
        ):
            raise ValueError(f"event {position} lane must be an integer or null")
        copy = dict(event)
        copy["time_ms"] = time_ms
        copy["feature_values"] = dict(values)
        validated.append(copy)
    return validated


class MappedPopulation:
    """One feature's selected indices, in encoder output order."""

    def __init__(
        self,
        feature: str,
        groups: dict[str, np.ndarray],
        *,
        evidence: str,
        hypothesis: str,
        statement: str,
        pool_mode: str,
    ) -> None:
        self.feature = feature
        self.groups = groups
        self.evidence = evidence
        self.hypothesis = hypothesis
        self.statement = statement
        self.pool_mode = pool_mode
        self._indices = np.concatenate([groups[name] for name in groups])

    @property
    def indices(self) -> np.ndarray:
        return self._indices

    def size(self) -> int:
        return int(self._indices.size)

    def report(self, graph, nodes, annotation_fields) -> dict:
        payload = {
            "feature": self.feature,
            "selected_size": self.size(),
            "evidence": self.evidence,
            "hypothesis": self.hypothesis,
            "statement": self.statement,
            "pool_mode": self.pool_mode,
            "groups": {
                name: {
                    "n_neurons": int(index.size),
                    "root_ids": [int(value) for value in graph.root_ids[index]],
                }
                for name, index in self.groups.items()
            },
            "annotation_composition": {
                field: _label_counts(nodes, field, self._indices)
                for field in annotation_fields
            },
        }
        return payload


def _label_counts(nodes, field: str, indices: np.ndarray) -> dict:
    values = (
        nodes[field]
        .fillna("")
        .astype(str)
        .to_numpy()[np.asarray(indices, dtype=np.int64)]
    )
    counts: dict[str, int] = {}
    for value in values:
        label = value if value else UNASSIGNED_LABEL
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


class BancSensoryMapping:
    """Seeded, motor-excluded feature mapping over BANC annotations."""

    def __init__(
        self,
        nodes,
        graph,
        config: dict,
        *,
        motor_mask,
        action_masks: dict | None = None,
        randomise_pools: bool = False,
    ) -> None:
        if not isinstance(config, dict):
            raise ValueError("mapping configuration must be a mapping")
        if len(nodes) != int(graph.n_nodes):
            raise ValueError("node table and graph node counts differ")
        self.nodes = nodes
        self.graph = graph
        self.seed = int(config.get("seed", 0))
        self.allow_duplicates = bool(config.get("allow_duplicates", False))
        self.randomise_pools = bool(randomise_pools)
        pools = config.get("pools")
        populations = config.get("populations")
        if not isinstance(pools, dict) or not pools:
            raise ValueError("mapping.pools must be a non-empty mapping")
        if not isinstance(populations, dict) or not populations:
            raise ValueError("mapping.populations must be a non-empty mapping")
        self.pools = pools
        self.population_config = populations

        motor = np.asarray(motor_mask, dtype=bool)
        if motor.shape != (graph.n_nodes,):
            raise ValueError("motor mask shape does not match the graph")
        self.motor_mask = motor
        self.action_masks = {
            str(name): np.asarray(mask, dtype=bool)
            for name, mask in (action_masks or {}).items()
        }
        for name, mask in self.action_masks.items():
            if mask.shape != motor.shape:
                raise ValueError(f"action mask {name!r} shape does not match")
        self._action_union = np.zeros(graph.n_nodes, dtype=bool)
        for mask in self.action_masks.values():
            self._action_union |= mask

        self._columns = {
            field: nodes[field].fillna("").astype(str).to_numpy()
            for field in FILTER_FIELDS
        }
        for name, payload in self.pools.items():
            self._validate_pool(name, payload)

        self._rng = np.random.default_rng(self.seed)
        self._pool_indices: dict[str, np.ndarray] = {}
        self._pool_orders: dict[str, np.ndarray] = {}
        self._used: set[int] = set()
        self.populations: dict[str, MappedPopulation] = {}
        self._pool_mode = (
            "random_matched_non_motor" if self.randomise_pools else "annotation"
        )
        for feature, payload in self.population_config.items():
            self.populations[str(feature)] = self._build_population(
                str(feature), payload
            )
        self.validate()

    # -- pool construction -------------------------------------------------
    def _validate_pool(self, name: str, payload: dict) -> None:
        if not isinstance(payload, dict) or not payload:
            raise ValueError(f"pool {name!r} must be a non-empty mapping")
        unknown = set(payload) - set(FILTER_FIELDS)
        if unknown:
            raise ValueError(
                f"pool {name!r} has unknown fields {sorted(unknown)}; "
                f"expected {list(FILTER_FIELDS)}"
            )
        for field, labels in payload.items():
            if not isinstance(labels, (list, tuple)) or not labels:
                raise ValueError(f"pool {name!r} field {field!r} has no labels")
            available = set(self._columns[field])
            for label in labels:
                if not isinstance(label, str) or not label:
                    raise ValueError(
                        f"pool {name!r} field {field!r} has a non-string label"
                    )
                if label == UNASSIGNED_LABEL:
                    if "" not in available:
                        raise ValueError(
                            f"pool {name!r} field {field!r} has no unassigned "
                            "values"
                        )
                    continue
                if label not in available:
                    raise ValueError(
                        f"pool {name!r} field {field!r} has unknown label "
                        f"{label!r}; available labels are "
                        f"{sorted(value for value in available if value)}"
                    )

    def _pool_mask(self, name: str) -> np.ndarray:
        if self.randomise_pools:
            return ~self.motor_mask
        mask = np.ones(self.graph.n_nodes, dtype=bool)
        for field, labels in self.pools[name].items():
            wanted = {
                "" if label == UNASSIGNED_LABEL else label for label in labels
            }
            mask &= np.isin(self._columns[field], list(wanted))
        mask &= ~self.motor_mask
        return mask

    def _pool(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        if name not in self._pool_indices:
            if not self.randomise_pools and name not in self.pools:
                raise ValueError(f"unknown annotation pool {name!r}")
            mask = self._pool_mask(name)
            if not mask.any():
                raise ValueError(
                    f"annotation pool {name!r} selects no non-motor neurons"
                )
            indices = np.flatnonzero(mask)
            self._pool_indices[name] = indices
            self._pool_orders[name] = self._rng.permutation(len(indices))
        return self._pool_indices[name], self._pool_orders[name]

    def _choose(self, pool: str, count: int) -> np.ndarray:
        if count < 1:
            raise ValueError("a population group must request at least one neuron")
        indices, order = self._pool(pool)
        candidates = indices[order]
        if not self.allow_duplicates:
            candidates = np.asarray(
                [index for index in candidates if int(index) not in self._used],
                dtype=np.int64,
            )
        if candidates.size < count:
            raise ValueError(
                f"annotation pool {pool!r} has {candidates.size} unused "
                f"neurons; requested {count}"
            )
        chosen = np.asarray(candidates[:count], dtype=np.int64)
        if not self.allow_duplicates:
            self._used.update(int(index) for index in chosen)
        return chosen

    def _build_population(self, feature: str, payload: dict) -> MappedPopulation:
        if not isinstance(payload, dict):
            raise ValueError(f"population {feature!r} must be a mapping")
        evidence = str(payload.get("evidence", ""))
        hypothesis = str(payload.get("hypothesis", ""))
        statement = str(payload.get("statement", ""))
        if not evidence or not hypothesis:
            raise ValueError(
                f"population {feature!r} requires an evidence label and a "
                "hypothesis identifier"
            )
        if "lane_pools" in payload:
            lane_pools = payload["lane_pools"]
            if not isinstance(lane_pools, dict) or len(lane_pools) < 2:
                raise ValueError(
                    f"population {feature!r} lane_pools must define at least "
                    "two groups"
                )
            count = int(payload.get("neurons_per_lane", 0))
            groups = {
                str(name): self._choose(str(pool), count)
                for name, pool in lane_pools.items()
            }
        else:
            pool = payload.get("pool")
            count = int(payload.get("n_neurons", 0))
            if not pool or count < 1:
                raise ValueError(
                    f"population {feature!r} requires pool and n_neurons"
                )
            groups = {"default": self._choose(str(pool), count)}
        return MappedPopulation(
            feature,
            groups,
            evidence=evidence,
            hypothesis=hypothesis,
            statement=statement,
            pool_mode=self._pool_mode,
        )

    # -- validation and reporting -----------------------------------------
    def validate(self) -> None:
        seen: set[int] = set()
        for feature, population in self.populations.items():
            indices = population.indices
            if indices.size == 0:
                raise ValueError(f"population {feature!r} is empty")
            if indices.min() < 0 or indices.max() >= self.graph.n_nodes:
                raise ValueError(
                    f"population {feature!r} has an index outside the graph"
                )
            if np.any(self.motor_mask[indices]):
                raise ValueError(
                    f"population {feature!r} targets a motor neuron"
                )
            if np.any(self._action_union[indices]):
                raise ValueError(
                    f"population {feature!r} targets a LEFT/RIGHT/JUMP neuron"
                )
            if not self.allow_duplicates:
                overlap = seen.intersection(int(value) for value in indices)
                if overlap:
                    raise ValueError(
                        f"population {feature!r} reuses {len(overlap)} neurons "
                        "from another feature without allow_duplicates"
                    )
                seen.update(int(value) for value in indices)

    @property
    def features(self) -> list[str]:
        return list(self.populations)

    def indices(self, feature: str) -> np.ndarray:
        return self.populations[feature].indices

    def size(self, feature: str) -> int:
        return self.populations[feature].size()

    def stimulated_indices(self) -> np.ndarray:
        chunks = [population.indices for population in self.populations.values()]
        return np.unique(np.concatenate(chunks))

    def signature(self) -> dict:
        per_feature = {
            feature: _digest(population.indices)
            for feature, population in self.populations.items()
        }
        payload = json.dumps(per_feature, sort_keys=True)
        return {
            "features": self.features,
            "per_feature_sha256": per_feature,
            "seed": self.seed,
            "pool_mode": self._pool_mode,
            "mapping_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        }

    def report(self) -> dict:
        selected = self.stimulated_indices()
        return {
            "seed": self.seed,
            "allow_duplicates": self.allow_duplicates,
            "pool_mode": self._pool_mode,
            "classification": CLASSIFICATION,
            "n_features": len(self.populations),
            "n_stimulated_neurons": int(selected.size),
            "motor_neurons_excluded": int(self.motor_mask.sum()),
            "motor_overlap": int(self.motor_mask[selected].sum()),
            "action_overlap": int(self._action_union[selected].sum()),
            "pools": {
                name: {field: sorted(labels) for field, labels in payload.items()}
                for name, payload in self.pools.items()
            }
            if not self.randomise_pools
            else {"pool_mode": "all non-motor neurons"},
            "populations": {
                feature: population.report(
                    self.graph, self.nodes, FILTER_FIELDS
                )
                for feature, population in self.populations.items()
            },
            "signature": self.signature(),
            "limitations": LIMITATIONS,
        }


class BancEventDrive:
    """Event-pulsed input schedule for the unchanged BANC simulator."""

    def __init__(
        self,
        mapping: BancSensoryMapping,
        encoders: dict,
        events,
        *,
        current_pa: dict[str, float],
        duration_ms: float,
        decay_ms: float = 150.0,
        dt_ms: float = 0.5,
        pulse_gain: float = 1.0,
        active_features=None,
    ) -> None:
        if not encoders:
            raise ValueError("at least one encoder is required")
        self.mapping = mapping
        self.encoders = encoders
        self.duration_ms = _finite(duration_ms, "duration_ms")
        if self.duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        self.decay_ms = _finite(decay_ms, "decay_ms")
        if self.decay_ms <= 0:
            raise ValueError("decay_ms must be positive")
        self.dt_ms = _finite(dt_ms, "dt_ms")
        if self.dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        self.pulse_gain = _finite(pulse_gain, "pulse_gain")
        if not 0 < self.pulse_gain <= 1.0:
            raise ValueError("pulse_gain must be in (0, 1]")

        missing = [name for name in encoders if name not in mapping.populations]
        if missing:
            raise ValueError(f"mapping is missing features {missing}")
        if active_features is None:
            self.active_features = list(encoders)
        else:
            unknown = set(active_features) - set(encoders)
            if unknown:
                raise ValueError(f"unknown active features {sorted(unknown)}")
            self.active_features = [
                feature for feature in encoders if feature in set(active_features)
            ]
            if not self.active_features:
                raise ValueError("at least one feature must be active")
        active = set(self.active_features)

        self.current_pa: dict[str, float] = {}
        for feature in encoders:
            value = _non_negative(
                current_pa.get(feature, 0.0), f"current_pa[{feature!r}]"
            )
            self.current_pa[feature] = value

        self._indices = np.concatenate(
            [mapping.indices(feature) for feature in encoders]
        )
        self._slices: dict[str, slice] = {}
        offset = 0
        for feature in encoders:
            size = mapping.size(feature)
            self._slices[feature] = slice(offset, offset + size)
            offset += size
        self._stimulated_indices = np.unique(
            np.concatenate(
                [mapping.indices(feature) for feature in self.active_features]
            )
        )

        self.events = validate_events(events, features=list(encoders))
        self._onsets: list[float] = []
        self._values: list[np.ndarray] = []
        self._source_events: list[dict] = []
        for event in self.events:
            values = event["feature_values"]
            if not values:
                continue
            encoded = encode_state(
                values, {name: encoders[name] for name in values}
            )
            drive = np.zeros(self._indices.size, dtype=np.float64)
            for feature in values:
                response = np.asarray(encoded[feature], dtype=np.float64)
                if response.size != mapping.size(feature):
                    raise ValueError(
                        f"encoder {feature!r} returns {response.size} values "
                        f"but the mapping has {mapping.size(feature)} neurons"
                    )
                if feature in active:
                    drive[self._slices[feature]] = (
                        response * self.current_pa[feature] * self.pulse_gain
                    )
            self._onsets.append(float(event["time_ms"]))
            self._values.append(drive)
            self._source_events.append(event)
        self._onsets = np.asarray(self._onsets, dtype=np.float64)

    # -- input-schedule contract ------------------------------------------
    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._stimulated_indices

    def apply(self, step: int, time_ms: float, current_pa: np.ndarray) -> None:
        """Add this step's decaying pulses; never overwrite other input."""
        if not self._onsets.size:
            return
        time_ms = float(time_ms)
        first = int(
            np.searchsorted(self._onsets, time_ms - self.decay_ms, side="left")
        )
        for position in range(first, self._onsets.size):
            onset = float(self._onsets[position])
            if onset > time_ms:
                break
            remaining = 1.0 - (time_ms - onset) / self.decay_ms
            if remaining <= 0.0:
                continue
            current_pa[self._indices] += self._values[position] * remaining

    def feature_currents_at(self, time_ms: float) -> dict[str, float]:
        buffer = np.zeros(int(self._indices.max()) + 1, dtype=np.float64)
        self.apply(0, float(time_ms), buffer)
        return {
            feature: float(
                buffer[self._indices[self._slices[feature]]].sum()
            )
            for feature in self.encoders
        }

    # -- accounting --------------------------------------------------------
    def _pulse_charge(self, position: int) -> float:
        onset = float(self._onsets[position])
        length = min(self.decay_ms, max(0.0, self.duration_ms - onset))
        if length <= 0:
            return 0.0
        area = self.decay_ms / 2.0 * (
            1.0 - (1.0 - length / self.decay_ms) ** 2
        )
        return float(self._values[position].sum()) * area

    def total_charge_pa_ms(self) -> float:
        return float(
            sum(self._pulse_charge(position) for position in range(self._onsets.size))
        )

    def input_statistics(self) -> dict:
        peaks = {feature: 0.0 for feature in self.encoders}
        for values in self._values:
            for feature in self.encoders:
                peaks[feature] = max(
                    peaks[feature], float(values[self._slices[feature]].sum())
                )
        by_kind: dict[str, int] = {}
        by_class: dict[str, int] = {}
        for event in self.events:
            by_kind[event["event"]] = by_kind.get(event["event"], 0) + 1
            by_class[event["class_name"]] = (
                by_class.get(event["class_name"], 0) + 1
            )
        return {
            "n_events": len(self.events),
            "n_pulses": int(self._onsets.size),
            "events_by_kind": dict(sorted(by_kind.items())),
            "events_by_class": dict(sorted(by_class.items())),
            "active_features": list(self.active_features),
            "peak_feature_current_pa": {
                feature: round(value, 6) for feature, value in peaks.items()
            },
            "max_per_neuron_current_pa": round(
                max(
                    (float(values.max()) for values in self._values),
                    default=0.0,
                ),
                6,
            ),
            "total_charge_pa_ms": round(self.total_charge_pa_ms(), 6),
            "decay_ms": self.decay_ms,
            "pulse_gain": self.pulse_gain,
        }

    def signature(self) -> dict:
        values = (
            np.stack(self._values)
            if self._values
            else np.zeros((0, self._indices.size), dtype=np.float64)
        )
        return {
            "indices": self._indices.astype(np.int64),
            "pulse_onsets": self._onsets,
            "pulse_values": values,
            "event_metadata": canonical_event_metadata(self.events),
        }

    def signature_sha256(self) -> str:
        signature = self.signature()
        digest = hashlib.sha256()
        digest.update(np.ascontiguousarray(signature["indices"]).tobytes())
        digest.update(b"|")
        digest.update(np.ascontiguousarray(signature["pulse_onsets"]).tobytes())
        digest.update(b"|")
        digest.update(np.ascontiguousarray(signature["pulse_values"]).tobytes())
        digest.update(b"|")
        digest.update(event_metadata_digest(self.events).encode("ascii"))
        return digest.hexdigest()

    def describe(self) -> dict:
        return {
            "kind": "banc_event_drive",
            "version": "phase_4h4_event_pulse_v1",
            "dt_ms": self.dt_ms,
            "duration_ms": self.duration_ms,
            "decay_ms": self.decay_ms,
            "pulse_gain": self.pulse_gain,
            "n_events": len(self.events),
            "n_pulses": int(self._onsets.size),
            "n_features": len(self.encoders),
            "active_features": list(self.active_features),
            "n_stimulated_neurons": int(self._stimulated_indices.size),
            "mapped_populations": {
                feature: int(self.mapping.size(feature))
                for feature in self.encoders
            },
            "event_metadata_sha256": event_metadata_digest(self.events),
            "signature_sha256": self.signature_sha256(),
            "policy": {
                "timing": (
                    "absolute event timestamps; equal timestamps are allowed"
                ),
                "decay": (
                    "linear decay of the encoded response over decay_ms after "
                    "each event"
                ),
                "state": (
                    "no held per-frame state; only events carrying feature "
                    "values drive current"
                ),
                "targets": (
                    "mapped non-motor sensory populations only; motor and "
                    "LEFT/RIGHT/JUMP masks are excluded"
                ),
            },
            "limitations": LIMITATIONS,
        }


class ConstantChargeDrive:
    """Uniform constant drive with the same total charge as a reference drive.

    Used by condition F: the same neurons receive a constant current over the
    whole run whose aggregate charge equals the reference event drive's
    aggregate charge. It carries no event timing or feature identity.
    """

    def __init__(
        self,
        indices,
        total_charge_pa_ms: float,
        *,
        duration_ms: float,
        dt_ms: float = 0.5,
    ) -> None:
        self._indices = np.unique(np.asarray(indices, dtype=np.int64))
        if self._indices.size == 0:
            raise ValueError("constant drive needs at least one neuron")
        self.duration_ms = _finite(duration_ms, "duration_ms")
        if self.duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        self.dt_ms = _finite(dt_ms, "dt_ms")
        total = _non_negative(total_charge_pa_ms, "total_charge_pa_ms")
        self.target_charge = total
        self.current_pa = float(
            total / (self._indices.size * self.duration_ms)
        )

    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._indices

    def apply(self, step: int, time_ms: float, current_pa: np.ndarray) -> None:
        if time_ms < 0 or time_ms >= self.duration_ms:
            return
        current_pa[self._indices] += self.current_pa

    def feature_currents_at(self, time_ms: float) -> dict:
        active = 0 <= time_ms < self.duration_ms
        return {
            "constant": float(self.current_pa * self._indices.size)
            if active
            else 0.0
        }

    def injected_charge_pa_ms(self) -> float:
        return float(self.current_pa * self._indices.size * self.duration_ms)

    def signature(self) -> dict:
        return {
            "indices": self._indices.astype(np.int64),
            "current_pa": np.asarray([self.current_pa]),
        }

    def signature_sha256(self) -> str:
        return _digest(
            self._indices.astype(np.int64), np.asarray([self.current_pa])
        )

    def describe(self) -> dict:
        return {
            "kind": "constant_charge_drive",
            "n_neurons": int(self._indices.size),
            "current_pa_per_neuron": round(self.current_pa, 9),
            "duration_ms": self.duration_ms,
            "target_charge_pa_ms": round(self.target_charge, 6),
            "injected_charge_pa_ms": round(self.injected_charge_pa_ms(), 6),
            "signature_sha256": self.signature_sha256(),
            "limitations": [
                "Carries no event timing or feature identity; it matches only "
                "the aggregate injected charge of the reference condition."
            ],
        }


def temporally_shuffle_events(events, *, seed: int) -> list:
    """Permute the sorted time array across event identities.

    Every event keeps its own identity fields and feature values; only the
    timestamp moves. The result is re-sorted by the new time so the adapter's
    monotonicity contract holds.
    """
    if not events:
        return []
    times = sorted(float(event["time_ms"]) for event in events)
    permutation = np.random.default_rng(int(seed)).permutation(len(times))
    shuffled = []
    for position, event in enumerate(events):
        copy = dict(event)
        copy["feature_values"] = dict(event["feature_values"])
        copy["time_ms"] = float(times[permutation[position]])
        shuffled.append(copy)
    shuffled.sort(
        key=lambda event: (
            event["time_ms"],
            int(event["frame_index"]),
            -1 if event["track_id"] is None else int(event["track_id"]),
            str(event["event"]),
        )
    )
    return shuffled


def shuffle_feature_identities(events, *, seed: int) -> list:
    """Permute feature-value payloads across the events that carry them.

    Timestamps and every other identity field are preserved; only which
    feature group fires at a time changes.
    """
    positions = [
        position
        for position, event in enumerate(events)
        if event.get("feature_values")
    ]
    payloads = [dict(events[position]["feature_values"]) for position in positions]
    permutation = np.random.default_rng(int(seed)).permutation(len(payloads))
    shuffled = []
    for position, event in enumerate(events):
        copy = dict(event)
        copy["feature_values"] = dict(event["feature_values"])
        shuffled.append(copy)
    for target, source in zip(positions, permutation):
        shuffled[target]["feature_values"] = dict(payloads[source])
    return shuffled
