"""Controlled synthetic cued-response task for Phase 5E.

SCIENTIFIC STATUS
    This task is a computational construct built to exercise the implemented
    three-factor rule. Success on it is not evidence of learning in a fly, not
    a biological experiment and not a measurement of any synaptic process. A
    cue is one stimulated neuron population; the designated response is a
    declared arbitrary mapping. The substrate is a small synthetic graph, never
    a connectome and never a read of ``datasets/``.

Protocol
    Each episode stimulates exactly one cue population. Cue neurons receive
    brief pulses whose onsets are jittered per trial, so different presynaptic
    spikes are coincident with the response across trials. The four action
    neurons (one per cue) receive a priming current followed by a constant
    holding current. A trial is successful when the designated action neuron
    spikes before the response deadline. The reward (+1) is returned at that
    spike step, so only the eligibility tags created by the coincident cue
    packet are updated. A miss returns a declared zero reward and changes no
    weight. This is a conditioned-response task: it measures whether the
    designated response becomes faster, not whether the network selects an
    action in competition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from brain.banc_graph import BancConnectome
from brain.banc_synapse_policy import (
    BancSynapsePolicy,
    SignPolicy,
    WeightPolicy,
    build_synapse_policy,
)

CONNECTIVITIES = ("complete", "random")


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _integer(value, name: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    number = int(value)
    if number < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return number


@dataclass(frozen=True)
class TaskConfig:
    """Declared parameters of the cued-response task."""

    n_cues: int = 4
    cue_neurons: int = 8
    action_neurons: int = 1
    threshold: int = 1
    min_count: int = 1
    max_count: int = 5
    weight_scale_pa: float = 5.0
    connectivity: str = "complete"
    edge_probability: float = 0.5
    cue_current_pa: float = 600.0
    action_prime_current_pa: float = 600.0
    action_prime_end_ms: float = 5.0
    action_background_pa: float = 145.0
    pulse_onset_min_ms: float = 1.0
    pulse_onset_max_ms: float = 7.0
    pulse_duration_ms: float = 6.0
    response_deadline_ms: float = 13.5
    duration_ms: float = 24.0
    dt_ms: float = 0.5
    noise_std_pa: float = 8.0
    reward_correct: float = 1.0
    reward_incorrect: float = 0.0
    tau_exc_ms: float = 20.0
    tau_inh_ms: float = 8.0
    delay_ms: float = 1.0

    def __post_init__(self) -> None:
        for name in (
            "n_cues",
            "cue_neurons",
            "action_neurons",
            "threshold",
            "min_count",
            "max_count",
        ):
            object.__setattr__(self, name, _integer(getattr(self, name), name))
        if self.n_cues < 2:
            raise ValueError("n_cues must be at least 2")
        if self.min_count > self.max_count:
            raise ValueError("min_count must not exceed max_count")
        if self.connectivity not in CONNECTIVITIES:
            raise ValueError(f"connectivity must be one of {CONNECTIVITIES}")
        probability = _finite(self.edge_probability, "edge_probability")
        if not 0.0 < probability <= 1.0:
            raise ValueError("edge_probability must lie in (0, 1]")
        object.__setattr__(self, "edge_probability", probability)
        for name in (
            "weight_scale_pa",
            "action_prime_end_ms",
            "pulse_onset_min_ms",
            "pulse_onset_max_ms",
            "pulse_duration_ms",
            "response_deadline_ms",
            "duration_ms",
            "dt_ms",
            "tau_exc_ms",
            "tau_inh_ms",
            "delay_ms",
        ):
            number = _finite(getattr(self, name), name)
            if number < 0 or (
                name not in ("pulse_onset_min_ms", "pulse_onset_max_ms", "delay_ms")
                and number == 0
            ):
                raise ValueError(f"{name} must be non-negative and nonzero where required")
            object.__setattr__(self, name, number)
        for name in (
            "cue_current_pa",
            "action_prime_current_pa",
            "action_background_pa",
            "noise_std_pa",
            "reward_correct",
            "reward_incorrect",
        ):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        if self.noise_std_pa < 0:
            raise ValueError("noise_std_pa must be non-negative")
        if self.pulse_onset_max_ms < self.pulse_onset_min_ms:
            raise ValueError("pulse_onset_max_ms must not precede the minimum")
        if self.action_prime_end_ms >= self.response_deadline_ms:
            raise ValueError("the action prime must end before the response deadline")
        if self.pulse_onset_max_ms + self.pulse_duration_ms > self.duration_ms:
            raise ValueError("the latest cue pulse must fit inside the episode")
        if not 0 < self.response_deadline_ms < self.duration_ms:
            raise ValueError("the response deadline must lie inside the episode")
        if int(np.ceil(self.response_deadline_ms / self.dt_ms)) >= self.n_steps:
            raise ValueError("the response deadline must precede the last step")

    @classmethod
    def from_config(cls, payload: Mapping) -> "TaskConfig":
        values = {
            field.name: payload[field.name]
            for field in fields(cls)
            if field.name in payload
        }
        return cls(**values)

    @property
    def n_nodes(self) -> int:
        return self.n_cues * (self.cue_neurons + self.action_neurons)

    @property
    def n_steps(self) -> int:
        return int(round(self.duration_ms / self.dt_ms))

    @property
    def deadline_step(self) -> int:
        return int(np.ceil(self.response_deadline_ms / self.dt_ms))

    def describe(self) -> dict:
        return {
            "n_cues": self.n_cues,
            "n_actions": self.n_cues,
            "cue_neurons": self.cue_neurons,
            "action_neurons": self.action_neurons,
            "n_nodes": self.n_nodes,
            "threshold": self.threshold,
            "synapse_count_range": [self.min_count, self.max_count],
            "weight_scale_pa": self.weight_scale_pa,
            "connectivity": self.connectivity,
            "edge_probability": self.edge_probability,
            "cue_current_pa": self.cue_current_pa,
            "pulse_onset_range_ms": [
                self.pulse_onset_min_ms,
                self.pulse_onset_max_ms,
            ],
            "pulse_duration_ms": self.pulse_duration_ms,
            "action_prime_current_pa": self.action_prime_current_pa,
            "action_prime_end_ms": self.action_prime_end_ms,
            "action_background_pa": self.action_background_pa,
            "response_deadline_ms": self.response_deadline_ms,
            "duration_ms": self.duration_ms,
            "dt_ms": self.dt_ms,
            "noise_std_pa": self.noise_std_pa,
            "reward_correct": self.reward_correct,
            "reward_incorrect": self.reward_incorrect,
            "success_rule": (
                "the designated action neuron spikes before the response "
                "deadline; a miss is rewarded with the declared miss value"
            ),
            "non_claims": (
                "a synthetic conditioned-response task; correct and incorrect "
                "outcomes are declared, not observed in an animal"
            ),
        }


@dataclass(frozen=True)
class TaskSubstrate:
    """Graph, policy and cue/action index groups for one task instance."""

    graph: BancConnectome
    policy: BancSynapsePolicy
    cue_indices: tuple[np.ndarray, ...]
    action_indices: tuple[np.ndarray, ...]
    config: TaskConfig
    seed: int

    def __post_init__(self) -> None:
        n_cues = self.config.n_cues
        if len(self.cue_indices) != n_cues or len(self.action_indices) != n_cues:
            raise ValueError("one cue and one action population per cue are required")
        all_indices = np.concatenate(self.cue_indices + self.action_indices)
        if all_indices.size != self.graph.n_nodes:
            raise ValueError("cue and action populations must cover every node")
        if np.unique(all_indices).size != all_indices.size:
            raise ValueError("cue and action populations must be disjoint")

    @property
    def correct_action(self) -> tuple[int, ...]:
        return tuple(range(self.config.n_cues))

    def describe(self) -> dict:
        exc = np.asarray(self.policy.edge_exc_weight, dtype=np.float64)
        counts = np.asarray(self.graph.edge_weight, dtype=np.int64)
        return {
            "seed": self.seed,
            "graph": {
                "n_nodes": int(self.graph.n_nodes),
                "n_edges": int(self.graph.n_edges),
                "n_synapses": int(counts.sum()),
                "threshold": int(self.graph.threshold),
            },
            "populations": {
                "cue_sizes": [int(index.size) for index in self.cue_indices],
                "action_sizes": [int(index.size) for index in self.action_indices],
                "mapping": "cue i -> action i",
            },
            "weights": {
                "excitatory_edges": int(np.count_nonzero(exc)),
                "inhibitory_edges": int(
                    np.count_nonzero(self.policy.edge_inh_weight)
                ),
                "sum_pa": round(float(exc.sum()), 6),
                "min_pa": round(float(exc.min(initial=0.0)), 6),
                "max_pa": round(float(exc.max(initial=0.0)), 6),
            },
            "config": self.config.describe(),
        }


def build_task_substrate(config: TaskConfig, *, seed: int = 20261114) -> TaskSubstrate:
    """Build the deterministic task graph and its signed edge weights."""
    rng = np.random.default_rng(int(seed))
    n_cue_nodes = config.n_cues * config.cue_neurons
    n_nodes = config.n_nodes
    cue_indices = tuple(
        np.arange(
            cue * config.cue_neurons,
            (cue + 1) * config.cue_neurons,
            dtype=np.int64,
        )
        for cue in range(config.n_cues)
    )
    action_indices = tuple(
        np.arange(
            n_cue_nodes + cue * config.action_neurons,
            n_cue_nodes + (cue + 1) * config.action_neurons,
            dtype=np.int64,
        )
        for cue in range(config.n_cues)
    )
    action_nodes = np.arange(n_cue_nodes, n_nodes, dtype=np.int64)

    pairs: list[tuple[int, int]] = []
    for cue in range(config.n_cues):
        for source in cue_indices[cue]:
            for target in action_nodes:
                if (
                    config.connectivity == "complete"
                    or rng.random() < config.edge_probability
                ):
                    pairs.append((int(source), int(target)))
    if not pairs:
        raise ValueError("the task substrate has no cue -> action edges")
    ordered = np.array(sorted(pairs), dtype=np.int32)
    edge_src = ordered[:, 0]
    edge_dst = ordered[:, 1]
    n_edges = int(ordered.shape[0])
    edge_weight = rng.integers(
        config.min_count, config.max_count + 1, size=n_edges
    ).astype(np.int32)

    out_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_src, minlength=n_nodes), out=out_indptr[1:])
    in_indptr = np.zeros(n_nodes + 1, dtype=np.int64)
    np.cumsum(np.bincount(edge_dst, minlength=n_nodes), out=in_indptr[1:])
    in_edge_idx = np.argsort(edge_dst, kind="stable").astype(np.int32)
    ordered_graph = BancConnectome(
        root_ids=np.arange(910_000, 910_000 + n_nodes, dtype=np.int64),
        out_indptr=out_indptr,
        edge_src=edge_src,
        edge_dst=edge_dst,
        edge_weight=edge_weight,
        in_indptr=in_indptr,
        in_edge_idx=in_edge_idx,
        threshold=config.threshold,
    )
    table = pd.DataFrame(
        {
            "banc_888_id": [str(value) for value in ordered_graph.root_ids],
            "node_index": np.arange(n_nodes),
            "neurotransmitter_verified": ["acetylcholine"] * n_nodes,
            "neurotransmitter_predicted": [None] * n_nodes,
        }
    )
    policy = build_synapse_policy(
        ordered_graph,
        table,
        SignPolicy(),
        WeightPolicy(
            transform="linear", scale_pa=config.weight_scale_pa, cap_pa=None
        ),
    )
    return TaskSubstrate(
        graph=ordered_graph,
        policy=policy,
        cue_indices=cue_indices,
        action_indices=action_indices,
        config=config,
        seed=int(seed),
    )


def derive_seed(master_seed: int, *keys: int) -> int:
    """A deterministic 32-bit seed from an independent SeedSequence stream."""
    sequence = np.random.SeedSequence([int(master_seed), *[int(k) for k in keys]])
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


class CueActionSchedule:
    """Per-trial cue pulses plus the declared action prime and holding drive."""

    def __init__(
        self,
        cue_indices: Sequence[int],
        action_indices: Sequence[int],
        onsets_ms: Sequence[float],
        *,
        pulse_duration_ms: float,
        cue_current_pa: float,
        action_prime_current_pa: float,
        action_prime_end_ms: float,
        action_background_pa: float,
        duration_ms: float,
    ) -> None:
        self.cue_indices = np.asarray(cue_indices, dtype=np.int64)
        self.action_indices = np.asarray(action_indices, dtype=np.int64)
        self.onsets_ms = np.asarray(onsets_ms, dtype=np.float64).ravel()
        if self.cue_indices.size == 0:
            raise ValueError("the schedule must target at least one cue neuron")
        if self.action_indices.size == 0:
            raise ValueError("the schedule must target at least one action neuron")
        if self.onsets_ms.size != self.cue_indices.size:
            raise ValueError("one onset is required per cue neuron")
        if not np.all(np.isfinite(self.onsets_ms)) or np.any(self.onsets_ms < 0):
            raise ValueError("onsets must be finite and non-negative")
        self.pulse_duration_ms = float(pulse_duration_ms)
        if self.pulse_duration_ms <= 0:
            raise ValueError("pulse_duration_ms must be positive")
        if float(self.onsets_ms.max()) + self.pulse_duration_ms > float(duration_ms):
            raise ValueError("a cue pulse extends beyond the episode")
        self.cue_current_pa = float(cue_current_pa)
        self.action_prime_current_pa = float(action_prime_current_pa)
        self.action_prime_end_ms = float(action_prime_end_ms)
        self.action_background_pa = float(action_background_pa)
        self.stimulated_indices = np.unique(
            np.concatenate([self.cue_indices, self.action_indices])
        )

    def apply(self, step: int, time_ms: float, current: np.ndarray) -> None:
        del step
        active = (self.onsets_ms <= time_ms) & (
            time_ms < self.onsets_ms + self.pulse_duration_ms
        )
        if active.any():
            current[self.cue_indices[active]] += self.cue_current_pa
        if time_ms < self.action_prime_end_ms:
            current[self.action_indices] += self.action_prime_current_pa
        else:
            current[self.action_indices] += self.action_background_pa

    def describe(self) -> dict:
        return {
            "kind": "cued_action_schedule",
            "n_cue_neurons": int(self.cue_indices.size),
            "n_action_neurons": int(self.action_indices.size),
            "onsets_ms": [round(float(value), 6) for value in self.onsets_ms],
            "pulse_duration_ms": self.pulse_duration_ms,
            "cue_current_pa": self.cue_current_pa,
            "action_prime_current_pa": self.action_prime_current_pa,
            "action_prime_end_ms": self.action_prime_end_ms,
            "action_background_pa": self.action_background_pa,
        }


class TargetResponseController:
    """Reward the designated action's spike; record the first action to spike."""

    def __init__(
        self,
        action_indices: Sequence[Sequence[int]],
        target_action: int,
        *,
        deadline_step: int,
        reward_correct: float,
        reward_incorrect: float,
        reward_shuffler=None,
        dt_ms: float = 0.5,
    ) -> None:
        self.action_indices = tuple(
            np.asarray(indices, dtype=np.int64) for indices in action_indices
        )
        self.target_action = int(target_action)
        if not 0 <= self.target_action < len(self.action_indices):
            raise ValueError("target_action is outside the action set")
        self.deadline_step = int(deadline_step)
        if self.deadline_step < 1:
            raise ValueError("deadline_step must be positive")
        self.reward_correct = float(reward_correct)
        self.reward_incorrect = float(reward_incorrect)
        if reward_shuffler is not None and not callable(reward_shuffler):
            raise ValueError("reward_shuffler must be callable")
        self.reward_shuffler = reward_shuffler
        self.dt_ms = float(dt_ms)
        if self.dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        self.reset()

    def reset(self) -> None:
        self.decided = False
        self.hit = False
        self.rewarded = False
        self.timed_out = False
        self.first_action: int | None = None
        self.response_step: int | None = None
        self.reward = 0.0

    @property
    def correct(self) -> bool:
        return bool(self.hit)

    def __call__(self, step, time_ms, spikes, simulator=None):
        del time_ms, simulator
        spiked = np.asarray(spikes, dtype=np.int64).ravel()
        if spiked.size:
            if self.first_action is None:
                for action, indices in enumerate(self.action_indices):
                    if indices.size and np.intersect1d(
                        indices, spiked, assume_unique=True
                    ).size:
                        self.first_action = action
                        break
            if not self.rewarded and np.intersect1d(
                self.action_indices[self.target_action],
                spiked,
                assume_unique=True,
            ).size:
                self.hit = True
                self.decided = True
                self.rewarded = True
                self.response_step = int(step)
                if self.reward_shuffler is not None:
                    self.reward = float(self.reward_shuffler())
                else:
                    self.reward = self.reward_correct
                return self.reward
        if not self.decided and step >= self.deadline_step:
            self.decided = True
            self.timed_out = True
            if not self.rewarded:
                self.rewarded = True
                self.reward = self.reward_incorrect
                return self.reward
        return None

    def outcome(self) -> dict:
        return {
            "correct_action": self.target_action,
            "chosen_action": self.first_action,
            "hit": bool(self.hit),
            "timed_out": bool(self.timed_out),
            "correct": bool(self.hit),
            "response_step": self.response_step,
            "response_ms": (
                None if self.response_step is None else self.response_step * self.dt_ms
            ),
            "reward": float(self.reward),
        }


