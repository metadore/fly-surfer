"""P3-T3: leave-one-feature-out ablation around the P3-T2 full-input baseline.

The P3-T2 full experiment showed that the combined 14-feature schedule
ignites a supercritical network cascade while its player-only (C1) and
visual-only (C2) sub-schedules do not. This runner asks which individual
features matter for that ignition: for each of the 14 canonical features it
builds one condition that removes exactly that feature from the active set
and keeps the other thirteen, then compares the outcome against the
full-input baseline.

Every scientific constant is inherited from
``configs/causal_control_config.yaml`` through its validated loader; the same
cached frames, graph, mapping, seeds, initial conditions, duration and
timestep as P3-T2 are used. Feature removal is implemented exclusively by
passing ``active_features`` to ``TemporalActivationScheduler``, which masks
both the hold and the pulse drive of inactive features
(``sensory/temporal_scheduler.py``); frame data is never modified.

This is a necessity experiment. Removing a feature that changes ignition
shows that feature is necessary for the observed change under this schedule;
it does not show the feature is sufficient, and reduced recurrent activity is
not automatically better behaviour.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from experiments.phase_3c import causal_control as cc  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "configs" / "feature_ablation_config.yaml"
PHASE = "P3-T3"
BASELINE_NAME = "full-input"


def ablation_name(feature: str) -> str:
    return f"no-{feature}"


@dataclass(frozen=True)
class AblationConfig:
    """Ablation bookkeeping on top of the validated causal-control config."""

    source_path: Path
    version: str
    description: str
    causal: cc.CausalControlConfig
    removed_features: tuple[str, ...]
    output_path: Path
    subprocess_conditions: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def all_features(self) -> tuple[str, ...]:
        return self.causal.all_features

    def condition_names(self) -> list[str]:
        return [BASELINE_NAME] + [ablation_name(f) for f in self.removed_features]

    def spec_for(self, name: str) -> cc.ConditionSpec:
        if name == BASELINE_NAME:
            return cc.ConditionSpec(
                name=name,
                description=(
                    "full 14-feature input; must reproduce the archived P3-T2 "
                    "C3 reference"
                ),
                frame_source="cached",
                active_features=None,
            )
        feature = name.removeprefix("no-")
        active = tuple(f for f in self.all_features if f != feature)
        return cc.ConditionSpec(
            name=name,
            description=f"full input with {feature!r} removed; 13 features active",
            frame_source="cached",
            active_features=active,
        )

    def removed_feature_of(self, name: str) -> str | None:
        if name == BASELINE_NAME:
            return None
        return name.removeprefix("no-")

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "AblationConfig":
        raw = cc._load_yaml(path)
        version = raw.get("version")
        cc._require(
            isinstance(version, str) and bool(version),
            "version must be a non-empty string",
        )
        causal_path = PROJECT_ROOT / str(raw["causal_control_config"])
        causal = cc.CausalControlConfig.load(causal_path)
        removed = tuple(str(item) for item in raw.get("removed_features", ()))
        cc._require(
            removed == causal.all_features,
            "removed_features must list exactly the 14 canonical features "
            "in encoder order",
        )
        output_path = PROJECT_ROOT / str(raw["output"])
        subprocess = tuple(str(item) for item in raw.get("subprocess_conditions", ()))
        cc._require(
            subprocess and subprocess[0] == BASELINE_NAME,
            "subprocess_conditions must start with the baseline",
        )
        expected_names = set(cls._expected_names(causal))
        cc._require(
            set(subprocess) <= expected_names,
            "subprocess_conditions contains unknown condition names",
        )
        limitations = tuple(str(item) for item in raw.get("limitations", ()))
        return cls(
            source_path=path,
            version=str(version),
            description=str(raw.get("description", "")).strip(),
            causal=causal,
            removed_features=removed,
            output_path=output_path,
            subprocess_conditions=subprocess,
            limitations=limitations,
        )

    @staticmethod
    def _expected_names(causal: cc.CausalControlConfig) -> list[str]:
        return [BASELINE_NAME] + [ablation_name(f) for f in causal.all_features]


# --------------------------------------------------------------------------
# ablation-specific verification
# --------------------------------------------------------------------------


def pulse_window_peak_by_feature(
    scheduler, setup, *, n_steps: int, dt_ms: float
) -> dict[str, float]:
    """Max per-feature population current inside pulse windows only.

    Mirrors the window arithmetic of ``cc.audit_currents`` so hold-only steps
    are excluded; this isolates the pulse drive each feature receives.
    """
    windows = cc.pulse_windows(scheduler)
    if scheduler is None or not windows:
        return {}
    flagged = np.zeros(n_steps, dtype=bool)
    for onset_ms, offset_ms in windows:
        first = max(0, int(math.floor(onset_ms / dt_ms)))
        last = min(n_steps, int(math.ceil(offset_ms / dt_ms)))
        if last > first:
            flagged[first:last] = True
    if not flagged.any():
        return {}
    indices = cc.feature_index_map(setup)
    buffer = np.zeros(int(setup.mapping.graph.n_nodes), dtype=np.float64)
    peaks = {feature: 0.0 for feature in indices}
    for step in np.flatnonzero(flagged):
        buffer.fill(0.0)
        scheduler.apply(int(step), float(step) * dt_ms, buffer)
        for feature, feature_indices in indices.items():
            total = float(buffer[feature_indices].sum())
            if total > peaks[feature]:
                peaks[feature] = total
    return peaks


def ablation_condition_checks(
    name: str,
    item: dict,
    removed: str | None,
    cfg: AblationConfig,
    baseline_item: dict | None,
    *,
    smoke: bool,
) -> tuple[dict[str, bool | None], list[str]]:
    """Verify single-feature removal, unchanged remaining drive, fixed R."""
    checks: dict[str, bool | None] = {}
    not_evaluated: list[str] = []
    audit = item["current_audit"]
    features = tuple(cfg.all_features)
    active = item["active_features"]

    checks["scheduler_present"] = bool(item["scheduler"]["present"])
    checks["scheduler_targets_active_set"] = (
        item["scheduler"]["n_stimulated_neurons"] == item["n_active_neurons"]
    )
    checks["no_current_outside_active"] = audit["n_indices_outside_active"] == 0
    checks["current_injected"] = audit["total_injected_pa_steps"] > 0.0
    checks["reference_population_unchanged"] = (
        item["n_reference_neurons"]
        == sum(int(n) for n in cfg.causal.feature_neurons.values())
    )

    if removed is None:
        checks["all_features_active"] = item["n_active_features"] == len(features)
        checks["reference_equals_active"] = (
            item["n_active_neurons"] == item["n_reference_neurons"]
        )
    else:
        expected_active = tuple(f for f in features if f != removed)
        checks["exactly_one_feature_removed"] = (
            set(features) - set(active) == {removed}
        )
        checks["thirteen_features_active"] = (
            tuple(active) == expected_active and item["n_active_features"] == 13
        )
        checks["removed_feature_current_zero"] = (
            audit["peak_feature_current_pa"][removed] == 0.0
        )
        if audit["hold_only_steps"] > 0 and (
            audit["hold_only_pa_steps"] > 0.0 or not smoke
        ):
            checks["removed_feature_hold_zero"] = (
                audit["hold_only_peak_feature_current_pa"][removed] == 0.0
            )
        else:
            not_evaluated.append("removed_feature_hold_zero")

    if baseline_item is not None:
        checks["cache_frames_identical"] = (
            item["cache_frames_digest"] == baseline_item["cache_frames_digest"]
            and item["cache_frames_digest"] is not None
        )
        base_audit = baseline_item["current_audit"]
        if removed is not None:
            checks["active_set_is_reference_minus_removed"] = (
                item["n_active_neurons"]
                == baseline_item["n_reference_neurons"]
                - int(cfg.causal.feature_neurons[removed])
            )
            if audit["pulse_steps"] > 0:
                pulse_peaks = item["pulse_window_peak_by_feature"]
                checks["removed_feature_pulse_zero"] = pulse_peaks[removed] == 0.0
            else:
                not_evaluated.append("removed_feature_pulse_zero")
            checks["remaining_feature_drive_unchanged"] = all(
                math.isclose(
                    audit["peak_feature_current_pa"][feature],
                    base_audit["peak_feature_current_pa"][feature],
                    abs_tol=1e-6,
                )
                for feature in features
                if feature != removed
            )
        checks["mapping_unchanged"] = (
            item["initial_conditions"]["mapping_sha256"]
            == baseline_item["initial_conditions"]["mapping_sha256"]
        )
    else:
        not_evaluated.extend(
            [
                "cache_frames_identical",
                "active_set_is_reference_minus_removed",
                "removed_feature_pulse_zero",
                "remaining_feature_drive_unchanged",
                "mapping_unchanged",
            ]
        )
    checks["repeats_identical"] = bool(item["reproducibility"]["identical"])
    return checks, not_evaluated


def evaluate_ablation_invalidations(
    items: dict[str, dict],
    checks: dict[str, dict[str, bool | None]],
    cfg: AblationConfig,
    protected: dict,
    *,
    mode: str,
) -> dict:
    triggered: list[dict] = []

    def trigger(rule: str, detail) -> None:
        triggered.append({"rule": rule, "detail": detail})

    for name, item in items.items():
        if item["spike_capacity_exceeded"]:
            trigger("spike_capacity_exceeded", {"condition": name})
        diagnostics = item["simulation"]["diagnostics"]
        if not diagnostics.get("finite_state", False):
            trigger("non_finite_state", {"condition": name})
        minimum = float(cfg.causal.reference["minimum_potential_mv"])
        threshold = float(cfg.causal.reference["threshold_mv"])
        if "min_membrane_mv" in diagnostics and (
            float(diagnostics["min_membrane_mv"]) < minimum - 1e-6
        ):
            trigger("membrane_below_floor", {"condition": name})
        if "max_membrane_mv" in diagnostics and (
            float(diagnostics["max_membrane_mv"]) > threshold + 1e-6
        ):
            trigger("membrane_above_threshold", {"condition": name})
        if item["reproducibility"]["differences"]:
            trigger(
                "repeated_runs_differ",
                {"condition": name, "differences": item["reproducibility"]["differences"]},
            )
        if item["current_audit"]["n_indices_outside_active"]:
            trigger(
                "current_outside_active_set",
                {"condition": name, "n": item["current_audit"]["n_indices_outside_active"]},
            )
        failed = sorted(key for key, value in checks[name].items() if value is False)
        if failed:
            trigger(
                "condition_definition_violation",
                {"condition": name, "checks": failed},
            )

    mismatched = sorted(
        name for name, entry in protected.items() if not entry["match"]
    )
    if mismatched:
        trigger("protected_hash_changed", {"inputs": mismatched})

    signatures = {
        name: json.dumps(item["initial_conditions"], sort_keys=True)
        for name, item in items.items()
    }
    if len(set(signatures.values())) > 1:
        trigger("initial_conditions_differ", {"conditions": sorted(items)})

    digests = {
        name: item["cache_frames_digest"]
        for name, item in items.items()
        if item["cache_frames_digest"] is not None
    }
    if digests and len(set(digests.values())) > 1:
        trigger("cached_frames_differ_between_conditions", sorted(digests))

    if mode == "full" and BASELINE_NAME in items:
        baseline = items[BASELINE_NAME]
        archived = cfg.causal.archived
        if archived["scheduler_sha256"] != baseline["scheduler"]["signature_sha256"]:
            trigger(
                "baseline_scheduler_signature_mismatch",
                {
                    "expected": archived["scheduler_sha256"],
                    "actual": baseline["scheduler"]["signature_sha256"],
                },
            )
        actual = baseline["reproducibility_hashes"]["spike_counts_sha256"]
        if archived["spike_counts_sha256"] != actual:
            trigger(
                "baseline_spike_counts_mismatch",
                {"expected": archived["spike_counts_sha256"], "actual": actual},
            )

    return {
        "valid": not triggered,
        "triggered": triggered,
        "archive_gate": (
            "evaluated" if mode == "full" else "not applicable in smoke mode"
        ),
        "rules_evaluated": [
            "spike_capacity_exceeded",
            "non_finite_state",
            "membrane_bounds",
            "repeated_runs_differ",
            "current_outside_active_set",
            "condition_definition_violation",
            "protected_hash_changed",
            "initial_conditions_differ",
            "cached_frames_differ_between_conditions",
            "baseline_scheduler_signature_mismatch",
            "baseline_spike_counts_mismatch",
        ],
    }


# --------------------------------------------------------------------------
# experiment driver
# --------------------------------------------------------------------------


def ignition_summary(item: dict) -> dict:
    partitions = item["partitions"]
    outside_reference = partitions["outside_reference"]
    outside_active = partitions["outside_active"]
    return {
        "ignited": outside_reference["first_spike_ms"] is not None,
        "first_spike_ms": partitions["total"]["first_spike_ms"],
        "first_spike_outside_reference_ms": outside_reference["first_spike_ms"],
        "first_spike_outside_active_ms": outside_active["first_spike_ms"],
        "outside_reference_spikes": outside_reference["spikes"],
        "outside_reference_active_neurons": outside_reference["active_neurons"],
        "outside_reference_rate_hz": outside_reference["firing_rate_hz"],
        "population_rate_peak_hz": item["simulation"]["activity"][
            "population_rate_peak_hz"
        ],
    }


def run_ablation_experiment(
    *,
    condition_names: list[str],
    cfg: AblationConfig,
    smoke_ms: float | None = None,
    repeats: int | None = None,
    cache_path: Path | None = None,
) -> dict:
    started = time.perf_counter()
    mode = "smoke" if smoke_ms is not None else "full"
    expected = set(cfg.condition_names())
    unknown = [name for name in condition_names if name not in expected]
    if unknown:
        raise ValueError(f"unknown ablation conditions {sorted(unknown)}")

    causal = cfg.causal
    setup, neuron_params, synapse_params = cc._load_setup(causal)
    cache = cc.load_cache(causal, cache_path)
    if smoke_ms is None:
        cc.require_cache_matches_archive(causal, cache)
    duration = cc._smoke_frames_duration(causal, cache, smoke_ms)
    if smoke_ms is None:
        if not math.isclose(
            duration, float(causal.reference["duration_ms"]), abs_tol=1e-6
        ):
            raise RuntimeError(
                "cached sequence duration differs from the preregistered duration"
            )
        n_steps = int(round(duration / float(causal.reference["dt_ms"])))
        if n_steps != int(causal.reference["n_steps"]):
            raise RuntimeError("step count differs from the preregistered value")

    protected = cc.protected_hashes(causal)
    repeats = int(repeats if repeats is not None else causal.in_process_repeats)
    dt_ms = float(causal.reference["dt_ms"])

    items: dict[str, dict] = {}
    checks: dict[str, dict] = {}
    not_evaluated: dict[str, list[str]] = {}
    baseline_first = BASELINE_NAME in condition_names
    for name in condition_names:
        removed = cfg.removed_feature_of(name)
        spec = cfg.spec_for(name)
        print(
            f"  {name}: {spec.frame_source} frames, "
            f"{len(spec.active_features) if spec.active_features is not None else 14}"
            f" active features, {duration:.1f} ms, {repeats} repetition(s)",
            flush=True,
        )
        item = cc.run_condition(
            spec,
            causal,
            setup,
            neuron_params,
            synapse_params,
            cache,
            duration_ms=duration,
            smoke_ms=smoke_ms,
            repeats=repeats,
        )
        n_steps = int(round(duration / dt_ms))
        if item["scheduler"]["present"]:
            frames = cc.resolve_frames(spec, causal, cache, smoke_ms=smoke_ms)
            scheduler = cc.build_scheduler(spec, setup, frames)
            item["pulse_window_peak_by_feature"] = {
                feature: round(value, 6)
                for feature, value in pulse_window_peak_by_feature(
                    scheduler,
                    setup,
                    n_steps=n_steps,
                    dt_ms=dt_ms,
                ).items()
            }
        else:
            item["pulse_window_peak_by_feature"] = {}
        items[name] = item
        baseline_item = items.get(BASELINE_NAME) if baseline_first else None
        checks[name], not_evaluated[name] = ablation_condition_checks(
            name,
            item,
            removed,
            cfg,
            baseline_item,
            smoke=smoke_ms is not None,
        )
        item["condition_checks"] = checks[name]
        item["condition_checks_not_evaluated"] = not_evaluated[name]
        item["ignition"] = ignition_summary(item)
        item["removed_feature"] = removed

    invalidations = evaluate_ablation_invalidations(
        items, checks, cfg, protected, mode=mode
    )

    baseline = items.get(BASELINE_NAME)
    contrasts = (
        {
            "available": True,
            "contrasts": {
                f"{name}_minus_{BASELINE_NAME}": cc._contrast(
                    baseline, item, f"{name}-{BASELINE_NAME}"
                )
                for name, item in items.items()
                if name != BASELINE_NAME
            },
            "note": (
                "Whole-condition contrasts of a deterministic recurrent "
                "network; descriptive only, not additive contributions."
            ),
        }
        if baseline is not None
        else {"available": False}
    )

    generated = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    payload = {
        "phase": PHASE,
        "version": cfg.version,
        "description": cfg.description,
        "verdict": (
            (
                "SMOKE ONLY (infrastructure validation)"
                if invalidations["valid"]
                else "SMOKE INVALID"
            )
            if mode == "smoke"
            else ("VALID" if invalidations["valid"] else "INVALID")
        ),
        "mode": mode,
        "smoke_ms": smoke_ms,
        "generated_at_utc": generated,
        "runtime_s": round(time.perf_counter() - started, 3),
        "git": cc.git_state(),
        "config": {
            "path": str(cfg.source_path.relative_to(PROJECT_ROOT)),
            "sha256": cc._sha256(cfg.source_path),
            "causal_control_config_sha256": cc._sha256(
                PROJECT_ROOT / "configs" / "causal_control_config.yaml"
            ),
        },
        "ablation_registry": {
            "n_features": len(cfg.all_features),
            "features": list(cfg.all_features),
            "removed_feature_neurons": {
                feature: int(cfg.causal.feature_neurons[feature])
                for feature in cfg.removed_features
            },
        },
        "cache": (
            {
                "path": str(cache.path),
                "file_sha256": cache.file_sha256,
                "frames_digest": cache.frames_digest,
                "n_frames": len(cache.frames),
                "scheduler_signature_sha256": cache.scheduler_signature_sha256,
                "n_pulse_events": cache.n_pulse_events,
            }
            if cache is not None
            else None
        ),
        "protected_hashes": protected,
        "conditions": items,
        "contrasts_vs_baseline": contrasts,
        "invalidations": invalidations,
        "limitations": list(cfg.limitations),
        "action_selection": "none; the chain ends at sensory current injection",
    }
    return payload


def _hash_subset(payload: dict, name: str) -> dict:
    return cc._hash_subset(payload, name)


def subprocess_reproducibility(
    payload: dict,
    *,
    condition_names: list[str],
    cfg: AblationConfig,
    smoke_ms: float | None,
    cache_path: Path | None,
) -> dict:
    """Re-run selected conditions in fresh interpreters and compare hashes."""
    import tempfile

    results = {}
    for name in condition_names:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / f"{name}.json"
            command = [
                sys.executable,
                "-m",
                "experiments.phase_3c.feature_ablation",
                "--condition",
                name,
                "--once",
                "--output",
                str(output),
            ]
            if smoke_ms is not None:
                command += ["--smoke-ms", str(smoke_ms)]
            if cache_path is not None:
                command += ["--cache", str(cache_path)]
            import subprocess as sp

            completed = sp.run(
                command,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                results[name] = {
                    "ran": False,
                    "returncode": completed.returncode,
                    "stderr_tail": completed.stderr[-2000:],
                }
                continue
            child = json.loads(output.read_text(encoding="utf-8"))
            parent_hashes = _hash_subset(payload, name)
            child_hashes = _hash_subset(child, name)
            differences = sorted(
                key
                for key in parent_hashes
                if json.dumps(parent_hashes[key], sort_keys=True)
                != json.dumps(child_hashes[key], sort_keys=True)
            )
            results[name] = {
                "ran": True,
                "identical": not differences,
                "differences": differences,
                "hashes": child_hashes,
            }
    return {
        "conditions": results,
        "identical": all(
            item.get("ran") and item.get("identical")
            for item in results.values()
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "P3-T3: leave-one-feature-out ablation around the P3-T2 "
            "full-input baseline. One run per condition; two in-process "
            "repeats by default; baseline checked against the archived "
            "P3-T2 C3 reference in full mode."
        )
    )
    parser.add_argument("--condition", action="append", default=[] )
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--smoke-ms", type=float, default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reproduce-subprocess", action="store_true")
    args = parser.parse_args(argv)

    cfg = AblationConfig.load()
    names: list[str]
    if args.all:
        names = cfg.condition_names()
    elif args.condition:
        names = []
        for name in args.condition:
            if name not in cfg.condition_names():
                parser.error(f"unknown condition {name!r}")
            if name not in names:
                names.append(name)
    else:
        parser.error("pass --all or at least one --condition")

    repeats = 1 if args.once else None
    payload = run_ablation_experiment(
        condition_names=names,
        cfg=cfg,
        smoke_ms=args.smoke_ms,
        repeats=repeats,
        cache_path=Path(args.cache) if args.cache else None,
    )
    if args.reproduce_subprocess:
        selected = [
            name
            for name in cfg.subprocess_conditions
            if name in names
        ]
        payload["subprocess_reproducibility"] = subprocess_reproducibility(
            payload,
            condition_names=selected,
            cfg=cfg,
            smoke_ms=args.smoke_ms,
            cache_path=Path(args.cache) if args.cache else None,
        )
        if not payload["subprocess_reproducibility"]["identical"]:
            payload["invalidations"]["valid"] = False
            payload["invalidations"]["triggered"].append(
                {"rule": "subprocess_runs_differ", "detail": "see subprocess_reproducibility"}
            )
            payload["verdict"] = (
                "SMOKE INVALID" if payload["mode"] == "smoke" else "INVALID"
            )
    output = Path(args.output) if args.output else cfg.output_path
    cc.write_outputs(payload, output, overwrite=args.overwrite)
    print(
        f"wrote {output} | verdict={payload['verdict']} | "
        f"conditions={names} | "
        f"invalidations={len(payload['invalidations']['triggered'])}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
