"""P3-T12 preflight: measured overhead, capacity and go/no-go record.

Consumes the 600 ms smoke artifact produced by
``python -m experiments.phase_3c.network_characterization --all --smoke-ms 600
--reproduce-subprocess`` and measures the only quantity the smoke payload
cannot supply: the wall-time cost of the instrumented stepper relative to the
unmodified ``causal_control.run_once`` path on the identical 600 ms C3 window.

The preflight never extrapolates short-run spike counts linearly. It records
the archived full-duration C3 count next to the measured smoke counts and
leaves the full-run capacity question to the recorder overflow rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from experiments.phase_3c import causal_control as cc
from experiments.phase_3c import network_characterization as nc

PHASE = "P3-T12-preflight"
VERSION = "p3-t12-preflight-v1"
DEFAULT_SMOKE = PROJECT_ROOT / "experiments/phase_3c/results/p3_t12_smoke.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments/phase_3c/results/p3_t12_preflight.json"
PROTOCOL = PROJECT_ROOT / "docs/P3_T12_NETWORK_CHARACTERIZATION_PROTOCOL.md"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def measure_uninstrumented_c3(smoke_ms: float) -> dict:
    cfg = nc.CharacterizationConfig.load()
    causal = cfg.causal
    setup, neuron_params, synapse_params = cc._load_setup(causal)
    cache = cc.load_cache(causal, None)
    spec = cfg.spec_for("C3")
    duration = cfg.duration_for("C3", smoke_ms=smoke_ms)
    item = cc.run_once(
        spec,
        causal,
        setup,
        neuron_params,
        synapse_params,
        cache,
        duration_ms=duration,
        smoke_ms=smoke_ms,
    )
    return {
        "condition": "C3",
        "duration_ms": float(duration),
        "step_loop_s": item["simulation"]["wall_runtime_s"],
        "spikes_total": item["simulation"]["spikes_total"],
        "spike_counts_sha256": item["reproducibility_hashes"]["spike_counts_sha256"],
        "scheduler_signature_sha256": item["reproducibility_hashes"][
            "scheduler_signature_sha256"
        ],
    }


def build_preflight(smoke_path: Path, smoke_ms: float) -> dict:
    payload = json.loads(smoke_path.read_text(encoding="utf-8"))
    conditions = payload["conditions"]
    cfg = nc.CharacterizationConfig.load()
    capacity = int(next(iter(conditions.values()))["spike_capacity"])

    baseline = measure_uninstrumented_c3(smoke_ms)
    c3 = conditions["C3"]
    instrumented = c3["simulation"]
    matches = (
        baseline["spike_counts_sha256"]
        == c3["reproducibility_hashes"]["spike_counts_sha256"]
        and baseline["spikes_total"] == instrumented["spikes_total"]
    )
    overhead = (
        instrumented["wall_runtime_s"] / baseline["step_loop_s"] - 1.0
    )

    archived_path = PROJECT_ROOT / "experiments/phase_3c/results/p3_t2_full.json"
    archived = None
    if archived_path.exists():
        archived_payload = json.loads(archived_path.read_text(encoding="utf-8"))
        archived_item = archived_payload["conditions"]["C3"]
        archived = {
            "duration_ms": archived_item["simulation"]["duration_ms"],
            "spikes_total": archived_item["simulation"]["spikes_total"],
            "spike_counts_sha256": archived_item["reproducibility_hashes"][
                "spike_counts_sha256"
            ],
            "fraction_of_capacity": round(
                archived_item["simulation"]["spikes_total"] / capacity, 6
            ),
        }

    per_condition = {}
    for name, item in conditions.items():
        simulation = item["simulation"]
        per_condition[name] = {
            "duration_ms": item["duration_ms"],
            "spikes_total": simulation["spikes_total"],
            "fraction_of_capacity": round(
                simulation["spikes_total"] / capacity, 6
            ),
            "wall_runtime_s": simulation["wall_runtime_s"],
            "steps_per_second_wall": simulation["steps_per_second_wall"],
            "rss_after_mb": simulation["rss_after_mb"],
            "repeats_identical": item["reproducibility"]["identical"],
            "spike_capacity_exceeded": item["spike_capacity_exceeded"],
        }

    failures = []
    if payload["mode"] != "smoke":
        failures.append("source artifact is not a smoke run")
    if not payload["invalidations"]["valid"]:
        failures.append("smoke invalidations triggered")
    if sorted(conditions) != sorted(cfg.conditions):
        failures.append("smoke does not cover exactly the configured conditions")
    if not all(entry["repeats_identical"] for entry in per_condition.values()):
        failures.append("in-process repeats differ")
    subprocess = payload.get("subprocess_reproducibility") or {}
    if not subprocess.get("identical"):
        failures.append("subprocess reproducibility failed or missing")
    if not (payload.get("prefix_gate") or {}).get("passed"):
        failures.append("washout prefix gate failed or missing")
    if not matches:
        failures.append("instrumented and uninstrumented C3 differ at 600 ms")
    if not (payload.get("equivalence") or {}).get("smoke", {}).get("evaluated") is False:
        failures.append("smoke equivalence status is not recorded as not applicable")
    if overhead > 0.5:
        failures.append("instrumentation overhead above 50 percent")

    return {
        "phase": PHASE,
        "version": VERSION,
        "mode": "preflight",
        "verdict": "READY" if not failures else "NOT READY",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "smoke_artifact": {
            "path": str(smoke_path.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(smoke_path),
            "size_bytes": smoke_path.stat().st_size,
            "runtime_s": payload["runtime_s"],
            "verdict": payload["verdict"],
        },
        "protocol": {
            "path": str(PROTOCOL.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(PROTOCOL),
        },
        "config": {
            "path": str(cfg.source_path.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(cfg.source_path),
            "conditions": list(cfg.conditions),
            "repeats": cfg.repeats,
        },
        "smoke_ms": float(smoke_ms),
        "instrumentation_overhead": {
            "definition": "instrumented step loop divided by unmodified run_once step loop, same 600 ms C3 schedule",
            "uninstrumented": baseline,
            "instrumented_step_loop_s": instrumented["wall_runtime_s"],
            "overhead_fraction": round(overhead, 4),
            "spike_counts_identical": matches,
        },
        "capacity": {
            "recorder_capacity": capacity,
            "capacity_bytes": capacity * 8,
            "archived_full_c3": archived,
            "note": (
                "Smoke counts are not extrapolated. The archived full-duration "
                "C3 count is the only measured full-window value; overflow in "
                "the washout is an INVALID result, not a reason to raise the "
                "recorded-spike budget."
            ),
        },
        "conditions": per_condition,
        "gates": {
            "smoke_invalidations": payload["invalidations"],
            "prefix_gate": payload.get("prefix_gate"),
            "equivalence": payload.get("equivalence"),
            "subprocess_reproducibility": subprocess,
            "condition_checks": {
                name: {
                    "passed": item["condition_checks"],
                    "not_evaluated": item["condition_checks_not_evaluated"],
                }
                for name, item in conditions.items()
            },
        },
        "failures": failures,
        "ready_for_full_run": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P3-T12 measured preflight")
    parser.add_argument("--smoke", default=str(DEFAULT_SMOKE))
    parser.add_argument("--smoke-ms", type=float, default=600.0)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    smoke_path = Path(args.smoke)
    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise SystemExit(f"{output} exists; pass --overwrite")

    payload = build_preflight(smoke_path, args.smoke_ms)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    sidecar = output.with_name(output.stem + ".sidecar.json")
    if sidecar.exists() and not args.overwrite:
        raise SystemExit(f"{sidecar} exists; pass --overwrite")
    sidecar.write_text(
        json.dumps(
            {
                "output": output.name,
                "phase": payload["phase"],
                "version": payload["version"],
                "mode": payload["mode"],
                "verdict": payload["verdict"],
                "generated_at_utc": payload["generated_at_utc"],
                "smoke_sha256": payload["smoke_artifact"]["sha256"],
                "config_sha256": payload["config"]["sha256"],
                "protocol_sha256": payload["protocol"]["sha256"],
                "ready_for_full_run": payload["ready_for_full_run"],
                "failures": payload["failures"],
            },
            indent=1,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    print(
        f"wrote {output} | ready={payload['ready_for_full_run']} | "
        f"overhead={payload['instrumentation_overhead']['overhead_fraction']:.1%} | "
        f"failures={payload['failures']}"
    )
    return 0 if payload["ready_for_full_run"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
