"""BANC-scale component factory for one Phase 8 evaluation episode.

SCIENTIFIC STATUS
    The factory assembles existing simulators, encoders, decoders and readouts
    into a declared condition. It adds no biological mechanism. Every heavy
    object is built per episode so no membrane, trace, readout or game state
    leaks between episodes.

    Weights are transformed structural synapse counts in pA, not
    conductances. A decoder label is not an identified biological motor
    command. A nonzero plasticity update is not evidence of learning.

Two things this module deliberately does not do:

* it never trains. F, Fbeta and E need artifacts produced by the separate
  training stage, which this task does not implement. A caller must inject a
  :class:`TrainingArtifacts` provider; without one the factory refuses rather
  than quietly evaluating an untrained model;
* it never substitutes the biological graph for a missing or refused random
  graph. Conditions C, D and C' obtain their graph only through
  :class:`experiments.phase_8.campaign.graphs.CertifiedGraphSource`, and the
  synapse policy for that graph is rebuilt from the frozen node table with the
  same sign and weight policies, then checked against the biological edge
  columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from brain.banc_graph import sha256_file
from brain.banc_synapse_policy import BancSynapsePolicy, build_synapse_policy
from environment.environment_adapter import GameEnvironmentAdapter
from environment.live_loop import ClockSync, LiveBancStepper, LiveSensoryDrive
from motor.action_decoder import GameActionDecoder
from plasticity.live_stepper import LivePlasticStepper
from plasticity.modulation import ModulationConfig
from plasticity.rules import RuleConfig, ThreeFactorRule
from plasticity.traces import TraceConfig
from plasticity.weights import WeightBounds, WeightState
from readout.features import MotorFeatureSpec
from sensory.population_encoder import build_encoders

from ..config import PROJECT_ROOT, ConfigError, load_yaml
from ..conditions import b_plastic, d_plastic
from ..conditions import e_conventional, f_readout
from ..conditions import base as conditions_base
from ..controls import a_prime, c_prime, f_beta, f_init
from ..controls import floor as floor_control
from ..seeds import MASTER_SEED, seed_plan
from .graphs import (
    CertifiedGraph,
    CertifiedGraphSource,
    GraphSelectionError,
    assert_target_exchange_alignment,
)

SENSORY_MAPPING_PATH = PROJECT_ROOT / "configs" / "banc_sensory_mapping.yaml"
PLASTICITY_PATH = PROJECT_ROOT / "configs" / "plasticity_banc.yaml"

STRUCTURE_ARMS = ("C", "D", "C_prime")
NEURAL_ARMS = ("A", "B", "C", "D", "F", "A_prime", "C_prime", "F_beta", "F_init")
CONVENTIONAL_ARMS = ("E", "E_full")
PLASTIC_ARMS = ("B", "D", "A_prime", "C_prime")
READOUT_ARMS = ("F", "F_beta", "F_init")


class FactoryError(RuntimeError):
    """The factory cannot build a declared arm without changing the design."""


@dataclass(frozen=True)
class FactorySettings:
    """Implementation constants; all are declared, none are tuned."""

    neural_dt_ms: float = 0.5
    game_dt_s: float = 1.0 / 60.0
    duration_ms: float = 60_000.0
    background_current_pa: float = 0.0
    noise_std_pa: float = 0.0
    window_ms: float = 50.0
    distance_horizon: float = 25.0
    max_game_updates: int = 900

    def describe(self) -> dict:
        return {
            "neural_dt_ms": self.neural_dt_ms,
            "game_dt_s": self.game_dt_s,
            "duration_ms": self.duration_ms,
            "background_current_pa": self.background_current_pa,
            "noise_std_pa": self.noise_std_pa,
            "window_ms": self.window_ms,
            "distance_horizon": self.distance_horizon,
            "max_game_updates": self.max_game_updates,
        }


class TrainingArtifacts:
    """Trained artifacts supplied by a caller; the factory never creates them.

    ``readouts`` maps ``(condition_id, campaign_seed)`` to a readout model;
    ``agents`` maps the same key to a conventional agent. Missing entries are a
    hard error at build time, because evaluating an untrained model in place of
    a trained one would silently change what the arm measures.
    """

    def __init__(
        self,
        *,
        readouts: Mapping[tuple[str, int], Any] | None = None,
        agents: Mapping[tuple[str, int], Any] | None = None,
        provenance: str = "caller-supplied",
    ) -> None:
        self._readouts = {
            (str(key[0]), int(key[1])): value
            for key, value in (readouts or {}).items()
        }
        self._agents = {
            (str(key[0]), int(key[1])): value
            for key, value in (agents or {}).items()
        }
        self.provenance = str(provenance)

    def readout(self, condition_id: str, seed: int) -> Any:
        key = (str(condition_id), int(seed))
        try:
            return self._readouts[key]
        except KeyError:
            raise FactoryError(
                f"no trained readout for {key[0]} at campaign seed {key[1]}; "
                "the campaign factory does not train and will not substitute "
                "an untrained readout"
            ) from None

    def agent(self, condition_id: str, seed: int) -> Any:
        key = (str(condition_id), int(seed))
        try:
            return self._agents[key]
        except KeyError:
            raise FactoryError(
                f"no trained conventional agent for {key[0]} at campaign seed "
                f"{key[1]}; the campaign factory does not train and will not "
                "substitute an untrained policy"
            ) from None

    @property
    def empty(self) -> bool:
        return not self._readouts and not self._agents

    def describe(self) -> dict:
        return {
            "provenance": self.provenance,
            "readouts": sorted(f"{key[0]}:{key[1]}" for key in self._readouts),
            "agents": sorted(f"{key[0]}:{key[1]}" for key in self._agents),
            "training_implemented_here": False,
        }


class CampaignFactory:
    """Build one episode's components for one declared arm."""

    def __init__(
        self,
        *,
        world: Any | None = None,
        graphs: CertifiedGraphSource | None = None,
        training: TrainingArtifacts | None = None,
        environment_factory: Callable[[], Any] | None = None,
        mapping_payload: Mapping[str, Any] | None = None,
        plasticity_payload: Mapping[str, Any] | None = None,
        frozen_inputs: Mapping[str, str] | None = None,
        registry: Any | None = None,
        settings: FactorySettings | None = None,
    ) -> None:
        self._world = world
        self.graphs = graphs or CertifiedGraphSource()
        self.training = training or TrainingArtifacts()
        self._registry = registry
        self._frozen_inputs = dict(frozen_inputs) if frozen_inputs else None
        self._input_hashes: dict[str, str] | None = None
        self._environment_factory = environment_factory
        self._mapping_payload = dict(mapping_payload) if mapping_payload else None
        self._plasticity_payload = (
            dict(plasticity_payload) if plasticity_payload else None
        )
        self.settings = settings or FactorySettings()
        self._graph_cache: dict[int, CertifiedGraph] = {}
        self._policy_cache: dict[int, BancSynapsePolicy] = {}
        self._alignments: dict[int, dict] = {}

    # -- lazily loaded shared inputs -------------------------------------
    @property
    def world(self) -> Any:
        if self._world is None:
            from experiments.phase_4h.common import load_world

            self._world = load_world()
        return self._world

    @property
    def mapping_payload(self) -> dict:
        if self._mapping_payload is None:
            self._mapping_payload = load_yaml(SENSORY_MAPPING_PATH)
        return self._mapping_payload

    @property
    def plasticity_payload(self) -> dict:
        if self._plasticity_payload is None:
            self._plasticity_payload = load_yaml(PLASTICITY_PATH)
        return self._plasticity_payload

    @property
    def modulation_config(self) -> ModulationConfig:
        return ModulationConfig.from_config(self.plasticity_payload["modulation"])

    def spec(self, arm: str) -> Any:
        if self._registry is not None:
            return self._registry.spec(arm)
        from ..registry import default_registry

        return default_registry().spec(arm)

    # -- frozen inputs ----------------------------------------------------
    def input_hashes(self) -> dict[str, str]:
        """SHA-256 of every frozen input declared by campaign.yaml.

        The row schema requires a non-empty input-hash map, so an undeclared
        input set is an error rather than an empty record. Digests are
        computed once per factory and never recomputed silently.
        """
        if self._input_hashes is not None:
            return dict(self._input_hashes)
        if not self._frozen_inputs:
            raise FactoryError(
                "the factory has no frozen_inputs declaration; every episode "
                "row must record the SHA-256 of its frozen inputs"
            )
        digests: dict[str, str] = {}
        for name, relative in self._frozen_inputs.items():
            source = PROJECT_ROOT / str(relative)
            if not source.is_file():
                raise FactoryError(
                    f"frozen input {name!r} is missing at {source}"
                )
            digests[str(name)] = sha256_file(source)
        self._input_hashes = digests
        return dict(digests)

    # -- graph and policy -------------------------------------------------
    def certified(self, seed: int) -> CertifiedGraph:
        seed = int(seed)
        if seed not in self._graph_cache:
            self._graph_cache[seed] = self.graphs.load(seed)
        return self._graph_cache[seed]

    def structure(self, seed: int) -> dict:
        return dict(self.certified(seed).record)

    def random_policy(self, seed: int) -> BancSynapsePolicy:
        seed = int(seed)
        if seed in self._policy_cache:
            return self._policy_cache[seed]
        certified = self.certified(seed)
        world = self.world
        alignment = assert_target_exchange_alignment(world.graph, certified.graph)
        policy = build_synapse_policy(
            certified.graph,
            world.nodes,
            world.policy.sign_policy,
            world.policy.weight_policy,
        )
        if int(policy.n_edges) != int(world.policy.n_edges):
            raise GraphSelectionError(
                "the random graph policy has a different edge count than the "
                "biological policy"
            )
        same_exc = np.array_equal(
            np.asarray(policy.edge_exc_weight),
            np.asarray(world.policy.edge_exc_weight),
        )
        same_inh = np.array_equal(
            np.asarray(policy.edge_inh_weight),
            np.asarray(world.policy.edge_inh_weight),
        )
        if not (same_exc and same_inh):
            raise GraphSelectionError(
                "edge signs/weights changed while rebuilding the random-graph "
                "policy; target exchange must preserve both"
            )
        alignment["policy_sign_arrays_equal"] = True
        self._alignments[seed] = alignment
        self._policy_cache[seed] = policy
        return policy

    def graph_and_policy(self, arm: str, seed: int) -> tuple[Any, BancSynapsePolicy, dict | None]:
        world = self.world
        if arm in STRUCTURE_ARMS:
            certified = self.certified(seed)
            policy = self.random_policy(seed)
            return certified.graph, policy, dict(certified.record)
        return world.graph, world.policy, None

    def alignment(self, seed: int) -> dict:
        if int(seed) not in self._alignments:
            self.random_policy(seed)
        return dict(self._alignments[int(seed)])

    # -- game ------------------------------------------------------------
    def environment(self) -> Any:
        if self._environment_factory is not None:
            environment = self._environment_factory()
        else:
            from environment.subway_environment import ControlledGameEnvironment

            environment = ControlledGameEnvironment(
                max_steps=int(self.settings.max_game_updates),
                distance_horizon=float(self.settings.distance_horizon),
                render_mode=None,
            )
        self._check_environment(environment)
        return environment

    def _check_environment(self, environment: Any) -> None:
        game = getattr(environment, "env", None)
        dt = float(getattr(game, "dt", float("nan")))
        if not np.isclose(dt, self.settings.game_dt_s, rtol=0.0, atol=1e-9):
            raise FactoryError(
                f"the controlled game dt {dt!r} does not match the declared "
                f"game_dt_s {self.settings.game_dt_s!r}"
            )
        if getattr(environment, "observation_adapter", None) is None:
            raise FactoryError("the controlled game has no observation adapter")

    def assert_environment(self, config: Any) -> dict:
        """Compare the declared game constants with a constructed environment."""
        from ..config import assert_environment_matches_game

        report = assert_environment_matches_game(config.environment, self.environment())
        if abs(float(self.settings.neural_dt_ms) - 0.5) > 1e-12:
            raise FactoryError("the neural timestep must stay at the declared 0.5 ms")
        return report

    def floor_adapter(self) -> GameEnvironmentAdapter:
        adapter = GameEnvironmentAdapter(environment=self.environment())
        floor_control.validate_adapter(adapter)
        return adapter

    # -- sensory interface ----------------------------------------------
    def _sensory(self) -> tuple[Any, LiveSensoryDrive]:
        from brain.banc_sensory_adapter import BancSensoryMapping

        world = self.world
        payload = self.mapping_payload
        encoders = build_encoders(payload["features"])
        current_pa = {
            str(feature): float(body.get("current_pa", 0.0))
            for feature, body in payload["features"].items()
        }
        action_masks = {
            str(name): np.asarray(mask, dtype=bool)
            for name, mask in world.populations.masks.items()
        }
        mapping = BancSensoryMapping(
            world.nodes,
            world.graph,
            payload["mapping"],
            motor_mask=world.populations.motor_mask,
            action_masks=action_masks,
        )
        drive = LiveSensoryDrive(
            mapping,
            encoders,
            current_pa=current_pa,
            unmapped_features=dict(payload["mapping"].get("unmapped_features", {})),
        )
        return mapping, drive

    # -- steppers ---------------------------------------------------------
    def _stepper_kwargs(self, drive: LiveSensoryDrive, network_seed: int) -> dict:
        return {
            "neuron_params": self.world.neuron_params,
            "dt_ms": float(self.settings.neural_dt_ms),
            "duration_ms": float(self.settings.duration_ms),
            "seed": int(network_seed),
            "background_current_pa": float(self.settings.background_current_pa),
            "noise_std_pa": float(self.settings.noise_std_pa),
            "input_schedule": drive,
        }

    def _fixed_stepper(self, graph: Any, policy: BancSynapsePolicy, drive, network_seed: int) -> LiveBancStepper:
        return LiveBancStepper(graph, policy, **self._stepper_kwargs(drive, network_seed))

    def _plastic_stepper(
        self, graph: Any, policy: BancSynapsePolicy, drive, network_seed: int, eta: float
    ) -> LivePlasticStepper:
        body = dict(self.plasticity_payload["plasticity"])
        bounds = WeightBounds.from_config(body["bounds"])
        traces = TraceConfig({"traces": dict(body["traces"])})
        if abs(float(traces.dt_ms) - float(self.settings.neural_dt_ms)) > 1e-12:
            raise FactoryError(
                "the eligibility trace dt does not match the neural timestep"
            )
        state = WeightState(graph, policy, bounds)
        rule = ThreeFactorRule(RuleConfig(eta=float(eta)), state)
        return LivePlasticStepper(
            graph,
            policy,
            weight_state=state,
            rule=rule,
            trace_config=traces,
            **self._stepper_kwargs(drive, network_seed),
        )

    # -- neural components ------------------------------------------------
    def neural_components(
        self,
        arm: str,
        *,
        seed: int,
        episode: int,
        environment_seed: int,
        master_seed: int = MASTER_SEED,
        training: bool = False,
    ) -> Any:
        """Build a fresh component bundle for one evaluation episode."""
        if training:
            raise FactoryError(
                "the campaign factory builds evaluation components only; no "
                "training stage is implemented in this task"
            )
        if arm not in NEURAL_ARMS:
            raise FactoryError(f"{arm!r} does not run the neural closed loop")
        requirements = conditions_base.requirements_for(arm)
        declared = self.spec(arm)
        # The environment stream is per-episode; network, learning and
        # structure streams are not.
        plan = seed_plan(master_seed, arm, seed, episode=int(episode))
        if int(environment_seed) != int(plan["environment"]):
            raise FactoryError(
                "the environment seed does not match the paired environment stream"
            )

        graph, policy, structure = self.graph_and_policy(arm, seed)
        if requirements.requires_structure and structure is None:
            raise FactoryError(f"{arm} requires a certified structure record")

        mapping, drive = self._sensory()
        clock = ClockSync(
            neural_dt_ms=float(self.settings.neural_dt_ms),
            game_dt_s=float(self.settings.game_dt_s),
        )
        if requirements.stepper_kind == "plastic":
            stepper = self._plastic_stepper(
                graph, policy, drive, plan["network"], eta=float(requirements.eta)
            )
        elif requirements.stepper_kind == "fixed":
            stepper = self._fixed_stepper(graph, policy, drive, plan["network"])
        else:  # pragma: no cover - the registry declares one of the two
            raise FactoryError(f"{arm} has no declared stepper kind")

        adapter = GameEnvironmentAdapter(environment=self.environment())
        decoder = None
        if requirements.needs_decoder:
            decoder = GameActionDecoder(self.world.populations, self.world.decoder_config)

        metadata = {
            "condition_id": arm,
            "seed": int(seed),
            "episode": int(episode),
            "environment_seed": int(environment_seed),
            "master_seed": int(master_seed),
            "network_seed": int(plan["network"]),
            "learning_seed": int(plan["learning"]),
            "structure_seed": int(plan["structure"]),
            "policy_source": (
                "certified_random_graph" if structure is not None else "biological_graph"
            ),
            "training": False,
        }

        if arm in READOUT_ARMS:
            components = self._readout_components(
                arm,
                adapter=adapter,
                stepper=stepper,
                drive=drive,
                clock=clock,
                structure=structure,
                plan=plan,
                master_seed=master_seed,
                metadata=metadata,
            )
            if structure is not None:  # pragma: no cover - no readout arm has one
                components.neural.structure = structure
        else:
            components = conditions_base.Components(
                neural=conditions_base.NeuralComponents(
                    adapter=adapter,
                    stepper=stepper,
                    drive=drive,
                    clock=clock,
                    action_decoder=decoder,
                    window_ms=float(self.settings.window_ms),
                    populations=self.world.populations,
                    structure=structure,
                    metadata=dict(metadata),
                ),
                metadata=dict(metadata),
            )
            if arm in ("B", "D"):
                hook = (
                    b_plastic.install_hook(
                        components, modulation_config=self.modulation_config
                    )
                    if arm == "B"
                    else d_plastic.install_hook(
                        components, modulation_config=self.modulation_config
                    )
                )
                components.metadata["plasticity_hook"] = type(hook).__name__
            elif arm == "A_prime":
                a_prime.install_hook(components)
            elif arm == "C_prime":
                c_prime.install_hook(components)

        conditions_base.validate_components(arm, components, declared)
        return components

    def _readout_components(
        self,
        arm: str,
        *,
        adapter: Any,
        stepper: Any,
        drive: Any,
        clock: Any,
        structure: dict | None,
        plan: Mapping[str, int],
        master_seed: int,
        metadata: dict,
    ) -> Any:
        if arm == "F":
            model = self.training.readout("F", metadata["seed"])
            self._check_readout_width(model, "F")
            components = f_readout.build_components(
                adapter=adapter,
                stepper=stepper,
                drive=drive,
                clock=clock,
                populations=self.world.populations,
                window_ms=float(self.settings.window_ms),
                training=False,
                seed=int(plan["learning"]),
                structure=structure,
                model=model,
                metadata=metadata,
            )
            f_readout.assert_state_dependent(components.neural.decision_source)
        elif arm == "F_beta":
            model = self.training.readout("F_beta", metadata["seed"])
            self._check_readout_width(model, "F_beta")
            components = f_beta.build_components(
                adapter=adapter,
                stepper=stepper,
                drive=drive,
                clock=clock,
                populations=self.world.populations,
                window_ms=float(self.settings.window_ms),
                training=False,
                seed=int(plan["learning"]),
                structure=structure,
                model=model,
                metadata=metadata,
            )
            f_beta.assert_state_independent(components.neural.decision_source)
        else:
            # F-init is the F architecture at its seeded initial parameters.
            # The seed is F's declared learning stream, not F-init's own, so
            # the parameters are the ones F would have started from.
            init_seed = int(seed_plan(master_seed, "F", metadata["seed"])["learning"])
            components = f_init.build_components(
                adapter=adapter,
                stepper=stepper,
                drive=drive,
                clock=clock,
                populations=self.world.populations,
                window_ms=float(self.settings.window_ms),
                seed=init_seed,
                structure=structure,
                metadata=metadata,
            )
            components.metadata["readout_init_seed"] = init_seed
            components.metadata["readout_init_stream"] = "learning stream of F"
        components.metadata["training"] = False
        return components

    def _check_readout_width(self, model: Any, arm: str) -> None:
        expected = MotorFeatureSpec().n_features
        actual = int(getattr(model, "n_features", -1))
        if actual != expected:
            raise FactoryError(
                f"the supplied {arm} readout expects {actual} features; the "
                f"motor interface declares {expected}"
            )

    # -- conventional components -----------------------------------------
    def conventional_components(
        self, arm: str, *, seed: int, master_seed: int = MASTER_SEED
    ) -> Any:
        if arm not in CONVENTIONAL_ARMS:
            raise FactoryError(f"{arm!r} is not a conventional arm")
        agent = self.training.agent(arm, seed)
        plan = seed_plan(master_seed, arm, seed)
        environment = self.environment()
        components = e_conventional.build_components(
            environment,
            condition_id=arm,
            seed=int(plan["learning"]),
            training=False,
            agent=agent,
            metadata={
                "condition_id": arm,
                "seed": int(seed),
                "environment_seed": int(plan["environment"]),
                "learning_seed": int(plan["learning"]),
                "training": False,
            },
        )
        e_conventional.validate(components, arm)
        return components

    # -- description -------------------------------------------------------
    def describe(self) -> dict:
        return {
            "settings": self.settings.describe(),
            "graphs": self.graphs.describe(),
            "training": self.training.describe(),
            "input_hashes_computed": self._input_hashes is not None,
            "world_loaded": self._world is not None,
            "mapping_config": SENSORY_MAPPING_PATH.as_posix(),
            "plasticity_config": PLASTICITY_PATH.as_posix(),
            "neural_arms": list(NEURAL_ARMS),
            "conventional_arms": list(CONVENTIONAL_ARMS),
            "structure_arms": list(STRUCTURE_ARMS),
        }


__all__ = [
    "CampaignFactory",
    "CONVENTIONAL_ARMS",
    "FactoryError",
    "FactorySettings",
    "NEURAL_ARMS",
    "PLASTIC_ARMS",
    "PLASTICITY_PATH",
    "READOUT_ARMS",
    "SENSORY_MAPPING_PATH",
    "STRUCTURE_ARMS",
    "TrainingArtifacts",
]
