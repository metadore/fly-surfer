"""Phase 4H.4: sensory-to-BANC round-trip on archived perception events.

Conditions (protocol section 6.4), each on the full Phase 3B.2C replay and on
the two archived segments:

A  no events
B  actual event sequence
C  temporally shuffled (the sorted time array is permuted across events)
D  feature-identity shuffled (feature payloads permuted across events)
E  random size-matched non-motor mapping
F  constant neutral drive with the same total injected charge
G  background 50 pA plus 50 pA Gaussian noise, no events

B and G are repeated with the same seed to verify determinism. All parameters
are fixed in ``configs/banc_sensory_mapping.yaml`` before execution. The
segments come from one recording group and are not independent sequences, so
condition differences are reported descriptively with intervals; no
confirmatory p-value is claimed and evidence level E4 is not claimed.

Writes ``experiments/results/phase_4h/sensory_roundtrip.json`` and appends one
JSON line per run to a resumable checkpoint.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_sensory_adapter import (  # noqa: E402
    BancEventDrive,
    BancSensoryMapping,
    ConstantChargeDrive,
    event_metadata_digest,
    shuffle_feature_identities,
    temporally_shuffle_events,
    validate_events,
)
from brain.banc_simulation_adapter import BancActivityAdapter  # noqa: E402
from brain.banc_simulator import BancSimulator  # noqa: E402
from experiments.phase_4h import common  # noqa: E402
from motor.motor_decoder import MotorDecoder  # noqa: E402
from sensory.population_encoder import build_encoders  # noqa: E402

MAPPING_CONFIG = PROJECT_ROOT / "configs" / "banc_sensory_mapping.yaml"
FULL_REPLAY = (
    PROJECT_ROOT
    / "experiments"
    / "phase_3b"
    / "results"
    / "phase_3b2c_real_sequence_replay.json"
)
SEQUENCE_DIR = PROJECT_ROOT / "experiments" / "phase_4h" / "sequences"
OUTPUT = common.RESULTS / "sensory_roundtrip.json"
CHECKPOINT = common.RESULTS / "sensory_roundtrip.checkpoint.jsonl"

CONDITIONS = (
    "A_no_events",
    "B_actual",
    "C_temporal_shuffle",
    "D_feature_identity_shuffle",
    "E_random_matched_mapping",
    "F_constant_matched_charge",
    "G_background_noise",
)
REPEATS = ("B_actual", "G_background_noise")
STREAMS = ("full_100_199", "seg_0_99", "seg_200_299")
LAG_MS = 200.0
BIN_MS = 10.0
LOCK_WINDOW_MS = 50.0
MAX_RECORDED_SPIKES = 5_000_000

LIMITATIONS = [
    "The three streams are non-overlapping segments of one recording group, "
    "not independent recordings.",
    "Event timestamps are synthesized at 30 fps because the images carry no "
    "timestamps; ordering and gaps come from the unchanged Phase 3B pipeline.",
    "Only lifecycle events carrying feature values drive current; the archived "
    "replay exposes events, not per-frame GameState features, so no held "
    "per-frame state is used.",
    "The mapping from a game feature to a BANC annotation pool is a labelled "
    "hypothesis or convention, not a measured sensory pathway.",
    "No confirmatory p-value is claimed across the three non-independent "
    "streams; evidence level E4 is not claimed.",
    "A motor spike or decoder label is not a biological motor command.",
]


# -- stream loading ---------------------------------------------------------


def load_stream(name: str) -> dict:
    if name == "full_100_199":
        payload = json.loads(FULL_REPLAY.read_text(encoding="utf-8"))
        events = payload["events"]
        sequence = payload.get("sequence", {})
        duration = float(payload["simulation"]["duration_ms"])
        source = str(FULL_REPLAY.relative_to(PROJECT_ROOT)).replace("\\", "/")
        segment = {
            "group": sequence.get("group"),
            "frame_start": sequence.get("frame_start"),
            "frame_end": sequence.get("frame_end"),
            "n_frames": sequence.get("n_frames"),
            "sequence_sha256": sequence.get("sequence_sha256"),
            "timestamp_policy": sequence.get("timestamp_policy"),
        }
    elif name == "seg_0_99":
        path = SEQUENCE_DIR / "events_0_99.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        events = payload["events"]
        segment = payload["segment"]
        duration = float(payload["temporal"]["final_time_ms"]) + 0.5
        source = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    elif name == "seg_200_299":
        path = SEQUENCE_DIR / "events_200_299.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        events = payload["events"]
        segment = payload["segment"]
        duration = float(payload["temporal"]["final_time_ms"]) + 0.5
        source = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    else:
        raise ValueError(f"unknown stream {name!r}; expected {list(STREAMS)}")
    return {
        "name": name,
        "source": source,
        "events": events,
        "duration_ms": duration,
        "segment": segment,
        "event_metadata_sha256": event_metadata_digest(events),
        "n_events": len(events),
        "n_pulses": sum(1 for event in events if event.get("feature_values")),
    }


# -- analysis helpers -------------------------------------------------------


def event_locked_summary(events, downstream_times: np.ndarray) -> dict:
    if not events:
        return {"n_events": 0, "note": "no events in this condition"}
    counts = []
    latencies = []
    for event in events:
        start = float(event["time_ms"])
        stop = start + LOCK_WINDOW_MS
        counts.append(
            int(np.count_nonzero((downstream_times >= start) & (downstream_times < stop)))
        )
        position = int(np.searchsorted(downstream_times, start, side="left"))
        latencies.append(
            None
            if position >= downstream_times.size
            else float(downstream_times[position] - start)
        )
    present = [value for value in latencies if value is not None]
    return {
        "n_events": len(events),
        "window_ms": LOCK_WINDOW_MS,
        "spikes_in_window": common.summary_stats(counts),
        "total_spikes_in_window": int(sum(counts)),
        "events_with_zero_spikes": int(sum(1 for value in counts if value == 0)),
        "latency_ms": common.summary_stats(present),
        "n_events_without_downstream_spike": len(events) - len(present),
        "per_event": [
            {"time_ms": round(float(event["time_ms"]), 4), "count": count, "latency_ms": latency}
            for event, count, latency in zip(events, counts, latencies)
        ],
    }


def alignment(events, downstream_times: np.ndarray, duration_ms: float) -> dict:
    edges = np.arange(0.0, duration_ms + BIN_MS, BIN_MS)
    event_times = np.asarray(
        [float(event["time_ms"]) for event in events], dtype=np.float64
    )
    event_counts, _ = np.histogram(event_times, bins=edges)
    spike_counts, _ = np.histogram(downstream_times, bins=edges)
    results = []
    for lag in np.arange(0.0, LAG_MS + BIN_MS, BIN_MS):
        shift = int(round(lag / BIN_MS))
        if shift >= event_counts.size:
            continue
        left = event_counts[: event_counts.size - shift]
        right = spike_counts[shift:]
        if left.size < 3 or left.std() == 0 or right.std() == 0:
            results.append({"lag_ms": float(lag), "pearson_r": None})
            continue
        results.append(
            {
                "lag_ms": float(lag),
                "pearson_r": round(float(np.corrcoef(left, right)[0, 1]), 6),
            }
        )
    valid = [item for item in results if item["pearson_r"] is not None]
    best = (
        max(valid, key=lambda item: abs(item["pearson_r"])) if valid else None
    )
    return {
        "bin_ms": BIN_MS,
        "lags_ms": [0.0, LAG_MS],
        "n_bins": int(event_counts.size),
        "event_spikes_in_bins": int(event_counts.sum()),
        "downstream_spikes_in_bins": int(spike_counts.sum()),
        "by_lag": results,
        "best": best,
        "note": "Pearson correlation of 10 ms event and downstream spike bins",
    }


def build_schedule(
    mapping,
    encoders,
    events,
    *,
    duration_ms: float,
    drive: dict,
    current_pa: dict,
):
    return BancEventDrive(
        mapping,
        encoders,
        events,
        current_pa=current_pa,
        duration_ms=duration_ms,
        decay_ms=float(drive["decay_ms"]),
        dt_ms=float(drive["dt_ms"]),
        pulse_gain=float(drive["pulse_gain"]),
    )


def run_condition(
    world,
    *,
    stream: dict,
    condition: str,
    real_mapping,
    random_mapping,
    encoders,
    drive: dict,
    current_pa: dict,
    seed: int,
    duration_ms: float,
    dt_ms: float,
) -> dict:
    events = stream["events"]
    mapping = real_mapping
    schedule = None
    background = 0.0
    noise = 0.0
    events_used = []
    mapping_used = "annotation"
    if condition == "A_no_events":
        events_used = []
    elif condition in ("B_actual", "B_actual_repeat"):
        events_used = events
        schedule = build_schedule(
            real_mapping, encoders, events_used, duration_ms=duration_ms, drive=drive,
            current_pa=current_pa,
        )
    elif condition == "C_temporal_shuffle":
        events_used = temporally_shuffle_events(events, seed=seed)
        schedule = build_schedule(
            real_mapping, encoders, events_used, duration_ms=duration_ms, drive=drive,
            current_pa=current_pa,
        )
    elif condition == "D_feature_identity_shuffle":
        events_used = shuffle_feature_identities(events, seed=seed)
        schedule = build_schedule(
            real_mapping, encoders, events_used, duration_ms=duration_ms, drive=drive,
            current_pa=current_pa,
        )
    elif condition == "E_random_matched_mapping":
        mapping = random_mapping
        events_used = events
        mapping_used = "random_matched_non_motor"
        schedule = build_schedule(
            random_mapping, encoders, events_used, duration_ms=duration_ms, drive=drive,
            current_pa=current_pa,
        )
    elif condition == "F_constant_matched_charge":
        reference = build_schedule(
            real_mapping, encoders, events, duration_ms=duration_ms, drive=drive,
            current_pa=current_pa,
        )
        schedule = ConstantChargeDrive(
            real_mapping.stimulated_indices(),
            reference.total_charge_pa_ms(),
            duration_ms=duration_ms,
            dt_ms=dt_ms,
        )
    elif condition in ("G_background_noise", "G_background_noise_repeat"):
        background = float(drive["background_pa_condition_g"])
        noise = float(drive["noise_std_pa_condition_g"])
    else:
        raise ValueError(f"unknown condition {condition!r}")

    if schedule is not None and np.any(
        np.asarray(world.populations.motor_mask, dtype=bool)[
            np.asarray(schedule.stimulated_indices, dtype=np.int64)
        ]
    ):
        raise RuntimeError("a schedule targets a motor neuron")

    started = time.perf_counter()
    simulator = BancSimulator(
        world.graph,
        world.policy,
        neuron_params=world.neuron_params,
        dt_ms=dt_ms,
        duration_ms=duration_ms,
        seed=int(seed),
        background_current_pa=background,
        noise_std_pa=noise,
        stimulation=None,
        input_schedule=schedule,
        max_recorded_spikes=MAX_RECORDED_SPIKES,
    )
    result = simulator.run()
    adapter = BancActivityAdapter(
        result.recorder, world.populations, graph_threshold=world.graph.threshold
    )
    decoder = MotorDecoder(world.populations, world.decoder_config)
    decisions = adapter.decode(decoder, 0.0, duration_ms)
    stimulated = np.asarray(mapping.stimulated_indices(), dtype=np.int64)
    metrics = common.condition_metrics(
        world,
        result.recorder,
        decisions,
        stimulated,
        stim_start_ms=0.0,
        stim_end_ms=duration_ms,
        duration_ms=duration_ms,
    )

    times = np.asarray(result.recorder.spike_times_ms, dtype=np.float64)
    indices = np.asarray(result.recorder.spike_neuron_indices, dtype=np.int64)
    stimulated_mask = np.zeros(world.n_nodes, dtype=bool)
    stimulated_mask[stimulated] = True
    downstream_times = np.sort(times[~stimulated_mask[indices]])

    record = {
        "stream": stream["name"],
        "condition": condition,
        "events_used": len(events_used),
        "pulses_used": int(
            sum(1 for event in events_used if event.get("feature_values"))
        ),
        "events_metadata_sha256": event_metadata_digest(events_used),
        "mapping_used": mapping_used,
        "n_stimulated_neurons": int(stimulated.size),
        "drive": None if schedule is None else schedule.describe(),
        "seed": int(seed),
        "background_pa": background,
        "noise_std_pa": noise,
        "duration_ms": duration_ms,
        "dt_ms": dt_ms,
        "metrics": metrics,
        "decisions": [decision.as_dict() for decision in decisions],
        "n_decisions": len(decisions),
        "event_locked": event_locked_summary(events_used, downstream_times),
        "alignment": alignment(events_used, downstream_times, duration_ms),
        "hashes": {
            "spike_sha256": common.spike_hash(result.recorder),
            "decision_sha256": common.digest_json(
                [decision.as_dict() for decision in decisions]
            ),
            "drive_sha256": None
            if schedule is None
            else schedule.signature_sha256(),
        },
        "activity_summary": result.summary["activity"],
        "activity_by_stimulation": result.summary["activity_by_stimulation"],
        "synaptic_transmission": result.summary["synaptic_transmission"],
        "memory": result.summary["memory"],
        "process_memory": common.process_memory(),
        "wall_time_s": round(time.perf_counter() - started, 3),
    }
    return record


# -- statistics -------------------------------------------------------------


def endpoint_pair(first: dict, second: dict) -> dict:
    endpoints = (
        ("total", ("n_spikes",)),
        ("stimulated", ("stimulated_spikes",)),
        ("non_stimulated", ("non_stimulated_spikes",)),
        ("motor", ("motor", "spikes")),
    )
    payload = {}
    for name, path in endpoints:
        a = first["metrics"]
        b = second["metrics"]
        for key in path:
            a = a[key]
            b = b[key]
        a = int(a)
        b = int(b)
        payload[name] = {
            "first": a,
            "second": b,
            "difference": a - b,
            "ratio": None if b == 0 else round(a / b, 6),
        }
    return payload


def summarise(runs: list[dict]) -> dict:
    table = {}
    for record in runs:
        if record["condition"].endswith("_repeat"):
            continue
        metrics = record["metrics"]
        table.setdefault(record["stream"], {})[record["condition"]] = {
            "total_spikes": metrics["n_spikes"],
            "stimulated_spikes": metrics["stimulated_spikes"],
            "non_stimulated_spikes": metrics["non_stimulated_spikes"],
            "motor_spikes": metrics["motor"]["spikes"],
            "active_neurons": metrics["active_neurons"],
            "decoded_state_counts": metrics["decoded_state_counts"],
            "n_windows": metrics["n_windows"],
            "time_to_first_motor_spike_ms": metrics["time_to_first_motor_spike_ms"],
            "events_with_zero_locked_spikes": (
                record["event_locked"].get("events_with_zero_spikes")
            ),
            "latency_median_ms": (
                record["event_locked"].get("latency_ms", {}).get("median")
            ),
            "alignment_best": record["alignment"].get("best"),
            "spike_sha256": record["hashes"]["spike_sha256"],
            "drive_sha256": record["hashes"]["drive_sha256"],
        }
    return table


def comparisons(runs: list[dict]) -> dict:
    lookup = {
        (record["stream"], record["condition"]): record
        for record in runs
        if not record["condition"].endswith("_repeat")
    }
    payload = {}
    for stream in sorted({record["stream"] for record in runs}):
        block = {}
        for other in ("C_temporal_shuffle", "D_feature_identity_shuffle"):
            first = lookup.get((stream, "B_actual"))
            second = lookup.get((stream, other))
            if first is None or second is None:
                continue
            block[f"B_actual_vs_{other}"] = endpoint_pair(first, second)
        payload[stream] = block
    return payload


def determinism(runs: list[dict]) -> dict:
    lookup = {(record["stream"], record["condition"]): record for record in runs}
    payload = {}
    for stream in sorted({record["stream"] for record in runs}):
        block = {}
        for base, repeat in (
            ("B_actual", "B_actual_repeat"),
            ("G_background_noise", "G_background_noise_repeat"),
        ):
            first = lookup.get((stream, base))
            second = lookup.get((stream, repeat))
            if first is None or second is None:
                block[base] = {"complete": False}
                continue
            block[base] = {
                "complete": True,
                "spike_hash_equal": first["hashes"]["spike_sha256"]
                == second["hashes"]["spike_sha256"],
                "decision_hash_equal": first["hashes"]["decision_sha256"]
                == second["hashes"]["decision_sha256"],
                "drive_hash_equal": first["hashes"]["drive_sha256"]
                == second["hashes"]["drive_sha256"],
                "metrics_equal": {
                    key: first["metrics"][key]
                    for key in (
                        "n_spikes",
                        "stimulated_spikes",
                        "non_stimulated_spikes",
                        "active_neurons",
                    )
                }
                == {
                    key: second["metrics"][key]
                    for key in (
                        "n_spikes",
                        "stimulated_spikes",
                        "non_stimulated_spikes",
                        "active_neurons",
                    )
                }
                and first["metrics"]["motor"]["spikes"]
                == second["metrics"]["motor"]["spikes"],
            }
        payload[stream] = block
    return payload


# -- main -------------------------------------------------------------------


def load_checkpoint(path: Path) -> dict:
    records = {}
    if not path.is_file():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        records[(record["stream"], record["condition"])] = record
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--streams", default=",".join(STREAMS))
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args(argv)
    streams = [item.strip() for item in args.streams.split(",") if item.strip()]
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    unknown = set(conditions) - set(CONDITIONS) - {
        "B_actual_repeat",
        "G_background_noise_repeat",
    }
    if unknown:
        raise SystemExit(f"unknown conditions {sorted(unknown)}")
    checkpoint = Path(args.checkpoint).resolve()
    output = Path(args.output).resolve()

    config = common.load_yaml(MAPPING_CONFIG)
    encoders = build_encoders(config["features"])
    current_pa = {
        feature: float(payload.get("current_pa", 0.0))
        for feature, payload in config["features"].items()
    }
    drive = config["drive"]
    dt_ms = float(drive["dt_ms"])
    clock = time.perf_counter()
    before = common.integrity_snapshot()
    world = common.load_world()

    mapping_seed = int(config["mapping"]["seed"])
    action_masks = {
        name: np.asarray(mask, dtype=bool)
        for name, mask in world.populations.masks.items()
    }
    real_mapping = BancSensoryMapping(
        world.nodes,
        world.graph,
        config["mapping"],
        motor_mask=world.populations.motor_mask,
        action_masks=action_masks,
    )
    random_config = json.loads(json.dumps(config["mapping"]))
    random_config["seed"] = mapping_seed + 450000
    random_mapping = BancSensoryMapping(
        world.nodes,
        world.graph,
        random_config,
        motor_mask=world.populations.motor_mask,
        action_masks=action_masks,
        randomise_pools=True,
    )
    if {feature: real_mapping.size(feature) for feature in encoders} != {
        feature: random_mapping.size(feature) for feature in encoders
    }:
        raise RuntimeError("random matched mapping changed the population sizes")

    existing = {} if args.fresh else load_checkpoint(checkpoint)
    runs: list[dict] = list(existing.values())
    stream_payloads = {name: load_stream(name) for name in streams}
    for stream_name in streams:
        stream = stream_payloads[stream_name]
        duration_ms = float(args.duration or stream["duration_ms"])
        for condition in conditions:
            key = (stream_name, condition)
            if key in existing:
                print(f"  skip {stream_name} {condition} (checkpoint)")
                continue
            seed = common.SEED_ROOT + 400000 + 100 * STREAMS.index(stream_name) + CONDITIONS.index(
                condition.replace("_repeat", "")
            )
            record = run_condition(
                world,
                stream=stream,
                condition=condition,
                real_mapping=real_mapping,
                random_mapping=random_mapping,
                encoders=encoders,
                drive=drive,
                current_pa=current_pa,
                seed=seed,
                duration_ms=duration_ms,
                dt_ms=dt_ms,
            )
            common.jsonl_append(checkpoint, record)
            runs.append(record)
            metrics = record["metrics"]
            print(
                f"  {stream_name} {condition} total={metrics['n_spikes']} "
                f"motor={metrics['motor']['spikes']} "
                f"states={record['metrics']['decoded_state_counts']} "
                f"({record['wall_time_s']} s)"
            )

    # Repeats are deterministic reruns of B and G; they are stored in the
    # same checkpoint and compared by hash.
    for stream_name in streams:
        stream = stream_payloads[stream_name]
        duration_ms = float(args.duration or stream["duration_ms"])
        for base in REPEATS:
            repeat = f"{base}_repeat"
            if base not in conditions and repeat not in conditions:
                continue
            key = (stream_name, repeat)
            if key in existing:
                continue
            seed = common.SEED_ROOT + 400000 + 100 * STREAMS.index(stream_name) + CONDITIONS.index(
                base
            )
            record = run_condition(
                world,
                stream=stream,
                condition=repeat,
                real_mapping=real_mapping,
                random_mapping=random_mapping,
                encoders=encoders,
                drive=drive,
                current_pa=current_pa,
                seed=seed,
                duration_ms=duration_ms,
                dt_ms=dt_ms,
            )
            common.jsonl_append(checkpoint, record)
            runs.append(record)
            print(f"  {stream_name} {repeat} written for determinism check")

    after = common.integrity_snapshot()
    payload = {
        "phase": "4H.4",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol_sha256": common.sha256_file(
            PROJECT_ROOT / "reports" / "PHASE_4H_EXPERIMENTAL_PROTOCOL.md"
        ),
        "software": common.software_versions(),
        "config": {
            "path": str(MAPPING_CONFIG.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": common.sha256_file(MAPPING_CONFIG),
            "drive": drive,
        },
        "world": world.describe(),
        "mapping": {
            "annotation": real_mapping.report(),
            "random_matched": random_mapping.report(),
        },
        "streams": {
            name: {key: value for key, value in stream.items() if key != "events"}
            for name, stream in stream_payloads.items()
        },
        "conditions": {
            "A_no_events": "no drive, no background, no noise",
            "B_actual": "actual archived events through the annotation mapping",
            "C_temporal_shuffle": "sorted time array permuted across events",
            "D_feature_identity_shuffle": "feature payloads permuted across events",
            "E_random_matched_mapping": "seeded size-matched non-motor mapping",
            "F_constant_matched_charge": "uniform constant drive, matched total charge",
            "G_background_noise": "50 pA background plus 50 pA Gaussian noise",
        },
        "runs": runs,
        "summary": summarise(runs),
        "comparisons": comparisons(runs),
        "determinism": determinism(runs),
        "integrity": {
            "before": before,
            "after": after,
            "protected_unchanged": before["pass"] and after["pass"],
        },
        "runtime": {
            "wall_time_s": round(time.perf_counter() - clock, 3),
            "n_runs": len(runs),
        },
        "limitations": LIMITATIONS,
    }
    common.write_json(output, payload)
    print(f"wrote {output} | runs={len(runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
