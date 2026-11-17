"""P1–P19 exact comparison for the A′/C′ internal-validity controls.

SCIENTIFIC STATUS
    A′ and C′ assert an identity, not a similarity: the plastic code path at
    ``eta = 0`` must reproduce the fixed-weight arm exactly. There is no
    tolerance (REV4 §3.8.4). The comparison here is a correctness check of an
    implementation, not a measurement of a fly, and a passing comparison is
    not evidence that plasticity improves behaviour.

The first unequal field stops the comparison and raises
:class:`EquivalenceMismatch` carrying the field id, the seed, the episode and
both values (or their content hashes). The caller must then follow the hard
stop of §3.8.5: retain the artefacts, mark B or D INVALID, and never retry
with another seed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

#: Field ids and the requirement each encodes (REV4 §3.8.3).
COMPARISON_FIELDS: dict[str, str] = {
    "P1": "spike times (exact array equality)",
    "P2": "spike neuron indices (exact array equality)",
    "P3": "spike_sha256",
    "P4": "action_reward_sha256",
    "P5": "full record sequence (canonical JSON)",
    "P6": "survival and termination summary",
    "P7": "action and decoder-state counts",
    "P8": "reward total and every component",
    "P9": "neural_steps, neural_time_ms, game_time_ms",
    "P10": "motor_activity per decision",
    "P11": "structural weight digest",
    "P12": "initial weight digest",
    "P13": "learned-delta digest and exact zero delta",
    "P14": "effective weight digest equals the initial digest",
    "P15": "max |Δw| exactly 0.0",
    "P16": "changed edges exactly 0",
    "P17": "clamp hits and saturation count exactly 0",
    "P18": "stepper weight fingerprint equal before and after",
    "P19": "resets during the episode",
}

FIELD_ORDER = tuple(COMPARISON_FIELDS)


class EquivalenceMismatch(RuntimeError):
    """The plastic path at eta = 0 is not an identity. Hard stop."""

    def __init__(self, payload: dict) -> None:
        super().__init__(
            f"{payload['control_id']} mismatch at {payload['field_id']} "
            f"(seed {payload['seed']}, episode {payload['episode']})"
        )
        self.payload = payload


def _summary(result: dict) -> dict:
    return result["summary"]


def _evidence(result: dict) -> dict:
    return dict(result["row"].get("evidence") or {})


def _records(result: dict) -> list:
    return result["records"]


def _recorder(result: dict) -> Any:
    return result["stepper"].recorder


def _state(result: dict) -> Any:
    return getattr(result["stepper"], "weight_state", None)


def _json_text(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    )


def _describe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        contiguous = np.ascontiguousarray(value)
        return {
            "type": "ndarray",
            "dtype": str(contiguous.dtype),
            "shape": list(contiguous.shape),
            "sha256": hashlib.sha256(contiguous.tobytes()).hexdigest(),
        }
    text = _json_text(value)
    if len(text) > 512:
        return {
            "type": "json",
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "length": len(text),
        }
    return {"type": "json", "value": json.loads(text)}


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        return (
            isinstance(left, np.ndarray)
            and isinstance(right, np.ndarray)
            and left.shape == right.shape
            and left.dtype == right.dtype
            and bool(np.array_equal(left, right))
        )
    return _json_text(left) == _json_text(right)


def _hashes(result: dict) -> dict:
    summary = _summary(result)
    return {
        "fingerprint": dict(result.get("fingerprint") or {}),
        "weights_before": summary.get("weights_before"),
        "weights_after": summary.get("weights_after"),
        "evidence": {
            key: _evidence(result).get(key)
            for key in (
                "structure_digest",
                "initial_digest",
                "delta_digest",
                "effective_digest",
            )
        },
    }


def _plastic_state(result: dict) -> Any:
    state = _state(result)
    if state is None:
        raise EquivalenceMismatch(
            {
                "control_id": result.get("condition"),
                "field_id": "P11",
                "field": COMPARISON_FIELDS["P11"],
                "seed": result["row"]["seed"],
                "episode": result["row"]["episode"],
                "reason": "the control has no WeightState; A′/C′ must run the "
                "plastic pathway, not the fixed path",
                "required_action": "hard stop (REV4 §3.8.5)",
            }
        )
    return state


# -- individual comparison functions ---------------------------------------


def _p11(fixed: dict, control: dict) -> tuple[Any, Any]:
    state = _plastic_state(control)
    after = state.structural_digest()
    before = _evidence(control).get("structure_digest")
    fixed_digest = _evidence(fixed).get("structure_digest")
    return (fixed_digest if fixed_digest is not None else before), after


def _p12(fixed: dict, control: dict) -> tuple[Any, Any]:
    state = _plastic_state(control)
    after = state.initial_digest()
    before = _evidence(control).get("initial_digest")
    fixed_digest = _evidence(fixed).get("initial_digest")
    return (fixed_digest if fixed_digest is not None else before), after


def _p13(fixed: dict, control: dict) -> tuple[Any, Any]:
    state = _plastic_state(control)
    digest = state.delta_digest()
    all_zero = bool(
        np.all(state.delta_exc == 0.0) and np.all(state.delta_inh == 0.0)
    )
    fixed_digest = _evidence(fixed).get("delta_digest")
    expected = fixed_digest if fixed_digest is not None else digest
    return [expected, True], [digest, all_zero]


def _p14(fixed: dict, control: dict) -> tuple[Any, Any]:
    # Layer digests include the layer name by construction, so the control's
    # effective digest can never equal its initial digest string. REV4 §3.8.3
    # P14 asks for the effective *values* to equal the initial values; the
    # array comparison below is that check, with no tolerance.
    state = _plastic_state(control)
    effective = state.effective_digest()
    matches_initial = bool(
        np.array_equal(state.effective_exc, state.initial_exc)
        and np.array_equal(state.effective_inh, state.initial_inh)
    )
    fixed_digest = _evidence(fixed).get("effective_digest")
    expected = fixed_digest if fixed_digest is not None else effective
    return [expected, True], [effective, matches_initial]


def _p15(fixed: dict, control: dict) -> tuple[Any, Any]:
    state = _plastic_state(control)
    return 0.0, float(state.describe()["delta_max_abs_pa"])


def _p16(fixed: dict, control: dict) -> tuple[Any, Any]:
    state = _plastic_state(control)
    return 0, int(state.describe()["n_changed_edges"])


def _p17(fixed: dict, control: dict) -> tuple[Any, Any]:
    state = _plastic_state(control)
    saturated = int(state.describe()["saturated_edges"])
    plasticity = _summary(control).get("plasticity") or {}
    clamps = int(plasticity.get("clamp_hits", 0)) + int(
        plasticity.get("update_clip_hits", 0)
    )
    return [0, 0], [saturated, clamps]


def _p18(fixed: dict, control: dict) -> tuple[Any, Any]:
    return (
        [
            _summary(fixed)["weights_before"]["sha256"],
            _summary(fixed)["weights_after"]["sha256"],
        ],
        [
            _summary(control)["weights_before"]["sha256"],
            _summary(control)["weights_after"]["sha256"],
        ],
    )


def _p19(fixed: dict, control: dict) -> tuple[Any, Any]:
    return (
        int(_summary(fixed)["neural_resets_during_episode"]),
        int(_summary(control)["neural_resets_during_episode"]),
    )


#: Each entry returns ``(fixed_value, control_value)``. All must be equal.
CHECKS: tuple[tuple[str, Callable[[dict, dict], tuple[Any, Any]]], ...] = (
    (
        "P1",
        lambda f, c: (
            np.asarray(_recorder(f).spike_times_ms),
            np.asarray(_recorder(c).spike_times_ms),
        ),
    ),
    (
        "P2",
        lambda f, c: (
            np.asarray(_recorder(f).spike_neuron_indices),
            np.asarray(_recorder(c).spike_neuron_indices),
        ),
    ),
    (
        "P3",
        lambda f, c: (
            f["fingerprint"]["spike_sha256"],
            c["fingerprint"]["spike_sha256"],
        ),
    ),
    (
        "P4",
        lambda f, c: (
            f["fingerprint"]["action_reward_sha256"],
            c["fingerprint"]["action_reward_sha256"],
        ),
    ),
    ("P5", lambda f, c: (_json_text(_records(f)), _json_text(_records(c)))),
    (
        "P6",
        lambda f, c: (
            [
                _summary(f)["updates"],
                _summary(f)["terminated"],
                _summary(f)["truncated"],
                _summary(f)["termination_reason"],
            ],
            [
                _summary(c)["updates"],
                _summary(c)["terminated"],
                _summary(c)["truncated"],
                _summary(c)["termination_reason"],
            ],
        ),
    ),
    (
        "P7",
        lambda f, c: (
            [_summary(f)["action_counts"], _summary(f)["decoder_state_counts"]],
            [_summary(c)["action_counts"], _summary(c)["decoder_state_counts"]],
        ),
    ),
    (
        "P8",
        lambda f, c: (
            [
                _summary(f)["total_reward"],
                _summary(f)["reward_component_totals"],
            ],
            [
                _summary(c)["total_reward"],
                _summary(c)["reward_component_totals"],
            ],
        ),
    ),
    (
        "P9",
        lambda f, c: (
            [
                _summary(f)["neural_steps"],
                _summary(f)["neural_time_ms"],
                _summary(f)["game_time_ms"],
            ],
            [
                _summary(c)["neural_steps"],
                _summary(c)["neural_time_ms"],
                _summary(c)["game_time_ms"],
            ],
        ),
    ),
    (
        "P10",
        lambda f, c: (
            [record.get("motor_activity") for record in _records(f)],
            [record.get("motor_activity") for record in _records(c)],
        ),
    ),
    ("P11", _p11),
    ("P12", _p12),
    ("P13", _p13),
    ("P14", _p14),
    ("P15", _p15),
    ("P16", _p16),
    ("P17", _p17),
    ("P18", _p18),
    ("P19", _p19),
)


def _check_identity(
    fixed: dict, control: dict, *, control_id: str
) -> tuple[int, int, int]:
    if fixed.get("condition") != {
        "A_prime": "A",
        "C_prime": "C",
    }[control_id]:
        raise ValueError(
            f"{control_id} must be compared with its declared mirror; got "
            f"{fixed.get('condition')!r}"
        )
    fixed_row = fixed["row"]
    control_row = control["row"]
    for key in ("seed", "episode", "environment_seed"):
        if int(fixed_row[key]) != int(control_row[key]):
            raise ValueError(
                f"{control_id} and {fixed_row['condition']} are not the same "
                f"{key}: {fixed_row[key]} vs {control_row[key]}"
            )
    return (
        int(control_row["seed"]),
        int(control_row["episode"]),
        int(control_row["environment_seed"]),
    )


def compare_runs(
    fixed: dict,
    control: dict,
    *,
    control_id: str,
    stop_at_first: bool = True,
) -> dict:
    """Compare a control run against its fixed-weight mirror.

    Returns a report when every field is equal. Raises
    :class:`EquivalenceMismatch` on the first unequal field; there is no
    tolerance and no retry.
    """
    if control_id not in ("A_prime", "C_prime"):
        raise ValueError("control_id must be 'A_prime' or 'C_prime'")
    seed, episode, environment_seed = _check_identity(
        fixed, control, control_id=control_id
    )
    checked: list[str] = []
    for field_id, check in CHECKS:
        fixed_value, control_value = check(fixed, control)
        checked.append(field_id)
        if _equal(fixed_value, control_value):
            continue
        payload = {
            "kind": f"{control_id.lower()}_mismatch",
            "control_id": control_id,
            "seed": seed,
            "episode": episode,
            "environment_seed": environment_seed,
            "field_id": field_id,
            "field": COMPARISON_FIELDS[field_id],
            "fields_checked_before_stop": checked[:-1],
            "fixed": _describe(fixed_value),
            "control": _describe(control_value),
            "fixed_hashes": _hashes(fixed),
            "control_hashes": _hashes(control),
            "tolerance": "none (REV4 §3.8.4)",
            "required_action": (
                "hard stop: retain artefacts, mark B/D INVALID and do not "
                "retry with another seed (REV4 §3.8.5)"
            ),
        }
        raise EquivalenceMismatch(payload)
    report = {
        "control_id": control_id,
        "mirror": fixed["condition"],
        "seed": seed,
        "episode": episode,
        "environment_seed": environment_seed,
        "fields": checked,
        "field_count": len(checked),
        "all_equal": True,
        "tolerance": "none",
        "protocol": "REV4 §3.8.3–§3.8.4",
    }
    if control_id == "A_prime":
        report["invalidates_on_mismatch"] = ["B"]
    else:
        report["invalidates_on_mismatch"] = ["D"]
    return report


def check_control_invariants(control: dict, *, control_id: str) -> dict:
    """Verify the eta=0 pathway executed and reported itself honestly."""
    if control_id not in ("A_prime", "C_prime"):
        raise ValueError("control_id must be 'A_prime' or 'C_prime'")
    summary = _summary(control)
    plasticity = summary.get("plasticity")
    if not isinstance(plasticity, dict):
        raise EquivalenceMismatch(
            {
                "kind": f"{control_id.lower()}_mismatch",
                "control_id": control_id,
                "field_id": "ETA0_PATHWAY",
                "field": "plastic pathway executed and reported",
                "seed": control["row"]["seed"],
                "episode": control["row"]["episode"],
                "reason": "the episode summary has no plasticity block; the "
                "control did not run the plastic pathway",
                "required_action": "hard stop (REV4 §3.8.5)",
            }
        )
    mode = plasticity.get("pathway")
    eta = float(plasticity.get("eta", float("nan")))
    evidence_mode = _evidence(control).get("plasticity_path", {}).get("mode")
    if eta != 0.0:
        raise EquivalenceMismatch(
            {
                "kind": f"{control_id.lower()}_mismatch",
                "control_id": control_id,
                "field_id": "ETA0_VALUE",
                "field": "eta exactly 0.0",
                "seed": control["row"]["seed"],
                "episode": control["row"]["episode"],
                "control": eta,
                "required_action": "hard stop (REV4 §3.8.5)",
            }
        )
    if evidence_mode not in ("rule_executed_zero_delta", "short_circuited"):
        raise EquivalenceMismatch(
            {
                "kind": f"{control_id.lower()}_mismatch",
                "control_id": control_id,
                "field_id": "ETA0_MODE",
                "field": "plasticity_path.mode",
                "seed": control["row"]["seed"],
                "episode": control["row"]["episode"],
                "control": evidence_mode,
                "required_action": "hard stop (REV4 §3.8.5)",
            }
        )
    return {
        "control_id": control_id,
        "pathway": mode,
        "eta": eta,
        "mode": evidence_mode,
        "n_update_reports": int(plasticity.get("n_update_reports", 0)),
        "zero_delta": (
            float(plasticity.get("max_abs_applied_pa", 0.0)) == 0.0
            and int(plasticity.get("n_changed_edges", 0)) == 0
        ),
    }


__all__ = [
    "CHECKS",
    "COMPARISON_FIELDS",
    "EquivalenceMismatch",
    "FIELD_ORDER",
    "check_control_invariants",
    "compare_runs",
]
