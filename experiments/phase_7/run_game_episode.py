"""Run one controlled endless-surfer episode through FLY-SURFER adapters.

Examples
--------
    python experiments/phase_7/run_game_episode.py --agent random --seed 42
    python experiments/phase_7/run_game_episode.py --agent rule_based --seed 7 --record out.json
    python experiments/phase_7/run_game_episode.py --agent phase4 --seed 42 --max-steps 300
    python experiments/phase_7/run_game_episode.py --agent rule_based --visual

``--headless`` (the default when ``--visual`` is absent) never creates a
renderer. The simulation advances one fixed game timestep per call, so visual
playback does not change the episode outcome.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from environment import ControlledGameEnvironment  # noqa: E402
from experiments.phase_7.phase4_agent import (  # noqa: E402
    DEFAULT_ARTIFACT,
    load_phase4_outputs,
    Phase4MotorAgent,
)


def build_agent(name: str, seed: int, api, phase4_artifact: Path):
    if name == "random":
        return api.random_agent(seed=seed + 1)
    if name == "rule_based":
        return api.rule_based_agent()
    if name == "phase4":
        return Phase4MotorAgent(load_phase4_outputs(phase4_artifact))
    raise ValueError(f"unknown agent {name!r}")


def compact_step(record: dict) -> dict:
    return {
        "step": record["fly_surfer"]["step"],
        "time_ms": record["fly_surfer"]["game_state"]["state"]["time_ms"],
        "action": record["fly_surfer"]["action"],
        "game_state": record["fly_surfer"]["game_state"]["state"],
        "reward": record["fly_surfer"]["reward"],
        "termination_reason": record["termination_reason"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["random", "rule_based", "phase4"], required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-steps", type=int, default=900)
    parser.add_argument("--game-root", default=None)
    parser.add_argument("--game-config", default=None)
    parser.add_argument("--distance-horizon", type=float, default=25.0)
    parser.add_argument("--phase4-artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--record", default=None, help="write the game recording here")
    parser.add_argument("--output", default=None, help="write the episode summary JSON here")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--visual", action="store_true")
    args = parser.parse_args()
    if args.visual and args.headless:
        parser.error("--visual and --headless are mutually exclusive")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    env = ControlledGameEnvironment(
        config=args.game_config,
        game_root=args.game_root,
        max_steps=args.max_steps,
        distance_horizon=args.distance_horizon,
        render_mode="visual" if args.visual else "headless",
    )
    agent = build_agent(args.agent, args.seed, env.api, Path(args.phase4_artifact))

    observation = env.reset(args.seed)
    terminated = truncated = False
    steps = 0
    mapping_counts: dict[str, int] = {}
    sample_steps: list[dict] = []
    renderer = None
    clock = None
    if args.visual:
        import pygame

        clock = pygame.time.Clock()
        env.render("RUNNING")
        running = True
    else:
        running = True

    while running and not (terminated or truncated):
        if args.visual:
            import pygame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
            if not running:
                break
        output = agent.act(observation)
        observation, reward, terminated, truncated, info = env.step(output)
        steps += 1
        mapping = info["fly_surfer"]["action"]
        key = f"{mapping['requested_state']}->{mapping['executed_action']}"
        mapping_counts[key] = mapping_counts.get(key, 0) + 1
        if len(sample_steps) < 5:
            sample_steps.append(compact_step(info))
        if args.visual:
            env.render("GAME OVER" if env.env.done else "RUNNING")
            clock.tick(60)

    if args.visual and steps >= 5:
        sample_steps[-1] = compact_step(env.last_info)
    if args.record:
        env.save_recording(args.record)
    if args.visual:
        env.close()

    reward = env.reward_function
    payload = {
        "phase": "7",
        "command": shlex.join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        "agent": args.agent,
        "seed": env.seed,
        "game": {
            "root": str(env.api.root),
            "config": args.game_config or "configs/default.yaml",
            "observation_schema_version": env.api.observation_schema_version,
            "simulation_dt_s": float(env.env.dt),
        },
        "run": {
            "max_steps": args.max_steps,
            "steps": steps,
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "termination_reason": env.env.metrics.termination_reason,
            "headless": not args.visual,
            "renderer_created": args.visual,
        },
        "summary": env.summary(),
        "reward": {
            "total": round(reward.total, 9),
            "components": reward.component_totals(),
            "n_steps": reward.n_steps,
            "n_reward_steps": reward.n_reward_steps,
            "n_neutral_steps": reward.n_neutral_steps,
            "classification": reward.describe()["classification"],
            "stream_digest": reward.stream.digest(),
            "stream_total": round(reward.stream.total(), 9),
        },
        "action_counts": env.action_counts(),
        "mapping_counts": mapping_counts,
        "adapters": {
            "game_state_conversions": len(env.conversions),
            "unrepresented_objects": sum(
                len(conversion.unrepresented) for conversion in env.conversions
            ),
            "estimated_fields": list(env.conversions[-1].estimated_fields),
            "warnings": list(env.conversions[-1].warnings),
            "distance_horizon": env.conversions[-1].distance_horizon,
            "sensory_timeline_segments": len(env.timeline()),
        },
        "sample_steps": sample_steps,
        "recording": args.record,
    }
    if args.agent == "phase4":
        payload["phase4"] = agent.describe()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({"output": str(target), "steps": steps, "seed": env.seed}))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
