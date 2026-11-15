"""Shared harness for Phase 4H robustness experiments.

Everything here reuses the Phase 4D graph artifact, the Phase 4F populations and
decoder, and the Phase 4G simulator and synapse policy unchanged. The module
adds only candidate selection, condition execution, metric extraction and
deterministic statistics.

Units and claims follow Phase 4G: weights are transformed structural synapse
counts, not conductances; spikes are model output; decoder labels are decoder
labels, not biological motor commands.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import sys
import time
from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import BancConnectome  # noqa: E402
from brain.banc_simulation_adapter import BancActivityAdapter  # noqa: E402
from brain.banc_simulator import BancSimulationResult, BancSimulator, BancStimulation  # noqa: E402
from brain.banc_synapse_policy import (  # noqa: E402
    CLASS_NAMES,
    VERIFIED_EXCITATORY,
    BancSynapsePolicy,
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)
from brain.neuron_model import LIFParameters  # noqa: E402
from motor.motor_decoder import DecoderConfig, MotorDecoder  # noqa: E402
from motor.populations import (  # noqa: E402
    ACTION_POPULATIONS,
    PopulationOptions,
    build_populations,
)

GRAPH_DIR = PROJECT_ROOT / "datasets" / "processed" / "banc_v888"
NODES_PATH = GRAPH_DIR / "banc_nodes.csv.gz"
GRAPH_T5 = GRAPH_DIR / "banc_graph_t5.npz"
POLICY_CONFIG = PROJECT_ROOT / "configs" / "banc_synapse_policy.yaml"
DECODER_CONFIG = PROJECT_ROOT / "configs" / "motor_decoder.yaml"
NEURON_CONFIG = PROJECT_ROOT / "configs" / "neuron_config.yaml"
PHASE_4G_RESULT = (
    PROJECT_ROOT / "experiments" / "results" / "phase_4g" / "phase_4g_experiment.json"
)
BASELINE_INTEGRITY = (
    PROJECT_ROOT / "experiments" / "phase_4h" / "baseline_integrity.json"
)
RESULTS = PROJECT_ROOT / "experiments" / "results" / "phase_4h"

THRESHOLD = 5
SEED_ROOT = 20261109
N_CANDIDATES = 64
DT_MS = 0.5
DURATION_MS = 300.0
STIM_START_MS = 50.0
STIM_END_MS = 250.0
STIM_CURRENT_PA = 300.0
DECODE_START_MS = 50.0
DECODE_END_MS = 300.0
MAX_RECORDED_SPIKES = 5_000_000
N_DRAWS = 100
FAMILIES = (
    "A_vnc_intrinsic_random",
    "B_motor_projecting_random",
    "C_all_verified_excitatory_random",
    "D_rank_stratum_shuffled",
    "E_connectivity_annotation_matched",
)
FAMILY_ORDINAL = {name: index + 1 for index, name in enumerate(FAMILIES)}


# ---------------------------------------------------------------------------
# hashing and small helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_json(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def digest_array(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def spike_hash(recorder) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(recorder.spike_times_ms).tobytes())
    digest.update(np.ascontiguousarray(recorder.spike_neuron_indices).tobytes())
    return digest.hexdigest()


def process_memory() -> dict | None:
    """Current and peak working-set memory of this process, if measurable."""
    try:
        import psutil

        info = psutil.Process().memory_info()
    except Exception:
        return None
    peak = getattr(info, "peak_wset", None)
    return {
        "rss_mb": round(float(info.rss) / 1e6, 4),
        "peak_wset_mb": None if peak is None else round(float(peak) / 1e6, 4),
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def software_versions() -> dict:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "platform": platform.platform(),
    }


def load_yaml(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=1, allow_nan=False, default=str) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# world
# ---------------------------------------------------------------------------


@dataclass
class World:
    graph: BancConnectome
    nodes: pd.DataFrame
    policy: BancSynapsePolicy
    populations: object
    decoder_config: DecoderConfig
    neuron_params: LIFParameters
    scores: np.ndarray
    in_degree: np.ndarray
    out_degree: np.ndarray
    eligible_vnc: np.ndarray
    eligible_all_exc: np.ndarray
    eligible_motor_projecting: np.ndarray
    candidate_c: np.ndarray
    config: dict
    signature: dict

    @property
    def n_nodes(self) -> int:
        return int(self.graph.n_nodes)

    def describe(self) -> dict:
        return {
            "graph": {
                "artifact": str(GRAPH_T5.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": self.signature["inputs"]["graph_sha256"],
                "threshold": int(self.graph.threshold),
                "n_nodes": int(self.graph.n_nodes),
                "n_edges": int(self.graph.n_edges),
                "n_synapses": int(self.graph.n_synapses),
                "n_isolated": int(self.graph.n_isolated),
            },
            "node_table": {
                "artifact": str(NODES_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": self.signature["inputs"]["nodes_sha256"],
            },
            "policy": self.policy.describe(),
            "decoder": {
                "config_sha256": self.signature["inputs"]["decoder_config_sha256"],
                "populations": self.populations.report(),
                "config": {
                    "window_ms": float(self.decoder_config.window_ms),
                    "step_ms": float(self.decoder_config.step_ms),
                    "activation_threshold": float(self.decoder_config.activation_threshold),
                    "release_threshold": float(self.decoder_config.release_threshold),
                    "min_active_neurons": int(self.decoder_config.min_active_neurons),
                    "min_spikes": int(self.decoder_config.min_spikes),
                    "priority": list(self.decoder_config.priority),
                    "arbitration": self.decoder_config.arbitration,
                    "smoothing": self.decoder_config.smoothing,
                },
            },
            "neuron": {
                item.name: getattr(self.neuron_params, item.name)
                for item in fields(self.neuron_params)
            },
            "pools": {
                "vnc_intrinsic_eligible": int(self.eligible_vnc.sum()),
                "vnc_intrinsic_eligible_excluding_c": int(
                    (self.eligible_vnc & ~_as_mask(self.candidate_c, self.n_nodes)).sum()
                ),
                "motor_projecting_eligible": int(self.eligible_motor_projecting.sum()),
                "all_verified_excitatory_non_motor": int(self.eligible_all_exc.sum()),
                "rank_stratum_65_256": int(
                    (
                        self.eligible_vnc
                        & ~_as_mask(self.candidate_c, self.n_nodes)
                        & _rank_between(self, 64, 256)
                    ).sum()
                ),
            },
            "config_sha256": self.signature["config_sha256"],
        }


def _as_mask(indices: np.ndarray, n: int) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    mask[np.asarray(indices, dtype=np.int64)] = True
    return mask


def _rank_between(world: "World", low: int, high: int) -> np.ndarray:
    order = rank_top(world, world.eligible_vnc, world.scores, high)
    mask = np.zeros(world.n_nodes, dtype=bool)
    mask[order[low:high]] = True
    return mask


def load_world() -> World:
    config = load_yaml(POLICY_CONFIG)
    decoder_payload = load_yaml(DECODER_CONFIG)
    neuron_payload = load_yaml(NEURON_CONFIG)
    sign_policy = SignPolicy.from_config(config["transmitter_sign_policy"])
    weight_policy = WeightPolicy.from_config(config["weight_policy"]["primary"])
    nodes = pd.read_csv(NODES_PATH)
    graph = BancConnectome.load(GRAPH_T5)
    if len(nodes) != graph.n_nodes:
        raise RuntimeError("node table and graph node counts differ")
    if not np.array_equal(
        nodes["banc_888_id"].to_numpy().astype(np.int64),
        np.asarray(graph.root_ids, dtype=np.int64),
    ):
        raise RuntimeError("node table order does not match graph root_ids")
    policy = build_synapse_policy(graph, nodes, sign_policy, weight_policy)
    populations = build_populations(
        nodes,
        n_neurons=graph.n_nodes,
        threshold=graph.threshold,
        options=PopulationOptions(**decoder_payload["populations"]),
    )
    decoder_config = DecoderConfig.from_config(decoder_payload["decoder"])
    neuron_params = LIFParameters.from_config(neuron_payload["neuron"])

    motor = np.asarray(populations.motor_mask, dtype=bool)
    codes = policy.neuron_codes
    super_class = nodes["super_class"].fillna("").astype(str)
    exc = (codes == VERIFIED_EXCITATORY) & ~motor

    src = np.asarray(graph.edge_src, dtype=np.int64)
    dst = np.asarray(graph.edge_dst, dtype=np.int64)
    weight = np.asarray(graph.edge_weight, dtype=np.int64)
    motor_edges = motor[dst]
    scores = np.bincount(
        src[motor_edges], weights=weight[motor_edges], minlength=graph.n_nodes
    )
    in_degree = np.diff(np.asarray(graph.in_indptr))
    out_degree = np.diff(np.asarray(graph.out_indptr))

    eligible_vnc = (
        super_class.eq("ventral_nerve_cord_intrinsic").to_numpy() & exc
    )
    eligible_all_exc = exc
    has_motor_edge = np.zeros(graph.n_nodes, dtype=bool)
    has_motor_edge[src[motor_edges]] = True
    eligible_motor_projecting = exc & has_motor_edge

    candidate_c = rank_top_from(
        np.flatnonzero(eligible_vnc), scores, N_CANDIDATES
    )
    _verify_candidate_reference(graph, candidate_c)

    signature = {
        "inputs": {
            "graph_sha256": sha256_file(GRAPH_T5),
            "nodes_sha256": sha256_file(NODES_PATH),
            "policy_config_sha256": sha256_file(POLICY_CONFIG),
            "decoder_config_sha256": sha256_file(DECODER_CONFIG),
            "neuron_config_sha256": sha256_file(NEURON_CONFIG),
        },
        "sign_policy": sign_policy.describe(),
        "weight_policy": weight_policy.describe(),
        "selection": {
            "package": "super_class == ventral_nerve_cord_intrinsic",
            "sign_class": "verified excitatory",
            "motor_neurons_excluded": True,
            "rule": "top-N by integer signed synapse count onto the 805 motor neurons",
            "tie_break": "ascending graph node index",
        },
    }
    signature["config_sha256"] = digest_json(signature)
    return World(
        graph=graph,
        nodes=nodes,
        policy=policy,
        populations=populations,
        decoder_config=decoder_config,
        neuron_params=neuron_params,
        scores=scores,
        in_degree=in_degree,
        out_degree=out_degree,
        eligible_vnc=eligible_vnc,
        eligible_all_exc=eligible_all_exc,
        eligible_motor_projecting=eligible_motor_projecting,
        candidate_c=candidate_c,
        config=config,
        signature=signature,
    )


def ranked_order_from(indices: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """Indices ordered by descending score, ties broken by ascending index."""
    indices = np.asarray(indices, dtype=np.int64)
    return indices[np.lexsort((indices, -scores[indices]))]


def rank_top_from(indices: np.ndarray, scores: np.ndarray, count: int) -> np.ndarray:
    indices = np.asarray(indices, dtype=np.int64)
    if indices.size == 0:
        raise ValueError("cannot rank an empty pool")
    order = ranked_order_from(indices, scores)
    if count > order.size:
        raise ValueError(f"pool has {order.size} neurons; requested {count}")
    return np.sort(order[:count].astype(np.int64))


def rank_top(world: World, mask: np.ndarray, scores: np.ndarray, count: int) -> np.ndarray:
    return rank_top_from(np.flatnonzero(mask), scores, count)


def _rank_between(world: "World", low: int, high: int) -> np.ndarray:
    order = ranked_order_from(np.flatnonzero(world.eligible_vnc), world.scores)
    mask = np.zeros(world.n_nodes, dtype=bool)
    mask[order[low:high]] = True
    return mask


def _verify_candidate_reference(graph: BancConnectome, candidate: np.ndarray) -> None:
    if not PHASE_4G_RESULT.is_file():
        return
    payload = json.loads(PHASE_4G_RESULT.read_text(encoding="utf-8"))
    block = payload["conditions"]["C_vnc_intrinsic_candidate"]["summary"]["stimulation"]
    expected = [int(value) for value in block["root_ids"]]
    actual = [int(value) for value in graph.root_ids[candidate]]
    if expected != actual:
        raise RuntimeError(
            "recomputed Phase 4G condition C does not match the recorded "
            "candidate list; Phase 4H must not proceed"
        )


# ---------------------------------------------------------------------------
# control families
# ---------------------------------------------------------------------------


def draw_seed(family: str, draw_index: int) -> int:
    return SEED_ROOT + 1000 * FAMILY_ORDINAL[family] + int(draw_index)


def _strata(world: World) -> tuple[np.ndarray, dict]:
    """Quintile bins over the positive-score VNC pool crossed with cell_class."""
    pool = np.flatnonzero(world.eligible_vnc)
    scored = pool[world.scores[pool] > 0]
    edges = np.quantile(world.scores[scored], [0.2, 0.4, 0.6, 0.8])
    cc = world.nodes["cell_class"].notna().to_numpy()

    def code(indices: np.ndarray) -> np.ndarray:
        bins = np.searchsorted(edges, world.scores[indices], side="right")
        return bins * 2 + cc[indices].astype(np.int64)

    return code, {"pool": pool, "bin_edges": [float(v) for v in edges]}


def family_draw(world: World, family: str, draw_index: int) -> dict:
    """One control draw plus the metadata needed to audit it."""
    if family not in FAMILY_ORDINAL:
        raise ValueError(f"unknown family {family!r}")
    seed = draw_seed(family, draw_index)
    rng = np.random.default_rng(seed)
    c_mask = _as_mask(world.candidate_c, world.n_nodes)
    meta: dict = {"family": family, "draw_index": int(draw_index), "seed": seed}
    if family == "A_vnc_intrinsic_random":
        pool = np.flatnonzero(world.eligible_vnc & ~c_mask)
        chosen = rng.choice(pool, size=N_CANDIDATES, replace=False)
        meta.update({"pool_size": int(pool.size), "pool": "vnc_intrinsic_eligible_excluding_c"})
    elif family == "B_motor_projecting_random":
        pool = np.flatnonzero(world.eligible_motor_projecting)
        chosen = rng.choice(pool, size=N_CANDIDATES, replace=False)
        meta.update({"pool_size": int(pool.size), "pool": "motor_projecting_eligible"})
    elif family == "C_all_verified_excitatory_random":
        pool = np.flatnonzero(world.eligible_all_exc)
        chosen = rng.choice(pool, size=N_CANDIDATES, replace=False)
        meta.update({"pool_size": int(pool.size), "pool": "all_verified_excitatory_non_motor"})
    elif family == "D_rank_stratum_shuffled":
        order = ranked_order_from(np.flatnonzero(world.eligible_vnc), world.scores)
        pool = order[64:256]
        chosen = rng.choice(pool, size=N_CANDIDATES, replace=False)
        meta.update({"pool_size": int(pool.size), "pool": "ranks_65_256_by_motor_synapses"})
    else:
        chosen, meta = _matched_draw(world, rng, c_mask, meta)
    indices = np.sort(np.asarray(chosen, dtype=np.int64))
    if indices.size != N_CANDIDATES:
        raise RuntimeError(f"family {family} produced {indices.size} neurons")
    if np.unique(indices).size != indices.size:
        raise RuntimeError(f"family {family} produced duplicate neurons")
    if np.any(world.populations.motor_mask[indices]):
        raise RuntimeError(f"family {family} selected a motor neuron")
    if not np.all(world.eligible_all_exc[indices]):
        raise RuntimeError(f"family {family} selected a non-excitatory neuron")
    meta["node_indices"] = [int(value) for value in indices]
    meta["root_ids"] = [int(value) for value in world.graph.root_ids[indices]]
    meta["indices_sha256"] = digest_array(indices)
    return meta


def _matched_draw(
    world: World, rng: np.random.Generator, c_mask: np.ndarray, meta: dict
) -> tuple[np.ndarray, dict]:
    """Stratified draw; shortages are capped and topped up from the score bin."""
    code, strata = _strata(world)
    pool = np.flatnonzero(world.eligible_vnc & ~c_mask)
    c_codes = code(world.candidate_c)
    chosen: list[int] = []
    shortages: dict[str, int] = {}
    for stratum in np.unique(c_codes):
        need = int(np.count_nonzero(c_codes == stratum))
        members = pool[code(pool) == stratum]
        take = min(need, members.size)
        if take < need:
            shortages[str(int(stratum))] = int(need - take)
        if take:
            picked = rng.choice(members, size=take, replace=False)
            chosen.extend(int(value) for value in picked)
    top_up = 0
    remaining = N_CANDIDATES - len(chosen)
    if remaining > 0:
        used = np.asarray(chosen, dtype=np.int64)
        excluded = _as_mask(np.concatenate([world.candidate_c, used]), world.n_nodes)
        refill_pool = np.flatnonzero(world.eligible_vnc & ~excluded)
        if refill_pool.size < remaining:
            raise RuntimeError("matched family cannot reach the requested size")
        chosen.extend(
            int(value)
            for value in rng.choice(refill_pool, size=remaining, replace=False)
        )
        top_up = int(remaining)
    meta.update(
        {
            "pool_size": int(pool.size),
            "pool": "vnc_intrinsic_eligible_excluding_c",
            "strata": {
                "bin_edges_motor_synapses": strata["bin_edges"],
                "crossed_with": "cell_class present / absent",
                "c_counts": {
                    str(int(key)): int(np.count_nonzero(c_codes == key))
                    for key in np.unique(c_codes)
                },
            },
            "stratum_shortages": shortages,
            "top_up_neurons": top_up,
        }
    )
    return np.asarray(chosen, dtype=np.int64), meta


def family_candidates(world: World, family: str, draw_index: int) -> np.ndarray:
    """Indices only; used by tests and diagnostics."""
    return np.asarray(
        family_draw(world, family, draw_index)["node_indices"], dtype=np.int64
    )


def matching_diagnostics(world: World, indices: np.ndarray) -> dict:
    cc = world.nodes["cell_class"].notna().to_numpy()

    def block(values: np.ndarray) -> dict:
        return {
            "mean": float(np.mean(values)),
            "sd": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
        }

    out = {
        "motor_synapses": block(world.scores[indices].astype(float)),
        "in_degree": block(world.in_degree[indices].astype(float)),
        "out_degree": block(world.out_degree[indices].astype(float)),
        "cell_class_present_fraction": float(np.mean(cc[indices])),
        "n_neurons": int(indices.size),
    }
    c = world.candidate_c
    for field_name, values in (
        ("motor_synapses", world.scores.astype(float)),
        ("in_degree", world.in_degree.astype(float)),
        ("out_degree", world.out_degree.astype(float)),
    ):
        sd = float(np.std(values[c], ddof=1))
        diff = (float(np.mean(values[indices])) - float(np.mean(values[c]))) / (
            sd if sd > 0 else 1.0
        )
        out[f"standardized_difference_{field_name}"] = float(diff)
    out["standardized_difference_cell_class_present"] = float(
        (np.mean(cc[indices]) - np.mean(cc[c]))
        / (np.std(cc[c].astype(float), ddof=1) or 1.0)
    )
    return out


# ---------------------------------------------------------------------------
# condition execution
# ---------------------------------------------------------------------------


def condition_metrics(
    world: World,
    recorder,
    decisions,
    stimulated: np.ndarray,
    *,
    stim_start_ms: float,
    stim_end_ms: float,
    duration_ms: float,
) -> dict:
    counts = np.asarray(recorder.spike_counts(), dtype=np.int64)
    times = np.asarray(recorder.spike_times_ms, dtype=np.float64)
    motor = np.asarray(world.populations.motor_mask, dtype=bool)
    total = int(counts.sum())
    stim_mask = _as_mask(stimulated, world.n_nodes) if len(stimulated) else np.zeros(
        world.n_nodes, dtype=bool
    )
    non_stim = ~stim_mask

    def time_of(mask_indices: np.ndarray) -> float | None:
        if mask_indices.size == 0:
            return None
        return float(times[mask_indices].min())

    motor_spike_rows = np.flatnonzero(motor[np.asarray(recorder.spike_neuron_indices, dtype=np.int64)])
    per_action = {}
    for action in ACTION_POPULATIONS:
        mask = np.asarray(world.populations.mask(action), dtype=bool)
        size = int(mask.sum())
        spikes = int(counts[mask].sum())
        active = int(np.count_nonzero(counts[mask]))
        peak = max(
            (float(decision.scores[action]) for decision in decisions), default=0.0
        )
        per_action[action] = {
            "size": size,
            "spikes": spikes,
            "active_neurons": active,
            "active_fraction": round(active / size, 6) if size else 0.0,
            "spikes_per_active_neuron": round(spikes / active, 4) if active else 0.0,
            "peak_window_active_fraction": round(peak, 6),
            "mean_window_active_fraction": round(
                float(np.mean([decision.scores[action] for decision in decisions])),
                6,
            )
            if decisions
            else 0.0,
            "n_windows_at_activation_threshold": int(
                sum(
                    1
                    for decision in decisions
                    if decision.scores[action]
                    >= world.decoder_config.activation_threshold
                )
            ),
        }

    motor_times = np.sort(times[motor[np.asarray(recorder.spike_neuron_indices, dtype=np.int64)]])
    motor_indices = np.asarray(recorder.spike_neuron_indices, dtype=np.int64)[
        motor[np.asarray(recorder.spike_neuron_indices, dtype=np.int64)]
    ]
    peak_motor_spikes = 0
    peak_motor_neurons = 0
    for decision in decisions:
        low = np.searchsorted(motor_times, decision.window_start_ms, side="left")
        high = np.searchsorted(motor_times, decision.window_end_ms, side="left")
        peak_motor_spikes = max(peak_motor_spikes, int(high - low))
        if high > low:
            peak_motor_neurons = max(
                peak_motor_neurons, int(np.unique(motor_indices[low:high]).size)
            )

    states: dict[str, int] = {}
    for decision in decisions:
        states[decision.state] = states.get(decision.state, 0) + 1
    first_action = next(
        (float(decision.window_start_ms) for decision in decisions if not decision.neutral),
        None,
    )
    post = times[times >= stim_end_ms]
    pre = times[times < stim_start_ms]
    return {
        "n_spikes": total,
        "stimulated_spikes": int(counts[stim_mask].sum()),
        "non_stimulated_spikes": int(counts[non_stim].sum()),
        "active_neurons": int(np.count_nonzero(counts)),
        "stimulated_active_neurons": int(np.count_nonzero(counts[stim_mask])),
        "non_stimulated_active_neurons": int(np.count_nonzero(counts[non_stim])),
        "motor": {
            "size": int(motor.sum()),
            "spikes": int(counts[motor].sum()),
            "active_neurons": int(np.count_nonzero(counts[motor])),
            "active_fraction": round(
                float(np.count_nonzero(counts[motor])) / int(motor.sum()), 6
            ),
            "peak_window_spikes": int(peak_motor_spikes),
            "peak_window_active_neurons": int(peak_motor_neurons),
            "peak_window_active_fraction": round(
                peak_motor_neurons / int(motor.sum()), 6
            ),
        },
        "actions": per_action,
        "decoded_state_counts": dict(sorted(states.items())),
        "neutral_windows": int(states.get("NEUTRAL", 0)),
        "n_windows": len(decisions),
        "jump_windows": int(states.get("JUMP", 0)),
        "left_windows": int(states.get("LEFT", 0)),
        "right_windows": int(states.get("RIGHT", 0)),
        "first_non_neutral_window_ms": first_action,
        "time_to_first_motor_spike_ms": time_of(motor_spike_rows),
        "pre_stimulation_spikes": int(pre.size),
        "post_stimulation_spikes": int(post.size),
        "spike_time_min_ms": float(times.min()) if times.size else None,
        "spike_time_max_ms": float(times.max()) if times.size else None,
        "duration_ms": float(duration_ms),
    }


def execute(
    world: World,
    indices: Sequence[int] | None,
    *,
    policy: BancSynapsePolicy | None = None,
    current_pa: float = STIM_CURRENT_PA,
    stim_start_ms: float = STIM_START_MS,
    stim_end_ms: float = STIM_END_MS,
    duration_ms: float = DURATION_MS,
    dt_ms: float = DT_MS,
    seed: int = 0,
    background_pa: float = 0.0,
    noise_pa: float = 0.0,
    input_schedule=None,
    decode_start_ms: float = DECODE_START_MS,
    decode_end_ms: float = DECODE_END_MS,
    label: str = "",
) -> dict:
    started = time.perf_counter()
    idx = (
        np.empty(0, dtype=np.int64)
        if indices is None
        else np.unique(np.asarray(indices, dtype=np.int64))
    )
    if idx.size:
        motor = np.asarray(world.populations.motor_mask, dtype=bool)
        if np.any(motor[idx]):
            raise ValueError("stimulation must never target motor neurons")
        if int(idx.max()) >= world.n_nodes:
            raise ValueError("stimulation index outside the graph")
    stimulation = None
    if idx.size:
        stimulation = BancStimulation(
            idx, float(current_pa), float(stim_start_ms), float(stim_end_ms), label=label
        )
    simulator = BancSimulator(
        world.graph,
        policy or world.policy,
        neuron_params=world.neuron_params,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        seed=seed,
        background_current_pa=background_pa,
        noise_std_pa=noise_pa,
        stimulation=stimulation,
        input_schedule=input_schedule,
        max_recorded_spikes=MAX_RECORDED_SPIKES,
    )
    result: BancSimulationResult = simulator.run()
    adapter = BancActivityAdapter(
        result.recorder, world.populations, graph_threshold=world.graph.threshold
    )
    decoder = MotorDecoder(world.populations, world.decoder_config)
    decisions = adapter.decode(decoder, decode_start_ms, decode_end_ms)
    stimulated = (
        idx
        if input_schedule is None
        else np.asarray(input_schedule.stimulated_indices, dtype=np.int64)
    )
    metrics = condition_metrics(
        world,
        result.recorder,
        decisions,
        stimulated,
        stim_start_ms=stim_start_ms,
        stim_end_ms=stim_end_ms,
        duration_ms=duration_ms,
    )
    counts = np.asarray(result.recorder.spike_counts(), dtype=np.int64)
    motor_counts = counts[np.asarray(world.populations.motor_mask, dtype=bool)]
    return {
        "label": label,
        "n_stimulated": int(stimulated.size),
        "current_pa": None if not idx.size else float(current_pa),
        "stimulation_window_ms": [float(stim_start_ms), float(stim_end_ms)],
        "seed": int(seed),
        "metrics": metrics,
        "motor_spike_counts": [int(value) for value in motor_counts],
        "spike_hash": spike_hash(result.recorder),
        "decision_hash": digest_json([decision.as_dict() for decision in decisions]),
        "decisions": [decision.as_dict() for decision in decisions],
        "activity_summary": result.summary["activity"],
        "activity_by_stimulation": result.summary["activity_by_stimulation"],
        "synaptic_transmission": result.summary["synaptic_transmission"],
        "diagnostics": result.summary["diagnostics"],
        "memory": result.summary["memory"],
        "process_memory": process_memory(),
        "simulation": result.summary["simulation"],
        "wall_time_s": round(time.perf_counter() - started, 3),
    }


def compact(record: dict) -> dict:
    """Drop the bulky per-window records from a stored condition."""
    keep = {
        key: value
        for key, value in record.items()
        if key not in {"decisions"}
    }
    keep["decision_states"] = [
        {
            "window_start_ms": item["window_start_ms"],
            "decoded_state": item["decoded_state"],
            "scores": item["scores"],
        }
        for item in record.get("decisions", [])
    ]
    return keep


# ---------------------------------------------------------------------------
# weight and sign variants
# ---------------------------------------------------------------------------


class GraphLocalTargetNorm:
    """`count / in_synapse_sum(dst)` approximation, capped.

    The dataset's ``post_count`` column is not present in the repository, so
    this uses the threshold-graph in-synapse sum instead. It is an
    approximation and is labelled as such.
    """

    name = "target_normalized_graph_local"

    def __init__(self, graph, scale_pa: float = 150.0, cap_pa: float | None = 300.0):
        self.in_sum = np.bincount(
            np.asarray(graph.edge_dst, dtype=np.int64),
            weights=np.asarray(graph.edge_weight, dtype=np.float64),
            minlength=graph.n_nodes,
        ).astype(np.float32)
        self.edge_dst = np.asarray(graph.edge_dst, dtype=np.int64)
        self.scale_pa = float(scale_pa)
        self.cap_pa = None if cap_pa is None else float(cap_pa)

    def apply(self, counts: np.ndarray) -> np.ndarray:
        base = np.asarray(counts, dtype=np.float32)
        denominator = self.in_sum[self.edge_dst]
        denominator = np.where(denominator > 0, denominator, np.float32(1.0))
        weights = base / denominator * np.float32(self.scale_pa)
        if self.cap_pa is not None:
            np.minimum(weights, np.float32(self.cap_pa), out=weights)
        return weights.astype(np.float32)

    def describe(self) -> dict:
        return {
            "transform": self.name,
            "scale_pa": self.scale_pa,
            "cap_pa": self.cap_pa,
            "normalisation": (
                "count / sum of in-edge synapse counts in the threshold-5 graph; "
                "an approximation of count/post_count, which is unavailable"
            ),
            "weight_source": "integer synapse count (`count`); `norm` is never used",
        }


def policy_with_weight(world: World, weight_policy) -> BancSynapsePolicy:
    return build_synapse_policy(
        world.graph, world.nodes, world.policy.sign_policy, weight_policy
    )


def policy_with_sign(world: World, sign_policy: SignPolicy) -> BancSynapsePolicy:
    return build_synapse_policy(
        world.graph, world.nodes, sign_policy, world.policy.weight_policy
    )


def reversed_from_graph(
    world: World,
    policy: BancSynapsePolicy,
    *,
    source_indices: np.ndarray | None = None,
) -> tuple[BancSynapsePolicy, int]:
    """Swap exc/inh weights globally or for edges whose source is in a set."""
    exc = np.asarray(policy.edge_exc_weight).copy()
    inh = np.asarray(policy.edge_inh_weight).copy()
    if source_indices is None:
        new_exc, new_inh = inh, exc
        flipped = int(np.count_nonzero(exc) + np.count_nonzero(inh))
    else:
        src = np.asarray(world.graph.edge_src, dtype=np.int64)
        mask = np.isin(src, np.asarray(source_indices, dtype=np.int64))
        new_exc = exc.copy()
        new_inh = inh.copy()
        new_exc[mask] = inh[mask]
        new_inh[mask] = exc[mask]
        flipped = int(np.count_nonzero(mask))
    updated = replace(policy, edge_exc_weight=new_exc, edge_inh_weight=new_inh)
    return updated, flipped


def aggregate_out_weight(world: World, policy: BancSynapsePolicy, indices: np.ndarray) -> float:
    src = np.asarray(world.graph.edge_src, dtype=np.int64)
    mask = np.isin(src, np.asarray(indices, dtype=np.int64))
    total = np.asarray(policy.edge_exc_weight)[mask].sum(dtype=np.float64) + np.asarray(
        policy.edge_inh_weight
    )[mask].sum(dtype=np.float64)
    return float(total)


# ---------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------


def summary_stats(values: Iterable[float]) -> dict:
    numbers = [float(value) for value in values]
    if not numbers:
        return {"n": 0}
    ordered = sorted(numbers)
    mean = statistics.fmean(numbers)
    sd = statistics.stdev(numbers) if len(numbers) > 1 else 0.0
    q1, q3 = np.quantile(ordered, [0.25, 0.75])
    return {
        "n": len(numbers),
        "mean": round(mean, 6),
        "sd": round(float(sd), 6),
        "median": round(float(statistics.median(numbers)), 6),
        "q1": round(float(q1), 6),
        "q3": round(float(q3), 6),
        "min": round(ordered[0], 6),
        "max": round(ordered[-1], 6),
    }


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denominator = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(
    values: Sequence[float], *, n_resamples: int = 10_000, seed: int = SEED_ROOT
) -> dict:
    numbers = np.asarray(list(values), dtype=np.float64)
    if numbers.size == 0:
        return {"low": None, "high": None}
    rng = np.random.default_rng(seed)
    means = rng.choice(numbers, size=(n_resamples, numbers.size), replace=True).mean(
        axis=1
    )
    return {
        "low": round(float(np.quantile(means, 0.025)), 6),
        "high": round(float(np.quantile(means, 0.975)), 6),
    }


def cliffs_delta(reference: float, sample: Sequence[float]) -> float:
    values = np.asarray(list(sample), dtype=np.float64)
    if values.size == 0:
        return 0.0
    greater = float(np.count_nonzero(values < reference)) / values.size
    less = float(np.count_nonzero(values > reference)) / values.size
    return greater - less


def empirical_p_greater(observed: float, null: Sequence[float]) -> float:
    values = np.asarray(list(null), dtype=np.float64)
    return (1.0 + float(np.count_nonzero(values >= observed))) / (1.0 + values.size)


def empirical_p_two_sided(observed: float, null: Sequence[float]) -> float:
    values = np.asarray(list(null), dtype=np.float64)
    greater = (1.0 + float(np.count_nonzero(values >= observed))) / (1.0 + values.size)
    less = (1.0 + float(np.count_nonzero(values <= observed))) / (1.0 + values.size)
    return min(1.0, 2.0 * min(greater, less))


def empirical_percentile(observed: float, null: Sequence[float]) -> float:
    values = np.asarray(list(null), dtype=np.float64)
    if values.size == 0:
        return float("nan")
    return float(np.count_nonzero(values < observed)) / values.size


def hedges_g(reference: float, sample: Sequence[float]) -> float | None:
    values = np.asarray(list(sample), dtype=np.float64)
    if values.size < 2:
        return None
    sd = float(np.std(values, ddof=1))
    if sd == 0:
        return None
    return float((reference - float(np.mean(values))) / sd)


def holm(pvalues: Mapping[str, float]) -> dict:
    items = sorted(pvalues.items(), key=lambda item: item[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, value) in enumerate(items):
        candidate = min(1.0, (m - rank) * float(value))
        running = max(running, candidate)
        adjusted[name] = round(running, 8)
    return {
        "adjusted": adjusted,
        "rejected": {
            name: bool(value <= 0.05) for name, value in adjusted.items()
        },
        "alpha": 0.05,
        "method": "Holm-Bonferroni",
    }


def permutation_test(
    a: Sequence[float], b: Sequence[float], *, n_permutations: int = 10_000, seed: int = SEED_ROOT
) -> dict:
    left = np.asarray(list(a), dtype=np.float64)
    right = np.asarray(list(b), dtype=np.float64)
    if left.size == 0 or right.size == 0:
        return {"p_value": None, "observed_difference": None}
    observed = float(np.mean(left) - np.mean(right))
    pooled = np.concatenate([left, right])
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_permutations):
        permuted = rng.permutation(pooled)
        difference = float(np.mean(permuted[: left.size]) - np.mean(permuted[left.size :]))
        if abs(difference) >= abs(observed):
            count += 1
    return {
        "p_value": (1.0 + count) / (1.0 + n_permutations),
        "observed_difference": observed,
        "n_permutations": n_permutations,
    }


def integrity_snapshot() -> dict:
    baseline = json.loads(BASELINE_INTEGRITY.read_text(encoding="utf-8"))
    failures = []
    for relative, expected in baseline.items():
        path = PROJECT_ROOT / relative
        if expected is None:
            continue
        if not path.is_file():
            failures.append({"path": relative, "reason": "missing"})
            continue
        if path.stat().st_size != expected["bytes"]:
            failures.append({"path": relative, "reason": "size"})
            continue
        if sha256_file(path) != expected["sha256"]:
            failures.append({"path": relative, "reason": "hash"})
    return {
        "checked": sum(1 for value in baseline.values() if value is not None),
        "failures": failures,
        "pass": not failures,
    }


def jsonl_append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


def jsonl_load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records
