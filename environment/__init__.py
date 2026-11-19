"""Phase 7 integration with the standalone controlled endless-runner game."""

from environment.action_adapter import (
    GAME_ACTIONS,
    ActionMapping,
    GameActionAdapter,
)
from environment.endless_surfer import GameAPI, find_game_root, load_game_api
from environment.environment_adapter import (
    AdapterStep,
    EpisodeRun,
    GameEnvironmentAdapter,
    build_timeline,
)
from environment.game_state import (
    DEFAULT_DISTANCE_HORIZON,
    GameObservationAdapter,
    ObservationConversion,
    UnrepresentedObject,
)
from environment.game_controller import ControllerCycle, GameController
from environment.reward_function import (
    REWARD_CLASSIFICATION,
    REWARD_COMPONENTS,
    GameRewardFunction,
    StepReward,
)
from environment.subway_environment import ControlledGameEnvironment

__all__ = [
    "GAME_ACTIONS",
    "REWARD_CLASSIFICATION",
    "REWARD_COMPONENTS",
    "DEFAULT_DISTANCE_HORIZON",
    "ActionMapping",
    "AdapterStep",
    "ControlledGameEnvironment",
    "ControllerCycle",
    "EpisodeRun",
    "GameAPI",
    "GameActionAdapter",
    "GameController",
    "GameEnvironmentAdapter",
    "GameObservationAdapter",
    "GameRewardFunction",
    "ObservationConversion",
    "StepReward",
    "UnrepresentedObject",
    "build_timeline",
    "find_game_root",
    "load_game_api",
]