class DelayedReward:
    """Deliver a controller reward after a declared delay in steps.

    A reward is computed by the wrapped controller at the step where the
    outcome occurs and is released ``delay_steps`` later. The update therefore
    uses the eligibility traces that are still active at delivery, which is the
    declared three-factor convention. Rewards still queued when the episode ends
    are counted as dropped, never silently discarded.
    """

    def __init__(self, controller, delay_steps: int) -> None:
        self.controller = controller
        self.delay_steps = int(delay_steps)
        if self.delay_steps < 0:
            raise ValueError("delay_steps must be non-negative")
        self.reset()

    def reset(self) -> None:
        self.controller.reset()
        self._pending: list[tuple[int, float]] = []
        self.n_delivered = 0
        self.n_dropped = 0

    def __call__(self, step, time_ms, spikes, simulator=None):
        value = self.controller(step, time_ms, spikes, simulator)
        if value is not None:
            if self.delay_steps == 0:
                self.n_delivered += 1
                return float(value)
            self._pending.append((int(step) + self.delay_steps, float(value)))
        if self._pending:
            due = [item for item in self._pending if item[0] <= step]
            if due:
                self._pending = [item for item in self._pending if item[0] > step]
                self.n_delivered += len(due)
                return float(due[0][1])
        return None

    def finalize(self) -> None:
        self.n_dropped += len(self._pending)
        self._pending = []

    def outcome(self) -> dict:
        return self.controller.outcome()


