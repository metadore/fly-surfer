"""Analyse a Phase 8 campaign store (G6, REV3 §10.11).

Usage::

    python -m experiments.phase_8.analyse_phase_8 \
        --store experiments/results/phase_8/episodes.jsonl \
        --family-size 4 --n-seeds 16

The command is read-only with respect to the episode store and refuses to
overwrite an existing analysis file unless ``--overwrite`` is supplied. Every
number in the output is computed from the rows and the declared configuration;
nothing is typed by hand. ``--family-size`` and ``--n-seeds`` are required
because they are recorded decisions (U14, U7), not analysis defaults.

The analysis is lightweight: it reads JSONL and enumerates sign vectors. It
does not run a campaign, training or BANC-scale computation, so the §9.3 memory
gate does not apply to it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import AnalysisError, analyse_campaign
from .config import ConfigError, PROJECT_ROOT, load_phase8_config
from .store import StoreError, read_store


def _default_store(config) -> Path:
    return (
        PROJECT_ROOT
        / config.campaign.results_root
        / config.campaign.episode_store_name
    )


def _write_json(path: Path, payload: dict, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    except FileExistsError:
        raise AnalysisError(
            f"analysis output already exists: {path}; nothing is overwritten "
            "unless --overwrite is supplied"
        ) from None


def _format_p(entry: dict | None) -> str:
    if not isinstance(entry, dict) or "value" not in entry:
        return "n/a"
    return f"{entry['value']:.6g} ({entry['exact']})"


def _summary_text(result: dict) -> str:
    lines = [
        f"Phase 8 analysis (protocol {result['protocol']})",
        f"rows={result['rows']}  planned N={result['n_seeds_planned']}  "
        f"analysed N={result['n_seeds_analysed']}  "
        f"family m={result['family_size']}  primary={result['primary_status']}",
    ]
    confirmatory = result["confirmatory"]
    for contrast_id, block in confirmatory["contrasts"].items():
        if block.get("status") == "design_failure":
            lines.append(f"{contrast_id}: NOT COMPUTED - {block.get('reason')}")
            continue
        flip = block.get("sign_flip", {})
        texts = block.get("sign_test", {})
        lines.append(
            f"{contrast_id} {block['minuend']}-{block['subtrahend']}: "
            f"n={block.get('seeds_paired')} "
            f"mean={block.get('effect_sizes', {}).get('mean_difference')} "
            f"sign-flip p={_format_p(flip.get('p_value'))} "
            f"sign-test p={_format_p(texts.get('p_value'))} "
            f"holm={block.get('holm_rejected')}"
        )
    for name, report in result["identity"].items():
        lines.append(
            f"identity {report['control']} vs {report['target']}: "
            f"{report['status']} ({report['pairs_compared']}/"
            f"{report['pairs_planned']})"
        )
    checks = result["readout"]["checklist"]["checks"]
    lines.append(
        "E1-E5: "
        + "  ".join(f"{key}={value['status']}" for key, value in checks.items())
    )
    if result["warnings"]:
        lines.append("warnings:")
        lines.extend(f"  - {warning}" for warning in result["warnings"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse the Phase 8 append-only episode store (REV3 §7)."
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="episodes.jsonl (default: the path declared in campaign.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="analysis JSON path (default: analysis.json beside the store)",
    )
    parser.add_argument(
        "--family-size",
        type=int,
        choices=(4, 3),
        required=True,
        help="Holm family size (U14): 4 for C1-C4, 3 for C1-C3",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        required=True,
        help="the declared design N actually run (10 or 16, REV3 U7)",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=60.0,
        help="assumed sigma_max in updates for the MDE table (REV3 §7.4)",
    )
    parser.add_argument(
        "--replay-store",
        type=Path,
        default=None,
        help="a fresh-process replay store for the E5 comparison",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing analysis file (refused by default)",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_phase8_config()
        store = args.store or _default_store(config)
        output = args.output or (Path(store).parent / "analysis.json")
        rows = read_store(store)
        replay_rows = (
            read_store(args.replay_store) if args.replay_store is not None else None
        )
        result = analyse_campaign(
            rows,
            config,
            family_size=int(args.family_size),
            n_seeds=int(args.n_seeds),
            sigma=float(args.sigma),
            replay_rows=replay_rows,
        )
        _write_json(Path(output), result, overwrite=bool(args.overwrite))
    except (AnalysisError, ConfigError, StoreError) as error:
        print(f"analysis refused: {error}", file=sys.stderr)
        return 2
    print(_summary_text(result))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["build_parser", "main"]
