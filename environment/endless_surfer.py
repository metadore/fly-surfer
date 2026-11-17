"""Locate and import the standalone ``endless-surfer`` game.

The game is a separate repository (``metadore/endless-surfer``) vendored under
``external/``. It is not reimplemented here: this module only finds its root
and imports its existing public API. The game uses absolute imports of its own
top-level packages (``game_env``, ``agents``, ``rendering``), so its root is
appended to ``sys.path`` once. Appending rather than prepending keeps the
FLY-SURFER packages authoritative if a name ever exists in both trees.
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GAME_ROOT_ENV = "FLY_SURFER_GAME_ROOT"

_REQUIRED_FILES = (
    "game_env/environment.py",
    "game_env/config_loader.py",
    "game_env/observations.py",
    "agents/__init__.py",
)

_CANDIDATE_ROOTS = (
    "external/endless-surfer",
    "external/endless-surfer-main/endless-surfer-main",
    "external/endless-surfer-main",
    "external/endless-surfer/endless-surfer-main",
)


def find_game_root(explicit: str | os.PathLike | None = None) -> Path:
    """Return the game root, or raise with every location that was tried."""
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    else:
        env_value = os.environ.get(GAME_ROOT_ENV)
        if env_value:
            candidates.append(Path(env_value))
        candidates.extend(PROJECT_ROOT / relative for relative in _CANDIDATE_ROOTS)

    checked: list[str] = []
    for candidate in candidates:
        root = candidate.expanduser().resolve()
        checked.append(str(root))
        if all((root / relative).is_file() for relative in _REQUIRED_FILES):
            return root
    raise FileNotFoundError(
        "could not locate the endless-surfer game; set "
        f"{GAME_ROOT_ENV} or provide game_root. Checked: {checked}"
    )


@dataclass(frozen=True)
class GameAPI:
    """The existing game objects FLY-SURFER integrates with."""

    root: Path
    environment: type
    action: type
    invalid_action_error: type
    episode_ended_error: type
    difficulty: type
    load_config: Callable
    recorder: type
    replay: Callable
    observation_schema_version: int
    random_agent: type
    rule_based_agent: type

    @property
    def default_config_path(self) -> Path:
        return self.root / "configs" / "default.yaml"

    def default_config(self):
        return self.load_config(self.default_config_path)

    def renderer(self):
        """Import the Pygame renderer only when rendering is requested."""
        return importlib.import_module("rendering").Renderer


_API_CACHE: dict[Path, GameAPI] = {}


def _import_from_game(root: Path):
    if str(root) not in sys.path:
        sys.path.append(str(root))

    environment_module = importlib.import_module("game_env.environment")
    actions_module = importlib.import_module("game_env.actions")
    difficulty_module = importlib.import_module("game_env.difficulty")
    config_module = importlib.import_module("game_env.config_loader")
    recording_module = importlib.import_module("game_env.recording")
    replay_module = importlib.import_module("game_env.replay")
    observations_module = importlib.import_module("game_env.observations")
    agents_module = importlib.import_module("agents")

    imported_root = Path(environment_module.__file__).resolve().parents[1]
    if imported_root != root:
        raise RuntimeError(
            "a different game_env package is already imported from "
            f"{imported_root}; refusing to mix two game trees"
        )
    return (
        environment_module,
        actions_module,
        difficulty_module,
        config_module,
        recording_module,
        replay_module,
        observations_module,
        agents_module,
    )


def load_game_api(
    game_root: str | os.PathLike | None = None,
) -> GameAPI:
    """Import the game API once per resolved root."""
    root = find_game_root(game_root)
    cached = _API_CACHE.get(root)
    if cached is not None:
        return cached

    (
        environment_module,
        actions_module,
        difficulty_module,
        config_module,
        recording_module,
        replay_module,
        observations_module,
        agents_module,
    ) = _import_from_game(root)

    api = GameAPI(
        root=root,
        environment=environment_module.EndlessRunnerEnv,
        action=actions_module.Action,
        invalid_action_error=actions_module.InvalidActionError,
        episode_ended_error=environment_module.EpisodeEndedError,
        difficulty=difficulty_module.Difficulty,
        load_config=config_module.load_config,
        recorder=recording_module.EpisodeRecorder,
        replay=replay_module.replay,
        observation_schema_version=observations_module.SCHEMA_VERSION,
        random_agent=agents_module.RandomAgent,
        rule_based_agent=agents_module.RuleBasedAgent,
    )
    _API_CACHE[root] = api
    return api
