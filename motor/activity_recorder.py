"""Time-windowed motor and pathway activity from a BANC spike recording.

The recorder is read-only. It selects published BANC annotation populations
(motor neurons, descending neurons, ascending neurons and VNC intrinsic
neurons) and reports per-population and per-neuron counts and rates inside
half-open windows ``[start_ms, end_ms)``. Spikes are never modified, shifted or
synthesised.

Two partitions are supported:

* direct stimulation versus downstream network activity. The caller supplies
  the stimulated node indices; every spike from one of those nodes is counted
  as direct and every other spike as downstream;
* motor neuron subsets are taken from :class:`motor.populations.MotorPopulations`
  so that LEFT, RIGHT and JUMP activity is measured with exactly the masks the
  decoder uses.

A population with no spikes is reported as zeros. Empty or silent populations
never raise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from motor.populations import ACTION_POPULATIONS, MotorPopulations

ANNOTATION_COLUMNS = (
    "banc_888_id",
    "super_class",
    "cell_class",
    "cell_sub_class",
    "cell_type",
    "side",
    "body_part_effector",
    "peripheral_target_type",
    "neurotransmitter_verified",
    "proofread",
)

_SELECTION_DEFINITIONS = {
    "motor": "super_class == 'motor'",
    "descending": "super_class == 'descending'",
    "ascending": "super_class == 'ascending'",
    "vnc_intrinsic": "super_class == 'ventral_nerve_cord_intrinsic'",
    "non_motor": "super_class != 'motor'",
    "unassigned_motor": "motor neurons outside LEFT, RIGHT and JUMP",
    "left_motor": "Phase 4F LEFT motor population",
    "right_motor": "Phase 4F RIGHT motor population",
    "jump_motor": "Phase 4F JUMP motor population",
}


def _jsonify(value):
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(float(value)) else float(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


@dataclass(frozen=True)
class PopulationSelection:
    """One annotated node population and the rule that produced it."""

    name: str
    role: str
    mask: np.ndarray
    node_indices: np.ndarray
    banc_ids: np.ndarray
    definition: str

    @property
    def size(self) -> int:
        return int(self.node_indices.size)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "size": self.size,
            "definition": self.definition,
            "provenance": "BANC v888 published node annotations",
        }


@dataclass(frozen=True)
class MotorWindow:
    """Activity inside one half-open window for every selected population."""

    start_ms: float
    end_ms: float
    n_spikes: int
    populations: Mapping[str, dict]
    direct: dict | None
    downstream: dict | None
    stimulated_neurons: int | None

    @property
    def duration_ms(self) -> float:
        return float(self.end_ms - self.start_ms)

    def as_dict(self) -> dict:
        return {
            "window_start_ms": round(float(self.start_ms), 4),
            "window_end_ms": round(float(self.end_ms), 4),
            "duration_ms": round(self.duration_ms, 4),
            "n_spikes": int(self.n_spikes),
            "stimulated_neurons": self.stimulated_neurons,
            "populations": {
                name: dict(block) for name, block in self.populations.items()
            },
            "direct": None if self.direct is None else dict(self.direct),
            "downstream": None if self.downstream is None else dict(self.downstream),
        }


class MotorActivityRecorder:
    """Read-only windowed view over a BANC ``SpikeRecorder``."""

    def __init__(
        self,
        recorder,
        populations: MotorPopulations,
        nodes: pd.DataFrame,
        *,
        graph=None,
        stimulated_indices: Iterable[int] | None = None,
        annotation_columns: Iterable[str] = ANNOTATION_COLUMNS,
    ) -> None:
        if recorder is None:
            raise ValueError("recorder is required")
        n = int(getattr(recorder, "n_neurons", -1))
        if n != int(populations.n_neurons):
            raise ValueError(
                "recorder neuron count does not match the motor populations"
            )
        if len(nodes) != n:
            raise ValueError(
                f"node table has {len(nodes)} rows; expected {n}"
            )
        for column in ("banc_888_id", "super_class"):
            if column not in nodes.columns:
                raise ValueError(f"node table is missing column {column!r}")
        if "node_index" in nodes.columns:
            index = nodes["node_index"].to_numpy()
            if not np.array_equal(index, np.arange(n, dtype=index.dtype)):
                raise ValueError("node_index must be contiguous from zero")

        self.recorder = recorder
        self.populations = populations
        self._nodes = nodes.reset_index(drop=True)
        self._graph = graph
        self._annotation_columns = tuple(str(name) for name in annotation_columns)
        missing = [name for name in self._annotation_columns if name not in self._nodes]
        if missing:
            raise ValueError(f"node table is missing annotation columns: {missing}")
        if graph is not None:
            graph_ids = np.asarray(graph.root_ids, dtype=np.int64)
            table_ids = self._nodes["banc_888_id"].to_numpy().astype(np.int64)
            if not np.array_equal(graph_ids, table_ids):
                raise ValueError(
                    "node table banc_888_id order does not match graph root_ids"
                )

        self._stimulated = np.empty(0, dtype=np.int64)
        self._selections = self._build_selections()
        if stimulated_indices is not None:
            self.set_stimulated_indices(stimulated_indices)

    # ------------------------------------------------------------------
    # selections
    # ------------------------------------------------------------------

    def _build_selections(self) -> dict[str, PopulationSelection]:
        nodes = self._nodes
        super_class = nodes["super_class"].fillna("").astype(str)
        masks = {
            "motor": np.asarray(self.populations.motor_mask, dtype=bool),
            "descending": super_class.eq("descending").to_numpy(dtype=bool),
            "ascending": super_class.eq("ascending").to_numpy(dtype=bool),
            "vnc_intrinsic": super_class.eq(
                "ventral_nerve_cord_intrinsic"
            ).to_numpy(dtype=bool),
            "non_motor": ~np.asarray(self.populations.motor_mask, dtype=bool),
            "unassigned_motor": np.asarray(
                self.populations.unassigned_mask, dtype=bool
            ),
        }
        for action in ACTION_POPULATIONS:
            masks[f"{action.lower()}_motor"] = np.asarray(
                self.populations.mask(action), dtype=bool
            )
        banc_ids = nodes["banc_888_id"].to_numpy().astype(np.int64)
        roles = {
            "motor": "motor_neuron",
            "descending": "descending_neuron",
            "ascending": "ascending_neuron",
            "vnc_intrinsic": "vnc_intrinsic_neuron",
            "non_motor": "comparison",
            "unassigned_motor": "motor_neuron_subset",
            **{f"{action.lower()}_motor": "motor_neuron_subset" for action in ACTION_POPULATIONS},
        }
        selections: dict[str, PopulationSelection] = {}
        for name, mask in masks.items():
            indices = np.flatnonzero(mask).astype(np.int64)
            selections[name] = PopulationSelection(
                name=name,
                role=roles[name],
                mask=mask,
                node_indices=indices,
                banc_ids=banc_ids[indices],
                definition=_SELECTION_DEFINITIONS[name],
            )
        return selections

    @property
    def n_neurons(self) -> int:
        return int(self.recorder.n_neurons)

    @property
    def n_spikes(self) -> int:
        return int(len(self.recorder.spike_times_ms))

    @property
    def graph_threshold(self) -> int | None:
        if self._graph is not None and hasattr(self._graph, "threshold"):
            return int(self._graph.threshold)
        return int(self.populations.threshold)

    @property
    def stimulated_indices(self) -> np.ndarray:
        return self._stimulated

    def selection(self, name: str) -> PopulationSelection:
        try:
            return self._selections[name]
        except KeyError:
            raise KeyError(
                f"unknown population {name!r}; available: {sorted(self._selections)}"
            ) from None

    def selection_names(self) -> tuple[str, ...]:
        return tuple(self._selections)

    def set_stimulated_indices(self, indices: Iterable[int]) -> None:
        values = np.asarray(list(indices), dtype=np.int64)
        if values.ndim != 1:
            raise ValueError("stimulated indices must be 1-D")
        if values.size:
            if int(values.min()) < 0 or int(values.max()) >= self.n_neurons:
                raise ValueError("stimulated index outside the graph")
        self._stimulated = np.unique(values).astype(np.int64)

    def clear_stimulation(self) -> None:
        self._stimulated = np.empty(0, dtype=np.int64)

    # ------------------------------------------------------------------
    # windows
    # ------------------------------------------------------------------

    def _validate_window(self, start_ms: float, end_ms: float) -> tuple[float, float]:
        start = float(start_ms)
        end = float(end_ms)
        if not np.isfinite(start) or not np.isfinite(end) or end <= start:
            raise ValueError("window end must be a finite time after its start")
        return start, end

    def _window_counts(
        self, start: float, end: float
    ) -> tuple[np.ndarray, int]:
        times = np.asarray(self.recorder.spike_times_ms)
        indices = np.asarray(self.recorder.spike_neuron_indices, dtype=np.int64)
        in_window = (times >= start) & (times < end)
        selected = indices[in_window]
        counts = np.bincount(selected, minlength=self.n_neurons).astype(np.int64)
        return counts, int(selected.size)

    def _block(
        self,
        mask: np.ndarray,
        counts: np.ndarray,
        seconds: float,
        total_spikes: int,
    ) -> dict:
        member = counts[mask]
        spikes = int(member.sum())
        active = int(np.count_nonzero(member))
        size = int(mask.sum())
        return {
            "size": size,
            "spikes": spikes,
            "active_neurons": active,
            "silent_neurons": size - active,
            "active_fraction": round(active / size, 6) if size else 0.0,
            "mean_rate_hz": round(spikes / size / seconds, 4) if size else 0.0,
            "active_mean_rate_hz": (
                round(spikes / active / seconds, 4) if active else 0.0
            ),
            "spike_share": round(spikes / max(1, total_spikes), 6),
        }

    def time_window(
        self,
        start_ms: float,
        end_ms: float,
        *,
        stimulated_indices: Iterable[int] | None = None,
    ) -> MotorWindow:
        """Measure every selected population inside ``[start_ms, end_ms)``."""
        start, end = self._validate_window(start_ms, end_ms)
        counts, total = self._window_counts(start, end)
        seconds = (end - start) / 1000.0

        if stimulated_indices is not None:
            original = self._stimulated
            self.set_stimulated_indices(stimulated_indices)
        else:
            original = None
        try:
            stimulated = self._stimulated
            stim_mask = None
            if stimulated.size:
                stim_mask = np.zeros(self.n_neurons, dtype=bool)
                stim_mask[stimulated] = True

            blocks: dict[str, dict] = {}
            for name, selection in self._selections.items():
                block = self._block(
                    selection.mask, counts, seconds, total
                )
                if stim_mask is not None:
                    direct_mask = selection.mask & stim_mask
                    downstream_mask = selection.mask & ~stim_mask
                    block["direct_spikes"] = int(counts[direct_mask].sum())
                    block["downstream_spikes"] = int(
                        counts[downstream_mask].sum()
                    )
                    block["direct_active_neurons"] = int(
                        np.count_nonzero(counts[direct_mask])
                    )
                    block["downstream_active_neurons"] = int(
                        np.count_nonzero(counts[downstream_mask])
                    )
                blocks[name] = block

            direct = None
            downstream = None
            if stim_mask is not None:
                direct = self._block(
                    stim_mask, counts, seconds, total
                )
                downstream = self._block(
                    ~stim_mask, counts, seconds, total
                )
            return MotorWindow(
                start_ms=start,
                end_ms=end,
                n_spikes=total,
                populations=blocks,
                direct=direct,
                downstream=downstream,
                stimulated_neurons=None if stim_mask is None else int(stim_mask.sum()),
            )
        finally:
            if original is not None:
                self._stimulated = original

    def per_neuron(
        self,
        start_ms: float,
        end_ms: float,
        population: str = "motor",
        *,
        annotation_columns: Iterable[str] | None = None,
        include_silent: bool = True,
    ) -> dict:
        """Per-neuron counts, rates and annotation provenance for one window.

        Only a declared population can be requested; returning all 172,433
        graph nodes is not a summary and is intentionally unsupported.
        """
        start, end = self._validate_window(start_ms, end_ms)
        selection = self.selection(population)
        counts, _ = self._window_counts(start, end)
        member = counts[selection.node_indices]
        seconds = (end - start) / 1000.0
        keep = np.ones(member.size, dtype=bool) if include_silent else member > 0
        indices = selection.node_indices[keep]
        member = member[keep]

        columns = tuple(
            str(name)
            for name in (
                self._annotation_columns
                if annotation_columns is None
                else annotation_columns
            )
        )
        annotations = {}
        frame = self._nodes.iloc[indices]
        for column in columns:
            if column == "banc_888_id":
                continue
            annotations[column] = [
                _jsonify(value) for value in frame[column].tolist()
            ]
        return {
            "population": population,
            "definition": selection.definition,
            "window_start_ms": round(start, 4),
            "window_end_ms": round(end, 4),
            "duration_ms": round(end - start, 4),
            "n_neurons": int(indices.size),
            "node_indices": [int(value) for value in indices],
            "banc_888_id": [int(value) for value in selection.banc_ids[keep]],
            "spikes": [int(value) for value in member],
            "rate_hz": [round(float(value) / seconds, 4) for value in member],
            "active": [bool(value) for value in member > 0],
            "annotations": annotations,
        }

    def describe(self) -> dict:
        return {
            "source": "BANC v888 published node annotations",
            "graph_threshold": self.graph_threshold,
            "n_neurons": self.n_neurons,
            "n_spikes": self.n_spikes,
            "window_semantics": "[start_ms, end_ms)",
            "populations": {
                name: selection.describe()
                for name, selection in self._selections.items()
            },
            "annotation_columns": list(self._annotation_columns),
            "stimulation": {
                "n_stimulated_neurons": int(self._stimulated.size),
                "partition": "direct = spikes from stimulated nodes; downstream = all other spikes",
            },
            "scientific_status": (
                "Activity is model output from a structural graph. Population "
                "membership comes from published annotations; the recorder does "
                "not infer biological function."
            ),
        }
