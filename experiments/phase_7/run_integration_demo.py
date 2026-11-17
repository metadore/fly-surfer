"""Run the fixed-seed Phase 7 integration demonstration.

The script executes real episodes through the controlled game, checks that a
repeated run reproduces the recording, replays each recording with the game's
own strict replay, and writes the measured results to
``experiments/results/phase_7/game_integration_demo.json``.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from environment import (  # noqa: E402
    ControlledGameEnvironment,
    GameEnvironmentAdapter,
)
from experiments.phase_7.phase4_agent import (  # noqa: E402
    load_phase4_outputs,
    Phase4MotorAgent,
)
from plasticity.reward import ScriptedRewardProvider  # noqa: E402
from sensory.population_encoder import build_encoders, encode_state  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase_7_environment.yaml"
SENSORY_CONFIG_PATH = PROJECT_ROOT / "configs" / "sensory_config.yaml"


def digest(payload) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_agent(name: str, seed: int, api, phase4_artifact: Path):
    if name == "random":
        return api.random_agent(seed=seed + 1)
    if name == "rule_based":
        return api.rule_based_agent()
    if name == "phase4":
        return Phase4MotorAgent(load_phase4_outputs(phase4_artifact))
    raise ValueError(f"unknown agent {name!r}")


def run_episode(
    agent_name: str,
    seed: int,
    max_steps: int,
    *,
    config: dict,
    phase4_artifact: Path,
    replay: bool,
):
    env = ControlledGameEnvironment(
        config=config["game_config"],
        game_root=config["game_root"],
        max_steps=max_steps,
        distance_horizon=float(config["distance_horizon"]),
        render_mode="headless",
    )
    agent = build_agent(agent_name, seed, env.api, phase4_artifact)
    adapter = GameEnvironmentAdapter(environment=env)
    result = adapter.run_episode(agent, seed=seed)
    recording = env.recording_data
    recording_digest = digest(recording)
    replay_summary = None
    if replay:
        with tempfile.TemporaryDirectory() as tmp:
            path = env.save_recording(Path(tmp) / "recording.json")
            replay_summary = env.api.replay(path)
    return env, adapter, agent, result, recording_digest, replay_summary


def condition_record(
    agent_name: str,
    seed: int,
    max_steps: int,
    *,
    config: dict,
    phase4_artifact: Path,
):
    env_a, adapter_a, _, run_a, digest_a, replay_summary = run_episode(
        agent_name,
        seed,
        max_steps,
        config=config,
        phase4_artifact=phase4_artifact,
        replay=True,
    )
    env_b, _, _, run_b, digest_b, _ = run_episode(
        agent_name,
        seed,
        max_steps,
        config=config,
        phase4_artifact=phase4_artifact,
        replay=False,
    )
    reward = env_a.reward_function
    records = run_a.records
    times = [record.time_ms for record in records]
    provider = reward.modulation_provider()
    emitted = 0.0
    update_steps = 0
    for index, time_ms in enumerate(times):
        value = provider.step(index, time_ms)
        if value is not None:
            emitted += value
            update_steps += 1
    scripted_total = (
        ScriptedRewardProvider(reward.schedule()).step(0, times[-1]) if times else 0.0
    )
    mapping_counts: dict[str, int] = {}
    for record in records:
        mapping = record.mapping
        key = f"{mapping.requested_state}->{mapping.executed_action}"
        mapping_counts[key] = mapping_counts.get(key, 0) + 1
    action_counts = env_a.action_counts()
    payload = {
        "agent": agent_name,
        "seed": env_a.seed,
        "max_steps": max_steps,
        "steps": run_a.steps,
        "terminated": run_a.terminated,
        "truncated": run_a.truncated,
        "termination_reason": run_a.termination_reason,
        "summary": run_a.summary,
        "score": run_a.summary["final_score"],
        "coins_collected": run_a.summary["coins_collected"],
        "collisions": run_a.summary["collisions"],
        "total_reward": round(run_a.total_reward, 9),
        "reward_components": reward.component_totals(),
        "reward_stream_digest": reward.stream.digest(),
        "action_counts": action_counts,
        "mapping_counts": mapping_counts,
        "recording_digest": digest_a,
        "replay_ok": replay_summary == run_a.summary,
        "reproducible": (digest_a == digest_b) and (run_a.as_dict() == run_b.as_dict()),
        "headless": True,
        "renderer_created": False,
        "phase5": {
            "provider_update_steps": update_steps,
            "emitted_modulation": round(emitted, 9),
            "scripted_total": round(scripted_total, 9),
            "matches_game_reward": abs(emitted - run_a.total_reward) < 1e-9,
        },
        "adapters": {
            "game_state_conversions": len(env_a.conversions),
            "unrepresented_objects": sum(
                len(conversion.unrepresented) for conversion in env_a.conversions
            ),
            "sensory_timeline_segments": len(adapter_a.timeline()),
        },
        "reproduce": (
            "python experiments/phase_7/run_game_episode.py "
            f"--agent {agent_name} --seed {seed} --max-steps {max_steps}"
        ),
    }
    return payload, env_a, run_a


def find_event(run, event_type: str):
    for record in run.records:
        if event_type in record.step_reward.event_types:
            return {
                "step": record.step,
                "time_ms": round(record.time_ms, 6),
                "player_lane": int(record.game_state.player.lane),
                "player_state": "COLLIDED"
                if record.terminated
                else (
                    "JUMPING"
                    if record.game_state.player.jumping
                    else "ROLLING"
                    if record.game_state.player.rolling
                    else "RUNNING"
                ),
                "events": list(record.step_reward.event_types),
                "reward_components": {
                    key: round(value, 9)
                    for key, value in record.step_reward.components.items()
                },
                "total_reward": round(record.reward, 9),
                "termination_reason": record.step_reward.termination_reason,
                "coins_collected": int(record.observation["coins_collected"]),
            }
    return None


def phase3_check(env) -> dict:
    config = yaml.safe_load(SENSORY_CONFIG_PATH.read_text(encoding="utf-8"))
    encoders = build_encoders(config["features"])
    state = env.game_state
    responses = encode_state(state.features(), encoders)
    n_neurons = sum(len(values) for values in responses.values())
    total = float(sum(float(values.sum()) for values in responses.values()))
    return {
        "source": "configs/sensory_config.yaml",
        "n_encoders": len(encoders),
        "n_neurons": n_neurons,
        "total_activation": round(total, 9),
        "state_time_ms": state.time_ms,
        "note": (
            "the final converted GameState is encoded by the existing Phase 3 "
            "population encoders; no neural simulation is run here"
        ),
    }


def main() -> int:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    demo = raw.get("demo", {})
    seeds = [int(seed) for seed in demo.get("seeds", [42, 7, 123])]
    agents = list(demo.get("agents", ["random", "rule_based"]))
    max_steps = int(demo.get("max_steps", 900))
    phase4 = demo.get("phase4", {})
    phase4_seeds = [int(seed) for seed in phase4.get("seeds", [42, 7])]
    phase4_steps = int(phase4.get("max_steps", 300))
    phase4_artifact = PROJECT_ROOT / phase4.get(
        "artifact", "experiments/results/phase_4/motor_output_demo.json"
    )
    output = PROJECT_ROOT / demo.get(
        "output", "experiments/results/phase_7/game_integration_demo.json"
    )

    conditions: list[dict] = []
    envs: dict[tuple[str, int], ControlledGameEnvironment] = {}
    runs: dict[tuple[str, int], object] = {}
    for agent_name in agents:
        for seed in seeds:
            record, env, run = condition_record(
                agent_name,
                seed,
                max_steps,
                config=raw,
                phase4_artifact=phase4_artifact,
            )
            conditions.append(record)
            envs[(agent_name, seed)] = env
            runs[(agent_name, seed)] = run

    phase4_conditions: list[dict] = []
    for seed in phase4_seeds:
        record, env, run = condition_record(
            "phase4",
            seed,
            phase4_steps,
            config=raw,
            phase4_artifact=phase4_artifact,
        )
        phase4_conditions.append(record)
        envs[("phase4", seed)] = env
        runs[("phase4", seed)] = run

    truncation_env = ControlledGameEnvironment(
        config=raw["game_config"],
        game_root=raw["game_root"],
        max_steps=100,
        distance_horizon=float(raw["distance_horizon"]),
        render_mode="headless",
    )
    truncation_agent = truncation_env.api.rule_based_agent()
    truncation_run = GameEnvironmentAdapter(
        environment=truncation_env
    ).run_episode(truncation_agent, seed=42)
    truncation = {
        "seed": truncation_env.seed,
        "steps": truncation_run.steps,
        "terminated": truncation_run.terminated,
        "truncated": truncation_run.truncated,
        "termination_reason": truncation_run.termination_reason,
        "summary": truncation_run.summary,
        "reproduce": (
            "python experiments/phase_7/run_game_episode.py "
            "--agent rule_based --seed 42 --max-steps 100"
        ),
    }

    coin_example = None
    collision_example = None
    for key in (("rule_based", seeds[0]), ("random", seeds[0])):
        if key in runs:
            coin_example = coin_example or find_event(runs[key], "coin_collected")
            collision_example = collision_example or find_event(
                runs[key], "collision"
            )
    if collision_example is None:
        for key, run in runs.items():
            collision_example = find_event(run, "collision")
            if collision_example:
                break
    if coin_example is None:
        for key, run in runs.items():
            coin_example = find_event(run, "coin_collected")
            if coin_example:
                break

    unmapped_example = None
    for record in phase4_conditions:
        for run in (runs[("phase4", record["seed"])],):
            for step in run.records:
                if step.mapping and step.mapping.unmapped:
                    unmapped_example = step.mapping.as_dict()
                    break
            if unmapped_example:
                break
        if unmapped_example:
            break

    representative = envs.get(("rule_based", seeds[0]))
    if representative is None:
        raise RuntimeError("the demo configuration must include a rule_based seed")
    actual_classification = representative.reward_function.describe()[
        "classification"
    ]
    declared = " ".join(
        str(raw.get("reward", {}).get("classification", "")).split()
    )
    if declared and declared != actual_classification:
        raise ValueError(
            "configs/phase_7_environment.yaml reward.classification does not "
            "match the integration reward classification"
        )
    payload = {
        "phase": "7",
        "title": "Controlled endless-surfer integration",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": shlex.join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        "game": {
            "root": str(representative.api.root),
            "observation_schema_version": representative.api.observation_schema_version,
            "simulation_dt_s": float(representative.env.dt),
            "recording_schema_version": 1,
        },
        "config": {
            "source": str(CONFIG_PATH),
            "game_config": raw.get("game_config") or "configs/default.yaml",
            "distance_horizon": float(raw["distance_horizon"]),
            "demo_max_steps": max_steps,
            "seeds": seeds,
        },
        "reward_classification": actual_classification,
        "conditions": conditions,
        "phase4_conditions": phase4_conditions,
        "truncation": truncation,
        "examples": {
            "coin_collection": coin_example,
            "collision": collision_example,
            "unmapped_motor_output": unmapped_example,
        },
        "phase3": phase3_check(representative),
        "checks": {
            "all_replays_ok": all(
                record["replay_ok"] for record in (*conditions, *phase4_conditions)
            ),
            "all_reproducible": all(
                record["reproducible"]
                for record in (*conditions, *phase4_conditions)
            ),
            "all_headless": all(
                record["headless"] and not record["renderer_created"]
                for record in (*conditions, *phase4_conditions)
            ),
            "all_rewards_match_phase5": all(
                record["phase5"]["matches_game_reward"]
                for record in (*conditions, *phase4_conditions)
            ),
        },
        "scientific_status": [
            "The reward is a synthetic task reward defined by the game rules; "
            "it is not a biological dopamine measurement.",
            "Distances are game world units normalised by the declared horizon, "
            "not metric distances.",
            "The Phase 4 motor outputs are replayed open loop from a previous "
            "experiment; no BANC simulation runs during these episodes.",
            "No learning or Phase 8 training is performed.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "conditions": len(conditions) + len(phase4_conditions),
                "checks": payload["checks"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