def load_task_config(path: str | Path) -> tuple[TaskConfig, dict]:
    """Load ``configs/plasticity_task.yaml`` with declared validation."""
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("task config must be a mapping")
    task_section = raw.get("task", {})
    if not isinstance(task_section, dict):
        raise ValueError("task must be a mapping")
    task = TaskConfig.from_config(task_section)
    experiment = raw.get("experiment", {})
    if not isinstance(experiment, dict):
        raise ValueError("experiment must be a mapping")
    settings = {
        "train_episodes": _integer(
            experiment.get("train_episodes", 160), "experiment.train_episodes"
        ),
        "eval_episodes": _integer(
            experiment.get("eval_episodes", 40), "experiment.eval_episodes"
        ),
        "replicates": _integer(
            experiment.get("replicates", 3), "experiment.replicates"
        ),
        "master_seed": _integer(
            experiment.get("master_seed", 20261114), "experiment.master_seed", minimum=0
        ),
        "eta": _finite(experiment.get("eta", 1.0), "experiment.eta"),
        "criterion_window": _integer(
            experiment.get("criterion_window", 20), "experiment.criterion_window"
        ),
        "criterion_success": _finite(
            experiment.get("criterion_success", 0.75),
            "experiment.criterion_success",
        ),
        "eval_checkpoints": [
            int(value) for value in experiment.get("eval_checkpoints", [0, 40, 80, 120, 160])
        ],
        "checkpoint_condition": str(experiment.get("checkpoint_condition", "B")),
        "raw": raw,
    }
    if settings["eta"] < 0:
        raise ValueError("experiment.eta must be non-negative")
    if not 0.0 <= settings["criterion_success"] <= 1.0:
        raise ValueError("experiment.criterion_success must lie in [0, 1]")
    checkpoints = settings["eval_checkpoints"]
    if (
        not checkpoints
        or checkpoints[0] != 0
        or checkpoints[-1] != settings["train_episodes"]
        or checkpoints != sorted(set(checkpoints))
    ):
        raise ValueError(
            "experiment.eval_checkpoints must start at 0, end at train_episodes "
            "and be strictly increasing"
        )
    return task, settings
