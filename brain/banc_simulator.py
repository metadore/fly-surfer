"""Time-stepped spiking simulation on a BANC threshold graph.

This is a separate pathway from :class:`brain.brain_simulator.BrainSimulator`:
the FAFB simulator derives transmitter signs inside
:class:`brain.synapse_model.SynapseModel`, which requires a FAFB graph
``vocabulary`` and ``nt_code``. BANC ships neither, so the signed edge weights
come from :mod:`brain.banc_synapse_policy` and the loop below uses them
directly.

The neuron model (:class:`brain.neuron_model.LIFPopulation`) and the spike
recorder (:class:`brain.neural_activity.SpikeRecorder`) are reused unchanged.

Timestep order (identical to the FAFB pathway)::

    deliver delayed synaptic input, decay currents
    add background noise and external stimulation
    integrate the LIF membrane and detect spikes
    record spikes at (step + 1) * dt_ms
    route spikes into the delay buffer

A spike emitted at the end of step ``k`` can therefore affect a postsynaptic
neuron no earlier than step ``k + 1``; with the default 1 ms delay and 0.5 ms
timestep the latency is two steps.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

from brain.banc_synapse_policy import BancSynapsePolicy
from brain.neural_activity import SpikeRecorder
from brain.neuron_model import LIFParameters, LIFPopulation


@dataclass(frozen=True)
class BancStimulation:
    """External current injected into a fixed set of local graph indices."""

    indices: np.ndarray
    current_pa: float
    start_ms: float
    end_ms: float
    label: str = "stimulation"

    def __post_init__(self) -> None:
        indices = np.unique(np.asarray(self.indices, dtype=np.int64))
        if indices.size == 0:
            raise ValueError("stimulation must target at least one neuron")
        if self.end_ms <= self.start_ms:
            raise ValueError("stimulation end_ms must exceed start_ms")
        if self.start_ms < 0:
            raise ValueError("stimulation start_ms cannot be negative")
        if not np.isfinite(self.current_pa):
            raise ValueError("stimulation current_pa must be finite")
        if not str(self.label):
            raise ValueError("stimulation label must be a non-empty string")
        object.__setattr__(self, "indices", indices)
        object.__setattr__(self, "current_pa", float(self.current_pa))
        object.__setattr__(self, "start_ms", float(self.start_ms))
        object.__setattr__(self, "end_ms", float(self.end_ms))
        object.__setattr__(self, "label", str(self.label))


class BancSignedSynapses:
    """Exponential current synapses with pre-signed structural weights.

    The dynamics mirror ``brain.synapse_model.SynapseModel``, but the edge
    weights arrive from :mod:`brain.banc_synapse_policy` instead of being
    derived from a graph transmitter vocabulary. Edge arrays are shared with
    the policy, not copied.
    """

    def __init__(
        self,
        graph,
        policy: BancSynapsePolicy,
        dt_ms: float,
        tau_exc_ms: float = 5.0,
        tau_inh_ms: float = 8.0,
        delay_ms: float = 1.0,
    ) -> None:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        if tau_exc_ms <= 0 or tau_inh_ms <= 0:
            raise ValueError("synaptic time constants must be positive")
        if delay_ms < 0 or not np.isfinite(delay_ms):
            raise ValueError("delay_ms must be finite and non-negative")
        n = int(graph.n_nodes)
        m = int(graph.n_edges)
        if policy.n_neurons != n:
            raise ValueError("policy and graph node counts differ")
        if policy.n_edges != m:
            raise ValueError("policy and graph edge counts differ")
        if int(getattr(graph, "threshold", -1)) != int(policy.threshold):
            raise ValueError("policy threshold does not match the graph")
        self.n_neurons = n
        self.n_edges = m
        self.dt_ms = float(dt_ms)
        self.edge_exc_weight = policy.edge_exc_weight
        self.edge_inh_weight = policy.edge_inh_weight
        self.has_inhibition = bool(np.any(self.edge_inh_weight > 0))
        self._out_indptr = graph.out_indptr
        self._edge_dst = graph.edge_dst
        self._exc_decay = float(np.exp(-self.dt_ms / tau_exc_ms))
        self._inh_decay = float(np.exp(-self.dt_ms / tau_inh_ms))
        rounded_delay = int(round(float(delay_ms) / self.dt_ms))
        extra_steps = max(0, rounded_delay - 1)
        self.delay_steps = extra_steps + 1
        self.effective_delay_ms = self.delay_steps * self.dt_ms
        self._pending_exc = deque(
            (np.zeros(n, dtype=np.float32) for _ in range(self.delay_steps)),
            maxlen=self.delay_steps,
        )
        self._pending_inh = deque(
            (np.zeros(n, dtype=np.float32) for _ in range(self.delay_steps)),
            maxlen=self.delay_steps,
        )
        self._exc = np.zeros(n, dtype=np.float32)
        self._inh = np.zeros(n, dtype=np.float32)
        self.total_transmissions = 0

    @property
    def excitatory_current_pa(self) -> np.ndarray:
        return self._exc

    @property
    def inhibitory_current_pa(self) -> np.ndarray:
        return self._inh

    @property
    def synaptic_current_pa(self) -> np.ndarray:
        return self._exc - self._inh

    @property
    def delay_buffer_bytes(self) -> int:
        return int(
            sum(buffer.nbytes for buffer in self._pending_exc)
            + sum(buffer.nbytes for buffer in self._pending_inh)
        )

    @property
    def memory_bytes(self) -> int:
        """Bytes held by shared weight arrays, currents and delay buffers."""
        return int(
            self.edge_exc_weight.nbytes
            + self.edge_inh_weight.nbytes
            + self._exc.nbytes
            + self._inh.nbytes
            + self.delay_buffer_bytes
        )

    def reset(self) -> None:
        self._exc.fill(0.0)
        self._inh.fill(0.0)
        for buffer in self._pending_exc:
            buffer.fill(0.0)
        for buffer in self._pending_inh:
            buffer.fill(0.0)
        self.total_transmissions = 0

    def advance(self) -> None:
        """Decay currents and deliver the next delayed spike packet."""
        self._exc *= self._exc_decay
        self._inh *= self._inh_decay
        incoming_exc = self._pending_exc.popleft()
        incoming_inh = self._pending_inh.popleft()
        if incoming_exc.any():
            self._exc += incoming_exc
        if incoming_inh.any():
            self._inh += incoming_inh
        incoming_exc.fill(0.0)
        incoming_inh.fill(0.0)
        self._pending_exc.append(incoming_exc)
        self._pending_inh.append(incoming_inh)

    def propagate(self, spike_indices: np.ndarray) -> int:
        """Route spikes through outgoing edges into the delay buffer.

        Returns the number of spike-to-edge transmissions. Only the edges of
        firing neurons are touched; no dense adjacency is constructed.
        """
        spikes = np.asarray(spike_indices, dtype=np.int64)
        if spikes.size == 0:
            return 0
        starts = self._out_indptr[spikes]
        ends = self._out_indptr[spikes + 1]
        counts = ends - starts
        total = int(counts.sum())
        if total == 0:
            return 0
        if spikes.size == 1:
            edge_index = np.arange(starts[0], ends[0], dtype=np.int64)
        else:
            prefix = np.cumsum(counts) - counts
            edge_index = np.repeat(starts - prefix, counts) + np.arange(
                total, dtype=np.int64
            )
        destinations = self._edge_dst[edge_index]
        exc = np.bincount(
            destinations,
            weights=self.edge_exc_weight[edge_index],
            minlength=self.n_neurons,
        )
        self._pending_exc[-1] += exc.astype(np.float32)
        if self.has_inhibition:
            inh = np.bincount(
                destinations,
                weights=self.edge_inh_weight[edge_index],
                minlength=self.n_neurons,
            )
            self._pending_inh[-1] += inh.astype(np.float32)
        self.total_transmissions += total
        return total


@dataclass
class BancSimulationResult:
    summary: dict
    recorder: SpikeRecorder
    duration_ms: float
    dt_ms: float
    n_steps: int
    seed: int
    threshold: int
    stimulation: BancStimulation | None

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


class BancSimulator:
    """Deterministic time-stepped spiking simulation on a BANC graph."""

    def __init__(
        self,
        graph,
        policy: BancSynapsePolicy,
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
        progress_interval_ms: float = 0.0,
        diagnostics_interval_steps: int = 200,
        profile_timing: bool = False,
    ) -> None:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        if noise_std_pa < 0 or not np.isfinite(noise_std_pa):
            raise ValueError("noise_std_pa must be finite and non-negative")
        if not np.isfinite(background_current_pa):
            raise ValueError("background_current_pa must be finite")
        if diagnostics_interval_steps < 1:
            raise ValueError("diagnostics_interval_steps must be positive")
        if progress_interval_ms < 0:
            raise ValueError("progress_interval_ms cannot be negative")
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
            schedule_indices = np.asarray(
                input_schedule.stimulated_indices, dtype=np.int64
            )
            if schedule_indices.size == 0:
                raise ValueError("input_schedule must target at least one neuron")
            if int(schedule_indices.max()) >= graph.n_nodes:
                raise ValueError("input schedule targets a neuron outside the graph")

        self.graph = graph
        self.policy = policy
        self.neuron_params = neuron_params or LIFParameters()
        self.dt_ms = float(dt_ms)
        self.duration_ms = float(duration_ms)
        self.seed = int(seed)
        self.background_current_pa = float(background_current_pa)
        self.noise_std_pa = float(noise_std_pa)
        self.stimulation = stimulation
        self.input_schedule = input_schedule
        self.initial_potential_mv = initial_potential_mv
        self.progress_interval_ms = float(progress_interval_ms)
        self.diagnostics_interval_steps = int(diagnostics_interval_steps)
        self.profile_timing = bool(profile_timing)
        self.neurons = LIFPopulation(graph.n_nodes, self.neuron_params, dt_ms)
        self.synapses = BancSignedSynapses(
            graph,
            policy,
            dt_ms,
            tau_exc_ms=tau_exc_ms,
            tau_inh_ms=tau_inh_ms,
            delay_ms=delay_ms,
        )
        self.recorder = SpikeRecorder(graph.n_nodes, max_recorded_spikes)

    @property
    def n_neurons(self) -> int:
        return int(self.graph.n_nodes)

    @property
    def threshold(self) -> int:
        return int(self.graph.threshold)

    def reset(self) -> None:
        self.neurons.reset(self.initial_potential_mv)
        self.synapses.reset()
        self.recorder.reset()

    def memory_breakdown(self) -> dict:
        """Bytes retained by graph, policy, simulation state and recorder.

        Temporary per-step arrays are not retained and are not included.
        """
        graph_bytes = sum(
            value.nbytes
            for value in vars(self.graph).values()
            if isinstance(value, np.ndarray)
        )
        policy_bytes = int(self.policy.memory_bytes)
        neuron_bytes = self.neurons.memory_bytes
        synapse_bytes = self.synapses.memory_bytes
        delay_bytes = self.synapses.delay_buffer_bytes
        recorder_bytes = self.recorder.memory_bytes
        retained = (
            graph_bytes + policy_bytes + neuron_bytes + synapse_bytes + recorder_bytes
        )

        def mb(value: int) -> float:
            return round(value / 1024**2, 4)

        return {
            "graph_arrays_bytes": int(graph_bytes),
            "policy_arrays_bytes": policy_bytes,
            "neuron_state_bytes": int(neuron_bytes),
            "synapse_state_bytes": int(synapse_bytes),
            "synapse_arrays_bytes": int(synapse_bytes - delay_bytes),
            "delay_buffer_bytes": int(delay_bytes),
            "spike_recorder_bytes": int(recorder_bytes),
            "retained_arrays_bytes": int(retained),
            "recorder_capacity": int(self.recorder.capacity),
            "recorder_capacity_bytes": int(
                SpikeRecorder.capacity_bytes(self.recorder.capacity)
            ),
            "components_mb": {
                "graph_arrays": mb(graph_bytes),
                "policy_arrays": mb(policy_bytes),
                "neuron_state": mb(neuron_bytes),
                "synapse_state": mb(synapse_bytes),
                "delay_buffers": mb(delay_bytes),
                "spike_recorder": mb(recorder_bytes),
            },
            "retained_arrays_mb": mb(retained),
        }

    def run(
        self, duration_ms: float | None = None, progress: bool = False
    ) -> BancSimulationResult:
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

        progress_steps = 0
        if progress and self.progress_interval_ms > 0:
            progress_steps = max(
                1, int(round(self.progress_interval_ms / self.dt_ms))
            )

        transmitted = 0
        max_current = 0.0
        max_exc_synaptic = 0.0
        max_inh_synaptic = 0.0
        min_membrane = np.inf
        max_membrane = -np.inf
        started = time.perf_counter()
        profile = self.profile_timing
        clock = time.perf_counter
        timing = (
            {
                "synaptic_update_s": 0.0,
                "input_s": 0.0,
                "integration_s": 0.0,
                "recording_s": 0.0,
                "propagation_s": 0.0,
                "diagnostics_s": 0.0,
            }
            if profile
            else None
        )

        for step in range(n_steps):
            mark = clock() if profile else 0.0
            self.synapses.advance()
            max_exc_synaptic = max(
                max_exc_synaptic,
                float(np.abs(self.synapses.excitatory_current_pa).max()),
            )
            max_inh_synaptic = max(
                max_inh_synaptic,
                float(np.abs(self.synapses.inhibitory_current_pa).max()),
            )
            if profile:
                timing["synaptic_update_s"] += clock() - mark
                mark = clock()

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
            if profile:
                timing["input_s"] += clock() - mark
                mark = clock()

            spikes = self.neurons.step(current)
            if profile:
                timing["integration_s"] += clock() - mark
                mark = clock()

            self.recorder.record(step, spikes, self.dt_ms)
            if profile:
                timing["recording_s"] += clock() - mark
                mark = clock()

            transmitted += self.synapses.propagate(spikes)
            if profile:
                timing["propagation_s"] += clock() - mark
                mark = clock()

            if (step + 1) % self.diagnostics_interval_steps == 0:
                self._check_finite()
                membrane = self.neurons.membrane_potential
                min_membrane = min(min_membrane, float(membrane.min()))
                max_membrane = max(max_membrane, float(membrane.max()))
            if profile:
                timing["diagnostics_s"] += clock() - mark

            if progress_steps and (step + 1) % progress_steps == 0:
                print(
                    f"  {step + 1:>6}/{n_steps} steps "
                    f"({(step + 1) * self.dt_ms:.0f}/{simulated_ms:.0f} ms)",
                    flush=True,
                )

        self._check_finite()
        membrane = self.neurons.membrane_potential
        min_membrane = min(min_membrane, float(membrane.min()))
        max_membrane = max(max_membrane, float(membrane.max()))
        runtime = time.perf_counter() - started
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
        )
        if timing is not None:
            timing["total_s"] = runtime
            summary["timing_s"] = {
                key: round(float(value), 6) for key, value in timing.items()
            }
        return BancSimulationResult(
            summary=summary,
            recorder=self.recorder,
            duration_ms=simulated_ms,
            dt_ms=self.dt_ms,
            n_steps=n_steps,
            seed=self.seed,
            threshold=self.threshold,
            stimulation=self.stimulation,
        )

    def _check_finite(self) -> None:
        arrays = (
            self.neurons.membrane_potential,
            self.synapses.excitatory_current_pa,
            self.synapses.inhibitory_current_pa,
        )
        if not all(np.isfinite(array).all() for array in arrays):
            raise FloatingPointError(
                "non-finite state detected; reduce dt_ms or input currents"
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
        max_exc_synaptic_pa: float = 0.0,
        max_inh_synaptic_pa: float = 0.0,
    ) -> dict:
        activity = self.recorder.summary(duration_ms)
        counts = self.recorder.spike_counts()
        stimulated = np.zeros(self.n_neurons, dtype=bool)
        if self.stimulation is not None:
            stimulated[self.stimulation.indices] = True
        if self.input_schedule is not None:
            stimulated[
                np.asarray(self.input_schedule.stimulated_indices, dtype=np.int64)
            ] = True
        stimulated_activity = {
            "stimulated_neurons": int(stimulated.sum()),
            "stimulated_active_neurons": int(np.count_nonzero(counts[stimulated])),
            "stimulated_spikes": int(counts[stimulated].sum()),
            "non_stimulated_active_neurons": int(
                np.count_nonzero(counts[~stimulated])
            ),
            "non_stimulated_spikes": int(counts[~stimulated].sum()),
            "non_stimulated_spike_fraction": round(
                float(counts[~stimulated].sum()) / max(1, int(counts.sum())), 6
            ),
        }
        stimulation = None
        if self.stimulation is not None:
            stimulation = {
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
        return {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "simulation": {
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
                    "tau_exc_ms": 5.0,
                    "tau_inh_ms": 8.0,
                    "effective_delay_ms": self.synapses.effective_delay_ms,
                    "delay_steps": int(self.synapses.delay_steps),
                    "weight_source": "structural synapse count (count), not norm",
                },
            },
            "synaptic_policy": {
                "sign_policy": self.policy.sign_policy.describe(),
                "weight_policy": self.policy.weight_policy.describe(),
                "signed_edges": int(self.policy.signed_edges),
                "excluded_edges": int(self.policy.n_edges - self.policy.signed_edges),
                "excitatory_edges": int(
                    np.count_nonzero(self.policy.edge_exc_weight)
                ),
                "inhibitory_edges": int(
                    np.count_nonzero(self.policy.edge_inh_weight)
                ),
            },
            "stimulation": stimulation,
            "input_schedule": (
                self.input_schedule.describe()
                if self.input_schedule is not None
                else None
            ),
            "activity": activity,
            "activity_by_stimulation": stimulated_activity,
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
                "max_abs_membrane_mv": round(
                    max(abs(min_membrane_mv), abs(max_membrane_mv)), 4
                ),
                "max_abs_total_current_pa": round(max_current_pa, 4),
                "max_excitatory_synaptic_current_pa": round(
                    max_exc_synaptic_pa, 4
                ),
                "max_inhibitory_synaptic_current_pa": round(
                    max_inh_synaptic_pa, 4
                ),
            },
            "memory": self.memory_breakdown(),
        }
