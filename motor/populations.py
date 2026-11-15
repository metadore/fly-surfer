"""Abstract action populations derived from published BANC annotations.

Membership is defined only by expert annotation columns of the BANC v888 node
table. No edge, simulator state or predicted neurotransmitter is consulted, and
no neuron is moved between populations by a connectivity result.

The three populations are decoder labels:

``LEFT``
    Motor neurons whose ``side`` is ``left`` and whose
    ``body_part_effector`` is a leg effector.
``RIGHT``
    The same rule for ``side == right``.
``JUMP``
    ``super_class == motor`` and
    ``peripheral_target_type == tergotrochanter_extensor_muscle``. This is an
    annotation-defined jump-associated candidate pool, not a jump command.

Motor neurons outside these groups stay ``UNASSIGNED`` and are reported, never
forced into an action. ``ROLL`` and ``DUCK`` have no population because no
published annotation in this export defines them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

LEG_EFFECTORS = ("front_leg", "middle_leg", "hind_leg")
TERGOTROCHANTER_TARGET = "tergotrochanter_extensor_muscle"
ACTION_POPULATIONS = ("LEFT", "RIGHT", "JUMP")

UNSUPPORTED_ACTIONS = {
    "ROLL": (
        "No published BANC annotation in this export defines a roll motor "
        "population; a roll signal would need evidence not present in the "
        "structural tables."
    ),
    "DUCK": (
        "No published BANC annotation in this export defines a duck or crouch "
        "motor population; a duck signal would need evidence not present in "
        "the structural tables."
    ),
}

_REQUIRED_COLUMNS = (
    "super_class",
    "side",
    "body_part_effector",
    "peripheral_target_type",
)


@dataclass(frozen=True)
class PopulationOptions:
    """Annotation rules used to build the action populations."""

    leg_effectors: tuple[str, ...] = LEG_EFFECTORS
    jump_target: str = TERGOTROCHANTER_TARGET
    jump_membership_in_leg_pools: bool = False

    def __post_init__(self) -> None:
        effectors = tuple(str(value) for value in self.leg_effectors)
        if not effectors or any(not value for value in effectors):
            raise ValueError("leg_effectors must be a non-empty list of labels")
        object.__setattr__(self, "leg_effectors", effectors)
        if not str(self.jump_target):
            raise ValueError("jump_target must be a non-empty label")
        object.__setattr__(self, "jump_target", str(self.jump_target))


@dataclass
class MotorPopulations:
    """Boolean node masks for the decoder populations."""

    n_neurons: int
    threshold: int
    masks: dict[str, np.ndarray]
    motor_mask: np.ndarray
    unassigned_mask: np.ndarray
    composition: dict
    provenance: dict

    def __post_init__(self) -> None:
        if self.n_neurons < 1:
            raise ValueError("n_neurons must be positive")
        if set(self.masks) != set(ACTION_POPULATIONS):
            raise ValueError(
                f"masks must cover exactly {ACTION_POPULATIONS}, got {sorted(self.masks)}"
            )
        for name, mask in self.masks.items():
            array = np.asarray(mask, dtype=bool)
            if array.shape != (self.n_neurons,):
                raise ValueError(f"mask {name!r} must have shape ({self.n_neurons},)")
            self.masks[name] = array
        for name, array in (
            ("motor_mask", self.motor_mask),
            ("unassigned_mask", self.unassigned_mask),
        ):
            if np.asarray(array).shape != (self.n_neurons,):
                raise ValueError(f"{name} must have shape ({self.n_neurons},)")

    @property
    def sizes(self) -> dict[str, int]:
        return {name: int(mask.sum()) for name, mask in self.masks.items()}

    @property
    def assigned_union(self) -> np.ndarray:
        union = np.zeros(self.n_neurons, dtype=bool)
        for mask in self.masks.values():
            union |= mask
        return union

    def mask(self, action: str) -> np.ndarray:
        try:
            return self.masks[action]
        except KeyError:
            raise KeyError(f"unknown action population {action!r}") from None

    def report(self) -> dict:
        return {
            "n_neurons": int(self.n_neurons),
            "graph_threshold": int(self.threshold),
            "sizes": self.sizes,
            "motor_neurons": int(np.count_nonzero(self.motor_mask)),
            "assigned_motor_neurons": int(np.count_nonzero(self.assigned_union)),
            "unassigned_motor_neurons": int(
                np.count_nonzero(self.unassigned_mask)
            ),
            "composition": self.composition,
            "provenance": self.provenance,
        }


def _true_count(series: pd.Series) -> int:
    return int(series.astype("string").str.upper().eq("TRUE").sum())


def _composition(
    nodes: pd.DataFrame, mask: np.ndarray, motor_mask: np.ndarray
) -> dict:
    subset = nodes.loc[mask]
    effectors = (
        subset["body_part_effector"]
        .fillna("unknown")
        .astype(str)
        .value_counts()
        .sort_index()
    )
    block = {
        "size": int(mask.sum()),
        "motor_neurons": int(np.count_nonzero(mask & motor_mask)),
        "left": int(subset["side"].eq("left").sum()),
        "right": int(subset["side"].eq("right").sum()),
        "unknown_side": int(subset["side"].isna().sum()),
        "effectors": {str(key): int(value) for key, value in effectors.items()},
    }
    if "proofread" in subset.columns:
        block["proofread_true"] = _true_count(subset["proofread"])
    return block


def build_populations(
    nodes: pd.DataFrame,
    *,
    n_neurons: int | None = None,
    threshold: int = 5,
    options: PopulationOptions | None = None,
) -> MotorPopulations:
    """Build action masks from a Phase 4D BANC node table.

    ``nodes`` must be ordered by ``node_index`` so that row position equals the
    graph node index used by ``SpikeRecorder``.
    """
    options = options or PopulationOptions()
    missing = [name for name in _REQUIRED_COLUMNS if name not in nodes.columns]
    if missing:
        raise ValueError(f"node table is missing columns: {missing}")
    count = len(nodes)
    if count == 0:
        raise ValueError("node table is empty")
    if n_neurons is not None and int(n_neurons) != count:
        raise ValueError(
            f"n_neurons {n_neurons} does not match the {count} node-table rows"
        )
    if "node_index" in nodes.columns:
        index = nodes["node_index"].to_numpy()
        if not np.array_equal(index, np.arange(count, dtype=index.dtype)):
            raise ValueError("node_index must be contiguous from zero")

    super_class = nodes["super_class"]
    side = nodes["side"]
    effector = nodes["body_part_effector"]
    target = nodes["peripheral_target_type"]

    motor = super_class.eq("motor").to_numpy(dtype=bool)
    leg = effector.isin(list(options.leg_effectors)).to_numpy(dtype=bool)
    left = side.eq("left").to_numpy(dtype=bool)
    right = side.eq("right").to_numpy(dtype=bool)
    jump = (motor & target.eq(options.jump_target)).to_numpy(dtype=bool)
    leg_mask = motor & leg
    if not options.jump_membership_in_leg_pools:
        leg_mask = leg_mask & ~jump

    masks = {
        "LEFT": leg_mask & left,
        "RIGHT": leg_mask & right,
        "JUMP": jump,
    }
    union = np.zeros(count, dtype=bool)
    for mask in masks.values():
        union |= mask
    unassigned = motor & ~union

    composition = {
        "motor": _composition(nodes, motor, motor),
        "LEFT": _composition(nodes, masks["LEFT"], motor),
        "RIGHT": _composition(nodes, masks["RIGHT"], motor),
        "JUMP": _composition(nodes, masks["JUMP"], motor),
        "UNASSIGNED": _composition(nodes, unassigned, motor),
        "motor_missing_side": int(motor.sum() - int((motor & (left | right)).sum())),
        "motor_missing_effector": int(
            (motor & effector.isna().to_numpy(dtype=bool)).sum()
        ),
        "jump_candidates_in_leg_pools": int(
            np.count_nonzero(jump & leg & motor)
        ),
    }

    inclusion = options.jump_membership_in_leg_pools
    definitions = {
        "LEFT": (
            "super_class == 'motor' and side == 'left' and body_part_effector "
            f"in {list(options.leg_effectors)}"
            + ("" if inclusion else " and not a tergotrochanter candidate")
        ),
        "RIGHT": (
            "super_class == 'motor' and side == 'right' and body_part_effector "
            f"in {list(options.leg_effectors)}"
            + ("" if inclusion else " and not a tergotrochanter candidate")
        ),
        "JUMP": (
            "super_class == 'motor' and peripheral_target_type == "
            f"'{options.jump_target}'"
        ),
        "UNASSIGNED": "motor neurons not covered by LEFT, RIGHT or JUMP",
        "ROLL": "unsupported: " + UNSUPPORTED_ACTIONS["ROLL"],
        "DUCK": "unsupported: " + UNSUPPORTED_ACTIONS["DUCK"],
    }
    provenance = {
        "source": "Phase 4D BANC v888 node table (annotations only)",
        "graph_threshold": int(threshold),
        "definitions": definitions,
        "options": {
            "leg_effectors": list(options.leg_effectors),
            "jump_target": options.jump_target,
            "jump_membership_in_leg_pools": inclusion,
        },
        "overlap_policy": (
            "tergotrochanter candidates are also leg motor neurons; by default "
            "they are removed from LEFT/RIGHT so the action populations are "
            "disjoint and JUMP activity is not double-counted"
            if not inclusion
            else "tergotrochanter candidates remain inside LEFT/RIGHT and are "
            "also scored as JUMP; populations overlap by construction"
        ),
        "unsupported_actions": dict(UNSUPPORTED_ACTIONS),
        "scientific_status": (
            "LEFT, RIGHT and JUMP are decoder labels derived from published "
            "effector annotations. They are not identified biological motor "
            "commands."
        ),
    }
    return MotorPopulations(
        n_neurons=count,
        threshold=int(threshold),
        masks=masks,
        motor_mask=motor,
        unassigned_mask=unassigned,
        composition=composition,
        provenance=provenance,
    )


def load_banc_populations(
    nodes_path: Path | None = None,
    graph_path: Path | None = None,
    *,
    threshold: int = 5,
    options: PopulationOptions | None = None,
) -> MotorPopulations:
    """Load the Phase 4D node table and graph, checking index alignment."""
    from brain.banc_graph import OUT_DIR, BancConnectome

    nodes_path = Path(nodes_path or OUT_DIR / "banc_nodes.csv.gz")
    graph_path = Path(graph_path or OUT_DIR / f"banc_graph_t{int(threshold)}.npz")
    if not nodes_path.is_file():
        raise FileNotFoundError(f"missing BANC node table: {nodes_path}")
    if not graph_path.is_file():
        raise FileNotFoundError(f"missing BANC graph: {graph_path}")

    nodes = pd.read_csv(nodes_path)
    graph = BancConnectome.load(graph_path)
    graph_ids = np.asarray(graph.root_ids, dtype=np.int64)
    table_ids = nodes["banc_888_id"].to_numpy().astype(np.int64)
    if len(graph_ids) != len(table_ids) or not np.array_equal(graph_ids, table_ids):
        raise ValueError(
            "node table banc_888_id order does not match the graph root_ids"
        )
    populations = build_populations(
        nodes, n_neurons=graph.n_nodes, threshold=graph.threshold, options=options
    )
    populations.provenance.update(
        {
            "nodes_path": str(nodes_path),
            "graph_path": str(graph_path),
            "graph_nodes": int(graph.n_nodes),
            "graph_edges": int(graph.n_edges),
        }
    )
    return populations
