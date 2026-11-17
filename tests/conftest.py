"""Shared fixtures: small in-memory graphs matching the loader's GraphView."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.subgraph import GraphView

DEFAULT_VOCABULARY = {
    "nt_type": ["ACH", "GABA", "DA", "GLUT"],
    "super_class": ["central", "sensory", "motor"],
    "class": ["class_a", "class_b"],
    "side": ["left", "right"],
}


def make_graph(
    n_nodes: int,
    edges: list[tuple[int, int, int]],
    *,
    nt_codes: np.ndarray | None = None,
    super_class_codes: np.ndarray | None = None,
    class_codes: np.ndarray | None = None,
    side_codes: np.ndarray | None = None,
    root_ids: np.ndarray | None = None,
    vocabulary: dict | None = None,
) -> GraphView:
    """Build a validated GraphView from an explicit edge list."""
    root_ids = (
        np.arange(1000, 1000 + n_nodes, dtype=np.int64)
        if root_ids is None
        else np.asarray(root_ids, dtype=np.int64)
    )
    order = sorted((int(s), int(d), int(w)) for s, d, w in edges)
    edge_src = np.array([e[0] for e in order], dtype=np.int32)
    edge_dst = np.array([e[1] for e in order], dtype=np.int32)
    edge_weight = np.array([e[2] for e in order], dtype=np.int32)

    out_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=n_nodes), out=out_indptr[1:])
    in_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=n_nodes), out=in_indptr[1:])
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int32)

    def codes(values, default):
        if values is None:
            return np.full(n_nodes, default, dtype=np.int16)
        return np.asarray(values, dtype=np.int16)

    return GraphView(
        root_ids=root_ids,
        node_map=np.arange(n_nodes, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        nt_code=codes(nt_codes, 0),
        super_class_code=codes(super_class_codes, 0),
        class_code=codes(class_codes, 0),
        side_code=codes(side_codes, 0),
        positions=np.zeros((n_nodes, 3), dtype=np.float32),
        vocabulary=dict(vocabulary or DEFAULT_VOCABULARY),
        source_n_nodes=n_nodes,
        source_n_edges=len(order),
    )


@pytest.fixture
def graph_factory():
    return make_graph


# ---------------------------------------------------------------------------
# Phase 8 synthetic rows
# ---------------------------------------------------------------------------

PHASE8_SHA = "a" * 64
PHASE8_ROLES = {
    "A": "reference",
    "B": "condition",
    "C": "condition",
    "D": "condition",
    "E": "condition",
    "E_full": "exploratory",
    "F": "condition",
    "F_beta": "control",
    "F_init": "control",
    "A_prime": "control",
    "C_prime": "control",
    "floor": "floor",
}


def make_phase8_row(
    condition,
    seed,
    episode,
    *,
    steps=20,
    non_no_action=0,
    role=None,
    status="ok",
    error=None,
    decision_classes=None,
    motor_summary=None,
    weights_before=None,
    weights_after=None,
    total_reward=0.0,
    termination_reason="collision",
    terminated=True,
    truncated=False,
):
    """Build one schema-valid Phase 8 episode row for analysis tests.

    The capped survival score is ``steps`` (the cap is 900), so a test can
    express the primary outcome directly. ``non_no_action`` transfers that many
    decisions from ``NO_ACTION`` to ``LEFT``; no game is constructed.
    """
    if status not in ("ok", "error"):
        raise ValueError("status must be 'ok' or 'error'")
    steps = int(steps)
    non_no_action = int(non_no_action)
    if status == "error":
        steps = 0
        counts = {"NO_ACTION": 0}
        terminated = False
        truncated = False
        termination_reason = None
    else:
        if not 0 <= non_no_action <= steps:
            raise ValueError("non_no_action must lie in [0, steps]")
        counts = {"NO_ACTION": steps - non_no_action}
        if non_no_action:
            counts["LEFT"] = non_no_action
        if truncated:
            termination_reason = termination_reason or "rollout_step_cap"
    row = {
        "schema_version": 1,
        "condition": condition,
        "role": PHASE8_ROLES[condition] if role is None else role,
        "seed": int(seed),
        "episode": int(episode),
        "environment_seed": 123456 + int(seed) * 100 + int(episode),
        "training": False,
        "steps": steps,
        "observed_updates": steps,
        "survival_score": float(steps),
        "max_game_updates": 900,
        "total_reward": float(total_reward),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "termination_reason": termination_reason,
        "action_counts": counts,
        "no_action_fraction": (
            counts["NO_ACTION"] / steps if steps else 0.0
        ),
        "motor_spikes": 0,
        "spike_sha256": PHASE8_SHA,
        "action_sha256": PHASE8_SHA,
        "weights_before": (
            PHASE8_SHA if weights_before is None else weights_before
        ),
        "weights_after": PHASE8_SHA if weights_after is None else weights_after,
        "config_hashes": {
            "environment": PHASE8_SHA,
            "campaign": PHASE8_SHA,
            "conditions": PHASE8_SHA,
        },
        "input_hashes": {"graph": PHASE8_SHA},
        "started_at": "2026-11-17T00:00:00Z",
        "wall_time_s": 0.5,
    }
    if status == "error":
        row["status"] = "error"
        row["error"] = error or "synthetic failure"
    if decision_classes is not None:
        row["decision_classes"] = dict(decision_classes)
    if motor_summary is not None:
        row["motor_summary"] = dict(motor_summary)
    return row


@pytest.fixture
def phase_8_row():
    return make_phase8_row
