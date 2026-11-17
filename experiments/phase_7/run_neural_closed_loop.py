"""Run the Phase 7 live neural closed loop on the controlled game.

The existing BANC simulator and Phase 4 decoder drive the existing controlled
endless-runner. Nothing here re-implements the simulator, the neuron model, the
synapse policy, the Phase 3 encoders, the Phase 4 decoder, the Phase 7
environment or the game.

The run is fixed-weight: no plasticity module is imported, and the synapse
weight arrays are hashed before and after the episode. Rewards are recorded
through the existing Phase 5 interfaces but never applied to weights.

Official artifact: ``experiments/results/phase_7/neural_closed_loop.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_sensory_adapter import BancSensoryMapping  # noqa: E402
from environment import (  # noqa: E402
    ControlledGameEnvironment,
    GameEnvironmentAdapter,
)
from environment.live_loop import (  # noqa: E402
    LIMITATIONS,
    NEURAL_SCHEDULE_INTERFACE,
    RECORD_FIELDS,
    ClockSync,
    LiveBancStepper,
    LiveSensoryDrive,
    NeuralClosedLoop,
)
from experiments.phase_4h import common  # noqa: E402
from motor.action_decoder import GameActionDecoder  # noqa: E402
from sensory.population_encoder import build_encoders  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase_7_closed_loop.yaml"

SCIENTIFIC_STATUS = [
    "The feature-to-BANC population assignment is the Phase 4H.4 hypothesis or "
    "convention; it is not a measured sensory pathway.",
    "LEFT, RIGHT and JUMP are decoder labels derived from published effector "
    "annotations, not identified biological motor commands. UNMAPPED and DUCK "
    "execute NO_ACTION.",
    "The game reward is a synthetic task reward defined by the game rules; it "
    "is not a biological dopamine, octopamine or serotonin measurement.",
    "The published structural synapse weights are fixed for the whole episode; "
    "this run measures control, not learning.",
    "Distances are normalised game-world units, not metric distances.",
]


def digest_file(path: Path) -> str:
    handle = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            handle.update(chunk)
    return handle.hexdigest()


def relative(path: Path) -> str:
    return str(Path(path).resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")


def build_components(raw: dict):
    """Construct the loop strictly from existing classes and config files."""
    neural = raw["neural"]
    world = common.load_world()

    mapping_path = PROJECT_ROOT / raw["sensory"]["mapping_config"]
    mapping_payload = common.load_yaml(mapping_path)
    encoders = build_encoders(mapping_payload["features"])
    current_pa = {
        feature: float(payload.get("current_pa", 0.0))
        for feature, payload in mapping_payload["features"].items()
    }
    action_masks = {
        name: np.asarray(mask, dtype=bool)
        for name, mask in world.populations.masks.items()
    }
    mapping = BancSensoryMapping(
        world.nodes,
        world.graph,
        mapping_payload["mapping"],
        motor_mask=world.populations.motor_mask,
        action_masks=action_masks,
    )
    unmapped = dict(mapping_payload["mapping"].get("unmapped_features", {}))
    drive = LiveSensoryDrive(
        mapping,
        encoders,
        current_pa=current_pa,
        unmapped_features=unmapped,
    )

    clock = ClockSync(
        neural_dt_ms=float(raw["clock"]["neural_dt_ms"]),
        game_dt_s=float(raw["clock"]["game_dt_s"]),
    )
    stepper = LiveBancStepper(
        world.graph,
        world.policy,
        neuron_params=world.neuron_params,
        dt_ms=float(neural["dt_ms"]),
        duration_ms=float(neural["nominal_duration_ms"]),
        seed=int(neural["seed"]),
        background_current_pa=float(neural["background_current_pa"]),
        noise_std_pa=float(neural["noise_std_pa"]),
        input_schedule=drive,
    )
    if abs(float(stepper.dt_ms) - clock.neural_dt_ms) > 1e-12:
        raise ValueError("clock neural_dt_ms does not match the simulator")

    game = raw["game"]
    environment = ControlledGameEnvironment(
        config=game["game_config"],
        game_root=game["game_root"],
        max_steps=int(game["max_steps"]),
        distance_horizon=float(game["distance_horizon"]),
        render_mode=game["render_mode"],
    )
    if abs(float(environment.env.dt) - clock.game_dt_s) > 1e-9:
        raise ValueError(
            "configured game_dt_s does not match the controlled game timestep"
        )
    adapter = GameEnvironmentAdapter(environment=environment)

    decoder = GameActionDecoder(world.populations, world.decoder_config)

    loop = NeuralClosedLoop(
        adapter,
        stepper,
        drive,
        decoder,
        clock=clock,
        max_updates=int(raw["demonstration"]["max_updates"]),
    )
    return {
        "world": world,
        "mapping_payload": mapping_payload,
        "mapping": mapping,
        "drive": drive,
        "stepper": stepper,
        "environment": environment,
        "adapter": adapter,
        "decoder": decoder,
        "clock": clock,
        "loop": loop,
    }


def first_present(records: list[dict], key: str):
    for record in records:
        if record.get(key):
            return record
    return None


def first_non_neutral(records: list[dict]):
    for record in records:
        decoder = record.get("decoder")
        if decoder and decoder.get("state") not in (None, "NO_ACTION"):
            return record
    return None


def pipeline_evidence(records: list[dict], components: dict) -> dict:
    """One measured example for each stage of the loop."""
    first = records[0] if records else None
    driven = first_present(records, "total_sensory_current_pa")
    spiking = None
    for record in records:
        if record["spikes_this_update"] > 0:
            spiking = record
            break
    decoded = first_non_neutral(records)
    rewarded = None
    for record in records:
        if record["reward_total"] != 0.0:
            rewarded = record
            break
    stepper = components["stepper"]
    return {
        "1_observation_to_game_state": (
            None
            if first is None
            else {
                "update": first["update"],
                "game_time_ms": first["game_time_ms"],
                "features": first["features"],
                "game_state_adapter": "environment.game_state.GameObservationAdapter",
            }
        ),
        "2_game_state_to_phase3_encoding": (
            None
            if driven is None
            else {
                "update": driven["update"],
                "n_stimulated_neurons": int(
                    components["drive"].stimulated_indices.size
                ),
                "feature_currents_pa": driven["feature_currents_pa"],
                "total_sensory_current_pa": driven["total_sensory_current_pa"],
                "encoder": "sensory.population_encoder.encode_state",
                "schedule_interface": NEURAL_SCHEDULE_INTERFACE,
            }
        ),
        "3_activity_recorded": (
            None
            if spiking is None
            else {
                "update": spiking["update"],
                "neural_time_ms": spiking["neural_time_ms"],
                "spikes_this_update": spiking["spikes_this_update"],
                "total_spikes": spiking["total_spikes"],
                "recorder": "brain.neural_activity.SpikeRecorder",
                "first_spike_time_ms": (
                    round(float(stepper.recorder.spike_times_ms[0]), 6)
                    if stepper.recorder.n_spikes
                    else None
                ),
            }
        ),
        "4_phase4_decoder": (
            None
            if decoded is None
            else {
                "update": decoded["update"],
                "neural_time_ms": decoded["neural_time_ms"],
                "decoder": decoded["decoder"],
                "note": (
                    "the first update whose decoder output is not NO_ACTION"
                ),
            }
        ),
        "5_action_reaches_game": (
            None
            if first is None
            else {
                "update": first["update"],
                "decoder_state": None
                if first["decoder"] is None
                else first["decoder"]["state"],
                "mapping": first["mapping"],
                "game_after_step": first["game"],
            }
        ),
        "6_reward_and_events": (
            None
            if rewarded is None
            else {
                "update": rewarded["update"],
                "reward_total": rewarded["reward_total"],
                "reward_components": rewarded["reward_components"],
                "reward_event_types": rewarded["reward_event_types"],
                "provenance": rewarded["reward_provenance"],
            }
        ),
        "7_feedback_to_next_update": (
            None
            if len(records) < 2
            else {
                "update": records[1]["update"],
                "game_time_ms": records[1]["game_time_ms"],
                "features": records[1]["features"],
                "previous_neural_time_ms": records[0]["neural_time_ms"],
                "neural_time_ms": records[1]["neural_time_ms"],
            }
        ),
    }


def build_checks(
    components: dict, run: dict, repeat: dict | None, limit: int
) -> dict:
    records = run["records"]
    summary = run["summary"]
    clock = components["clock"]
    stepper = components["stepper"]
    adapter = components["adapter"]
    last = records[-1] if records else None
    expected_steps = (
        0 if last is None else clock.target_step(last["update"] * clock.game_dt_s)
    )
    per_update = sorted({record["neural_steps"] for record in records})
    return {
        "records_complete": bool(records)
        and all(set(record) == set(RECORD_FIELDS) for record in records),
        "game_state_per_update": len(adapter.game.conversions) == len(records) + 1,
        "sensory_input_delivered": any(
            record["total_sensory_current_pa"] > 0.0 for record in records
        ),
        "neural_activity_recorded": summary["total_spikes"] > 0,
        "decoder_called_every_update": all(
            record["decoder"] is not None for record in records
        ),
        "decoder_received_motor_activity": summary["motor_spikes"] > 0,
        "decoded_action_supported": any(
            record["mapping"]["supported"]
            and record["executed_action"] != "NO_ACTION"
            for record in records
        ),
        "game_advanced_every_update": len(records) == adapter.game.n_steps,
        "reward_provenance_recorded": all(
            record["reward_provenance"] for record in records
        ),
        "neural_state_persisted": summary["neural_resets_during_episode"] == 0,
        "time_synchronised": (
            summary["neural_steps"] == expected_steps
            and set(per_update).issubset({33, 34})
        ),
        "weights_unchanged": bool(summary["weights_unchanged"]),
        "deterministic_replay": (
            None
            if repeat is None
            else run["fingerprint"] == repeat["fingerprint"]
        ),
        "episode_finished": bool(
            summary["terminated"] or summary["truncated"]
        )
        or summary["updates"] >= limit,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-updates", type=int, default=None)
    parser.add_argument("--skip-repeat", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if bool(raw.get("plasticity", {}).get("enabled", False)):
        raise SystemExit("this experiment is fixed-weight; plasticity must be off")
    seed = int(args.seed if args.seed is not None else raw["demonstration"]["seed"])
    max_updates = int(
        args.max_updates
        if args.max_updates is not None
        else raw["demonstration"]["max_updates"]
    )
    output = Path(args.output or PROJECT_ROOT / raw["recording"]["output"]).resolve()

    started = time.perf_counter()
    integrity_before = common.integrity_snapshot()
    components = build_components(raw)
    built = time.perf_counter()

    run = components["loop"].run(seed=seed, max_updates=max_updates)
    first_run_seconds = time.perf_counter() - built

    repeat = None
    if not args.skip_repeat and bool(raw["demonstration"].get("repeat", True)):
        repeat = components["loop"].run(seed=seed, max_updates=max_updates)
        repeat = {
            "fingerprint": repeat["fingerprint"],
            "summary": {
                key: repeat["summary"][key]
                for key in (
                    "updates",
                    "neural_steps",
                    "total_spikes",
                    "terminated",
                    "truncated",
                    "termination_reason",
                    "weights_unchanged",
                )
            },
        }

    environment = components["environment"]
    stepper = components["stepper"]
    game_recording = Path(
        PROJECT_ROOT / raw["recording"]["game_recording"]
    ).resolve()
    neural_activity = Path(
        PROJECT_ROOT / raw["recording"]["neural_activity"]
    ).resolve()
    environment.save_recording(game_recording)
    stepper.recorder.save(neural_activity, max(stepper.time_ms, stepper.dt_ms))

    integrity_after = common.integrity_snapshot()
    checks = build_checks(components, run, repeat, max_updates)
    world = components["world"]
    mapping = components["mapping"]
    drive = components["drive"]

    used_files = [
        config_path,
        PROJECT_ROOT / raw["neural"]["nodes"],
        PROJECT_ROOT / raw["neural"]["graph"],
        PROJECT_ROOT / raw["neural"]["policy_config"],
        PROJECT_ROOT / raw["neural"]["neuron_config"],
        PROJECT_ROOT / raw["sensory"]["mapping_config"],
        PROJECT_ROOT / raw["motor"]["decoder_config"],
        PROJECT_ROOT / "configs" / "phase_7_environment.yaml",
    ]
    payload = {
        "phase": "7",
        "title": "Live fixed-weight neural closed loop on the controlled game",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": shlex.join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        "config": {
            "path": relative(config_path),
            "sha256": digest_file(config_path),
            "environment_seed": seed,
            "max_updates": max_updates,
            "plasticity_enabled": False,
            "game_dt_s": components["clock"].game_dt_s,
            "neural_dt_ms": components["clock"].neural_dt_ms,
            "steps_per_update_rule": components["clock"].describe(),
            "input_schedule_interface": NEURAL_SCHEDULE_INTERFACE,
            "sensory_hold": raw["sensory"]["hold"],
        },
        "input_hashes": {relative(path): digest_file(path) for path in used_files},
        "neural": {
            "source": "brain.banc_simulator.BancSimulator (subclassed additively)",
            "graph": {
                "artifact": relative(PROJECT_ROOT / raw["neural"]["graph"]),
                "threshold": int(world.graph.threshold),
                "n_nodes": int(world.graph.n_nodes),
                "n_edges": int(world.graph.n_edges),
                "n_synapses": int(world.graph.n_synapses),
            },
            "policy": world.policy.describe(),
            "neuron": {
                field: getattr(world.neuron_params, field)
                for field in (
                    "capacitance_pf",
                    "leak_conductance_ns",
                    "resting_potential_mv",
                    "threshold_mv",
                    "reset_potential_mv",
                    "refractory_ms",
                    "minimum_potential_mv",
                )
            },
            "stepper": stepper.describe(),
            "weights_fingerprint_before": run["summary"]["weights_before"],
            "weights_fingerprint_after": run["summary"]["weights_after"],
        },
        "sensory": {
            "mapping": mapping.report(),
            "drive": drive.describe(),
            "unmapped_features": dict(
                components["mapping_payload"]["mapping"].get(
                    "unmapped_features", {}
                )
            ),
        },
        "motor": {
            "decoder": components["decoder"].describe(),
            "populations": world.populations.report(),
            "window_ms": components["loop"].window_ms,
        },
        "game": {
            **environment.describe(),
            "seed": seed,
            "n_steps": int(environment.n_steps),
        },
        "run": {
            "summary": run["summary"],
            "fingerprint": run["fingerprint"],
            "wall_time_s": round(first_run_seconds, 3),
        },
        "repeat": repeat,
        "pipeline": pipeline_evidence(run["records"], components),
        "records": run["records"],
        "checks": checks,
        "integrity": {
            "before": integrity_before,
            "after": integrity_after,
            "unchanged_during_run": (
                integrity_before["failures"] == integrity_after["failures"]
            ),
            "non_readme_failures": [
                failure
                for failure in integrity_after["failures"]
                if failure["path"] != "README.md"
            ],
            "note": (
                "README.md is pinned by the Phase 4H baseline and was already "
                "modified before this experiment; the 36 other pinned files "
                "must match."
            ),
        },
        "outputs": {
            "experiment": relative(output),
            "game_recording": relative(game_recording),
            "neural_activity": relative(neural_activity),
        },
        "limitations": LIMITATIONS,
        "scientific_status": SCIENTIFIC_STATUS,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=1, allow_nan=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "output": str(output),
                "wall_time_s": round(time.perf_counter() - started, 2),
                "run": {
                    key: run["summary"][key]
                    for key in (
                        "seed",
                        "updates",
                        "neural_steps",
                        "total_spikes",
                        "motor_spikes",
                        "action_counts",
                        "unmapped_or_invalid",
                        "coins_collected",
                        "collisions",
                        "total_reward",
                        "termination_reason",
                        "weights_unchanged",
                    )
                },
                "checks": checks,
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
