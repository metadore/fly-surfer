"""Time-stepped spiking simulation over a connectome-derived graph.

The timestep order is: deliver delayed synaptic input and decay currents,
integrate the LIF membrane, record spikes, then route those spikes into the
synaptic delay buffer. A spike emitted at the end of step ``k`` can therefore
influence a postsynaptic neuron no earlier than step ``k + 1``.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from brain.neural_activity import SpikeRecorder
from brain.neuron_model import LIFParameters, LIFPopulation
from brain.synapse_model import SynapseModel, SynapseParameters


@dataclass(frozen=True)
class Stimulus:
    """External current injected into a fixed set of local neuron indices."""

    indices: np.ndarray
    current_pa: float
    start_ms: float
    end_ms: float

    def __post_init__(self) -> None:
        indices = np.unique(np.asarray(self.indices, dtype=np.int64))
        if indices.size == 0:
            raise ValueError("stimulus must target at least one neuron")
        if self.end_ms <= self.start_ms:
            raise ValueError("stimulus end_ms must exceed start_ms")
        if self.start_ms < 0:
            raise ValueError("stimulus start_ms cannot be negative")
        object.__setattr__(self, "indices", indices)


@dataclass
class SimulationResult:
    summary: dict
    recorder: SpikeRecorder
    duration_ms: float
    dt_ms: float
    n_steps: int
    seed: int
    stimulus: Stimulus | None

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

class BrainSimulator:
    """Deterministic time-stepped spiking simulation."""

    def __init__(
        self,
        graph,
        neuron_params: LIFParameters,
        synapse_params: SynapseParameters,
        dt_ms: float = 0.5,
        duration_ms: float = 1000.0,
        seed: int = 0,
        background_current_pa: float = 0.0,
        noise_std_pa: float = 0.0,
        stimulus: Stimulus | None = None,
        input_schedule=None,
        max_recorded_spikes: int = 2_000_000,
        progress_interval_ms: float = 100.0,
        diagnostics_interval_steps: int = 200,
        profile_timing: bool = False,
    ) -> None:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        if noise_std_pa < 0:
            raise ValueError("noise_std_pa cannot be negative")
        if diagnostics_interval_steps < 1:
            raise ValueError("diagnostics_interval_steps must be positive")
        if stimulus is not None and int(stimulus.indices.max()) >= graph.n_nodes:
            raise ValueError("stimulus index outside the graph")
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
        self.neuron_params = neuron_params
        self.synapse_params = synapse_params
        self.dt_ms = float(dt_ms)
        self.duration_ms = float(duration_ms)
        self.seed = int(seed)
        self.background_current_pa = float(background_current_pa)
        self.noise_std_pa = float(noise_std_pa)
        self.stimulus = stimulus
        self.input_schedule = input_schedule
        self.progress_interval_ms = float(progress_interval_ms)
        self.diagnostics_interval_steps = int(diagnostics_interval_steps)
        self.profile_timing = bool(profile_timing)
        self.neurons = LIFPopulation(graph.n_nodes, neuron_params, dt_ms)
        self.synapses = SynapseModel(graph, synapse_params, dt_ms)
        self.recorder = SpikeRecorder(graph.n_nodes, max_recorded_spikes)

    @property
    def n_neurons(self) -> int:
        return self.graph.n_nodes

    def reset(self) -> None:
        self.neurons.reset()
        self.synapses.reset()
        self.recorder.reset()

    def memory_breakdown(self) -> dict:
        """Bytes retained by the graph and simulation state.

        Temporary propagation arrays are not retained; an upper bound for a
        single step that fires every neuron is reported separately.
        """
        graph_bytes = sum(
            value.nbytes
            for value in vars(self.graph).values()
            if isinstance(value, np.ndarray)
        )
        out_degree = np.diff(self.graph.out_indptr)
        max_out = int(out_degree.max()) if out_degree.size else 0
        neuron_bytes = self.neurons.memory_bytes
        delay_bytes = self.synapses.delay_buffer_bytes
        synapse_bytes = self.synapses.memory_bytes
        synapse_arrays_bytes = synapse_bytes - delay_bytes
        recorder_bytes = self.recorder.memory_bytes
        retained = graph_bytes + neuron_bytes + synapse_bytes + recorder_bytes
        n = self.n_neurons
        m = self.graph.n_edges

        def mb(value: int) -> float:
            return round(value / 1024**2, 4)

        return {
            "graph_arrays_bytes": int(graph_bytes),
            "neuron_state_bytes": int(neuron_bytes),
            "synapse_state_bytes": int(synapse_bytes),
            "synapse_arrays_bytes": int(synapse_arrays_bytes),
            "delay_buffer_bytes": int(delay_bytes),
            "spike_recorder_bytes": int(recorder_bytes),
            "retained_arrays_bytes": int(retained),
            "recorder_capacity": int(self.recorder.capacity),
            "recorder_capacity_bytes": int(
                SpikeRecorder.capacity_bytes(self.recorder.capacity)
            ),
            "max_out_degree": max_out,
            "single_hub_propagation_temporary_bytes": int(12 * max_out + 24 * n),
            "worst_case_propagation_temporary_bytes": int(12 * m + 24 * n),
            "components_mb": {
                "graph_arrays": mb(graph_bytes),
                "neuron_state": mb(neuron_bytes),
                "synapse_state": mb(synapse_bytes),
                "delay_buffers": mb(self.synapses.delay_buffer_bytes),
                "spike_recorder": mb(recorder_bytes),
            },
            "retained_arrays_mb": mb(retained),
            "single_hub_propagation_temporary_mb": mb(12 * max_out + 24 * n),
            "worst_case_propagation_temporary_mb": mb(12 * m + 24 * n),
        }

    def run(
        self, duration_ms: float | None = None, progress: bool = True
    ) -> SimulationResult:
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
        if self.stimulus is not None:
            stim_start = int(np.ceil(self.stimulus.start_ms / self.dt_ms))
            stim_end = int(np.ceil(self.stimulus.end_ms / self.dt_ms))

        progress_steps = 0
        if progress and self.progress_interval_ms > 0:
            progress_steps = max(
                1, int(round(self.progress_interval_ms / self.dt_ms))
            )

        transmitted = 0
        max_current = 0.0
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
            if profile:
                timing["synaptic_update_s"] += clock() - mark
                mark = clock()

            if self.noise_std_pa > 0:
                current = rng.normal(0.0, self.noise_std_pa, n)
            else:
                current = np.zeros(n, dtype=np.float64)
            current += self.background_current_pa
            current += self.synapses.synaptic_current_pa
            if self.stimulus is not None and stim_start <= step < stim_end:
                current[self.stimulus.indices] += self.stimulus.current_pa
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
        )
        if timing is not None:
            timing["total_s"] = runtime
            summary["timing_s"] = {
                key: round(float(value), 6) for key, value in timing.items()
            }
        return SimulationResult(
            summary=summary,
            recorder=self.recorder,
            duration_ms=simulated_ms,
            dt_ms=self.dt_ms,
            n_steps=n_steps,
            seed=self.seed,
            stimulus=self.stimulus,
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
    ) -> dict:
        activity = self.recorder.summary(duration_ms)
        counts = self.recorder.spike_counts()
        stimulated = np.zeros(self.n_neurons, dtype=bool)
        if self.stimulus is not None:
            stimulated[self.stimulus.indices] = True
        if self.input_schedule is not None:
            stimulated[
                np.asarray(self.input_schedule.stimulated_indices, dtype=np.int64)
            ] = True
        stimulated_activity = {
            "stimulated_neurons": int(stimulated.sum()),
            "stimulated_active_neurons": int(
                np.count_nonzero(counts[stimulated])
            ),
            "stimulated_spikes": int(counts[stimulated].sum()),
            "non_stimulated_active_neurons": int(
                np.count_nonzero(counts[~stimulated])
            ),
            "non_stimulated_spikes": int(counts[~stimulated].sum()),
            "non_stimulated_spike_fraction": round(
                float(counts[~stimulated].sum()) / max(1, int(counts.sum())), 6
            ),
        }
        excitatory = int(np.count_nonzero(self.synapses.edge_exc_weight))
        inhibitory = int(np.count_nonzero(self.synapses.edge_inh_weight))
        signs = self.synapses.signs
        stimulus = None
        if self.stimulus is not None:
            stimulus = {
                "n_neurons": int(len(self.stimulus.indices)),
                "root_ids": [
                    int(value) for value in self.graph.root_ids[self.stimulus.indices]
                ],
                "current_pa": self.stimulus.current_pa,
                "start_ms": self.stimulus.start_ms,
                "end_ms": self.stimulus.end_ms,
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
                "n_nodes": self.graph.n_nodes,
                "n_edges": self.graph.n_edges,
                "n_synapses": int(self.graph.edge_weight.sum(dtype=np.int64)),
                "source_n_nodes": getattr(self.graph, "source_n_nodes", None),
                "source_n_edges": getattr(self.graph, "source_n_edges", None),
            },
            "model": {
                "neuron": asdict(self.neuron_params),
                "synapse": asdict(self.synapse_params),
            },
            "stimulus": stimulus,
            "input_schedule": (
                self.input_schedule.describe()
                if self.input_schedule is not None
                else None
            ),
            "synapses": {
                "excitatory_edges": excitatory,
                "inhibitory_edges": inhibitory,
                "excitatory_neurons": int(np.count_nonzero(signs > 0)),
                "inhibitory_neurons": int(np.count_nonzero(signs < 0)),
                "silent_neurons": int(np.count_nonzero(signs == 0)),
                "effective_delay_ms": self.synapses.effective_delay_ms,
                "spike_transmissions": int(transmitted),
                "transmissions_per_spike": round(
                    transmitted / max(1, activity["n_spikes"]), 3
                ),
            },
            "activity": activity,
            "activity_by_stimulation": stimulated_activity,
            "diagnostics": {
                "finite_state": True,
                "min_membrane_mv": round(min_membrane_mv, 4),
                "max_membrane_mv": round(max_membrane_mv, 4),
                "max_abs_membrane_mv": round(
                    max(abs(min_membrane_mv), abs(max_membrane_mv)), 4
                ),
                "max_abs_total_current_pa": round(max_current_pa, 4),
            },
        }


