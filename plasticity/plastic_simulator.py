"""Independent simulator for the three-factor plastic BANC pathway.

SCIENTIFIC STATUS
    Every quantity produced here is a model output. A learned weight is a
    transformation of a structural synapse count changed by a declared
    computational rule; it is not a biological measurement.

The loop below mirrors ``brain.banc_simulator.BancSimulator.run`` operation for
operation: the same RNG call order, current assembly, LIF integration, spike
recording and propagation. The only additions are the trace/tag update after
propagation and an optional reward-event update. Consequently, with
``eta = 0`` and the same seed and inputs, the recorded spikes are byte-for-byte
identical to the fixed-weight simulator; :func:`spike_hash` makes that
contract verifiable rather than assumed.

``brain/`` is not modified. ``BancSimulator`` stays the fixed-weight oracle and
this class is a separate pathway.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from brain.banc_simulator import BancStimulation
from brain.neural_activity import SpikeRecorder
from brain.neuron_model import LIFParameters, LIFPopulation

from .diagnostics import (
    memory_breakdown,
    spike_hash,
    summarize_updates,
    trace_diagnostics,
    weight_diagnostics,
)
from .engine import PlasticityEngine
from .plastic_synapses import PlasticSignedSynapses
from .rules import RuleConfig, ThreeFactorRule, UpdateReport
from .traces import TraceConfig
from .weights import WeightBounds, WeightState


@dataclass
class PlasticSimulationResult:
    """Recorder, learned state and diagnostics from one plastic run."""

    summary: dict
    recorder: SpikeRecorder
    duration_ms: float
    dt_ms: float
    n_steps: int
    seed: int
    threshold: int
    stimulation: BancStimulation | None
    weight_state: WeightState = field(repr=False)
    update_reports: tuple[UpdateReport, ...] = ()
    spike_hash: str = ""

    def save(self, out_dir: Path) -> dict:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        activity_path = out_dir / "activity.npz"
        self.recorder.save(activity_path, self.duration_ms)
        metadata_path = out_dir / "simulation_metadata.json"
        metadata_path.write_text(
            json.dumps(self.summary, indent=1), encoding="utf-8"
        )
        return {
            "activity": str(activity_path),
            "metadata": str(metadata_path),
        }


class PlasticSimulator:
    """Time-stepped spiking simulation with independently owned plastic weights."""

    def __init__(
        self,
        graph,
        policy,
        *,
        weight_state: WeightState | None = None,
        bounds: WeightBounds | None = None,
        rule: ThreeFactorRule | None = None,
        rule_config: RuleConfig | None = None,
        trace_config: TraceConfig | None = None,
        enable_traces: bool = True,
        prune_interval_steps: int | None = None,
        reward_provider=None,
        step_callback=None,
        predictor=None,
        state_fn=None,
        neuron_params: LIFParameters | None = None,
        dt_ms: float = 0.5,
        duration_ms: float = 100.0,
        seed: int = 0,
        background_current_pa: float = 0.0,
        noise_std_pa: float = 0.0,
        stimulation: BancStimulation | None = None,
        input_schedule=None,
        initial_potential_mv: float | None = None,
        max_recorded_spikes: int = 2_000_000,
        tau_exc_ms: float = 5.0,
        tau_inh_ms: float = 8.0,
        delay_ms: float = 1.0,
    ) -> None:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        if noise_std_pa < 0 or not np.isfinite(noise_std_pa):
            raise ValueError("noise_std_pa must be finite and non-negative")
        if not np.isfinite(background_current_pa):
            raise ValueError("background_current_pa must be finite")
        if (
            int(getattr(graph, "threshold", -1))
            != int(getattr(policy, "threshold", -2))
        ):
            raise ValueError("policy was built for a different graph threshold")
        if stimulation is not None and int(stimulation.indices.max()) >= graph.n_nodes:
            raise ValueError("stimulation index outside the graph")
        if input_schedule is not None:
            if not hasattr(input_schedule, "apply") or not hasattr(
                input_schedule, "stimulated_indices"
            ):
                raise TypeError(
                    "input_schedule must provide apply(step, time_ms, current) "
                    "and stimulated_indices"
                )
            indices = np.asarray(input_schedule.stimulated_indices, dtype=np.int64)
            if indices.size == 0:
                raise ValueError("input_schedule must target at least one neuron")
            if int(indices.max()) >= graph.n_nodes:
                raise ValueError("input schedule targets a neuron outside the graph")
        if reward_provider is not None and not hasattr(reward_provider, "step"):
            raise TypeError("reward_provider must provide step(step, time_ms, context)")
        if step_callback is not None and not callable(step_callback):
            raise TypeError("step_callback must be callable")
        if state_fn is not None and not callable(state_fn):
            raise TypeError("state_fn must be callable")

        self.graph = graph
        self.policy = policy
        if weight_state is None:
            weight_state = WeightState(graph, policy, bounds)
        elif not isinstance(weight_state, WeightState):
            raise ValueError("weight_state must be a WeightState")
        if weight_state.n_edges != int(graph.n_edges):
            raise ValueError("weight state and graph edge counts differ")
        self.weight_state = weight_state
        if rule is None:
            rule = ThreeFactorRule(
                rule_config or RuleConfig(eta=0.0), weight_state
            )
        elif not isinstance(rule, ThreeFactorRule):
            raise ValueError("rule must be a ThreeFactorRule")
        if rule.weight_state is not weight_state:
            raise ValueError("rule and simulator must share one weight state")
        self.rule = rule

        self.neuron_params = neuron_params or LIFParameters()
        self.dt_ms = float(dt_ms)
        self.duration_ms = float(duration_ms)
        self.seed = int(seed)
        self.background_current_pa = float(background_current_pa)
        self.noise_std_pa = float(noise_std_pa)
        self.stimulation = stimulation
        self.input_schedule = input_schedule
        self.initial_potential_mv = initial_potential_mv
        self.reward_provider = reward_provider
        self.step_callback = step_callback
        self.predictor = predictor
        self.state_fn = state_fn
        self.tau_exc_ms = float(tau_exc_ms)
        self.tau_inh_ms = float(tau_inh_ms)

        self.neurons = LIFPopulation(graph.n_nodes, self.neuron_params, dt_ms)
        self.synapses = PlasticSignedSynapses(
            graph,
            policy,
            weight_state,
            dt_ms,
            tau_exc_ms=tau_exc_ms,
            tau_inh_ms=tau_inh_ms,
            delay_ms=delay_ms,
        )
        self.engine = PlasticityEngine(
            graph,
            weight_state,
            rule,
            trace_config,
            dt_ms=self.dt_ms,
            delay_steps=self.synapses.delay_steps,
            enable_traces=enable_traces,
            prune_interval_steps=prune_interval_steps,
        )
        self.recorder = SpikeRecorder(graph.n_nodes, max_recorded_spikes)
        self._reports: list[UpdateReport] = []

    @property
    def n_neurons(self) -> int:
        return int(self.graph.n_nodes)

    @property
    def threshold(self) -> int:
        return int(self.graph.threshold)

    @property
    def update_reports(self) -> tuple[UpdateReport, ...]:
        return tuple(self._reports)

    @property
    def eta(self) -> float:
        return float(self.rule.eta)

    def reset(self) -> None:
        self.neurons.reset(self.initial_potential_mv)
        self.synapses.reset()
        self.recorder.reset()
        self.engine.reset()
        self._reports = []
        if self.reward_provider is not None and hasattr(
            self.reward_provider, "reset"
        ):
            self.reward_provider.reset()
        if self.step_callback is not None and hasattr(self.step_callback, "reset"):
            self.step_callback.reset()

    def _delta_t(self, step: int, time_ms: float, reward: float) -> float:
        if self.predictor is None:
            return float(reward)
        if self.state_fn is None:
            state, next_state = "episode", None
        else:
            state, next_state = self.state_fn(step, time_ms, reward)
        return float(self.predictor.learn(state, next_state, reward))

    def run(
        self, duration_ms: float | None = None
    ) -> PlasticSimulationResult:
        duration = self.duration_ms if duration_ms is None else float(duration_ms)
        if duration <= 0:
            raise ValueError("duration_ms must be positive")
        n_steps = int(round(duration / self.dt_ms))
        if n_steps < 1:
            raise ValueError("duration is shorter than one timestep")
        simulated_ms = n_steps * self.dt_ms
        self.reset()
        rng = np.random.default_rng(self.seed)
        n = self.n_neurons

        stim_start = stim_end = 0
        if self.stimulation is not None:
            stim_start = int(np.ceil(self.stimulation.start_ms / self.dt_ms))
            stim_end = int(np.ceil(self.stimulation.end_ms / self.dt_ms))

        cadence = self.rule.config.update_cadence
        transmitted = 0
        max_current = 0.0
        max_exc_synaptic = 0.0
        max_inh_synaptic = 0.0
        min_membrane = np.inf
        max_membrane = -np.inf
        started = time.perf_counter()

        for step in range(n_steps):
            self.synapses.advance()
            max_exc_synaptic = max(
                max_exc_synaptic,
                float(np.abs(self.synapses.excitatory_current_pa).max()),
            )
            max_inh_synaptic = max(
                max_inh_synaptic,
                float(np.abs(self.synapses.inhibitory_current_pa).max()),
            )

            if self.noise_std_pa > 0:
                current = rng.normal(0.0, self.noise_std_pa, n)
            else:
                current = np.zeros(n, dtype=np.float64)
            current += self.background_current_pa
            current += self.synapses.synaptic_current_pa
            if self.stimulation is not None and stim_start <= step < stim_end:
                current[self.stimulation.indices] += self.stimulation.current_pa
            if self.input_schedule is not None:
                self.input_schedule.apply(step, step * self.dt_ms, current)
            max_current = max(max_current, float(np.abs(current).max()))

            spikes = self.neurons.step(current)
            self.recorder.record(step, spikes, self.dt_ms)
            transmitted += self.synapses.propagate(spikes)

            self.engine.observe_step(
                step, spikes, self.synapses.last_active_edges
            )

            reward = None
            if self.step_callback is not None:
                value = self.step_callback(
                    step, step * self.dt_ms, spikes, self
                )
                if value is not None:
                    reward = float(value)
            if reward is None and self.reward_provider is not None:
                reward = self.reward_provider.step(
                    step, step * self.dt_ms, None
                )
            if reward is not None:
                report = self.engine.learn(
                    step, self._delta_t(step, step * self.dt_ms, float(reward))
                )
                if report is not None:
                    self._reports.append(report)
            elif cadence == "every_step":
                report = self.engine.learn(step, 0.0)
                if report is not None:
                    self._reports.append(report)

        membrane = self.neurons.membrane_potential
        if not np.all(np.isfinite(membrane)):
            raise FloatingPointError(
                "non-finite membrane state detected; reduce dt_ms or input currents"
            )
        min_membrane = min(min_membrane, float(membrane.min()))
        max_membrane = max(max_membrane, float(membrane.max()))
        runtime = time.perf_counter() - started
        invariants = self.weight_state.assert_invariants()
        summary = self._build_summary(
            simulated_ms,
            n_steps,
            runtime,
            transmitted,
            min_membrane,
            max_membrane,
            max_current,
            max_exc_synaptic,
            max_inh_synaptic,
            invariants,
        )
        return PlasticSimulationResult(
            summary=summary,
            recorder=self.recorder,
            duration_ms=simulated_ms,
            dt_ms=self.dt_ms,
            n_steps=n_steps,
            seed=self.seed,
            threshold=self.threshold,
            stimulation=self.stimulation,
            weight_state=self.weight_state,
            update_reports=tuple(self._reports),
            spike_hash=spike_hash(self.recorder),
        )

    def _build_summary(
        self,
        duration_ms: float,
        n_steps: int,
        runtime_s: float,
        transmitted: int,
        min_membrane_mv: float,
        max_membrane_mv: float,
        max_current_pa: float,
        max_exc_synaptic_pa: float,
        max_inh_synaptic_pa: float,
        invariants: dict,
    ) -> dict:
        activity = self.recorder.summary(duration_ms)
        weights = weight_diagnostics(
            self.weight_state, self._reports, invariants=invariants
        )
        return {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "simulation": {
                "pathway": "plastic_three_factor",
                "duration_ms": duration_ms,
                "dt_ms": self.dt_ms,
                "n_steps": n_steps,
                "seed": self.seed,
                "runtime_s": round(runtime_s, 4),
                "steps_per_second": round(n_steps / runtime_s, 1),
            },
            "graph": {
                "source": "BANC v888",
                "graph_threshold": self.threshold,
                "n_nodes": int(self.graph.n_nodes),
                "n_edges": int(self.graph.n_edges),
                "n_synapses": int(self.graph.n_synapses),
                "n_isolated": int(self.graph.n_isolated),
            },
            "model": {
                "neuron": asdict(self.neuron_params),
                "synapse": {
                    "tau_exc_ms": self.tau_exc_ms,
                    "tau_inh_ms": self.tau_inh_ms,
                    "effective_delay_ms": self.synapses.effective_delay_ms,
                    "delay_steps": int(self.synapses.delay_steps),
                    "weight_source": "structural synapse count (count), not norm",
                },
                "rule": self.rule.describe(),
            },
            "plasticity": {
                "weight_state": weights,
                "engine": self.engine.describe(),
                "traces": trace_diagnostics(self.engine),
                "updates": summarize_updates(self._reports),
            },
            "stimulation": (
                None
                if self.stimulation is None
                else {
                    "label": self.stimulation.label,
                    "n_neurons": int(len(self.stimulation.indices)),
                    "root_ids": [
                        int(value)
                        for value in self.graph.root_ids[self.stimulation.indices]
                    ],
                    "current_pa": self.stimulation.current_pa,
                    "start_ms": self.stimulation.start_ms,
                    "end_ms": self.stimulation.end_ms,
                }
            ),
            "activity": activity,
            "synaptic_transmission": {
                "spike_transmissions": int(transmitted),
                "transmissions_per_spike": round(
                    transmitted / max(1, activity["n_spikes"]), 3
                ),
            },
            "diagnostics": {
                "finite_state": True,
                "min_membrane_mv": round(min_membrane_mv, 4),
                "max_membrane_mv": round(max_membrane_mv, 4),
                "max_abs_total_current_pa": round(max_current_pa, 4),
                "max_excitatory_synaptic_current_pa": round(
                    max_exc_synaptic_pa, 4
                ),
                "max_inhibitory_synaptic_current_pa": round(
                    max_inh_synaptic_pa, 4
                ),
                "spike_hash": spike_hash(self.recorder),
            },
            "memory": memory_breakdown(self),
        }
