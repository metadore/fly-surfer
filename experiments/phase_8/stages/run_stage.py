"""Single entry point for the Phase 8 stage harnesses (REV4 §10).

Each stage module owns its own argparse parser and refusal logic; this module
only routes. It adds no behaviour, no default and no gate of its own: the
selected stage keeps the first word on whether it may run.

Usage
    python -m experiments.phase_8.stages.run_stage --list
    python -m experiments.phase_8.stages.run_stage pilot1  --describe
    python -m experiments.phase_8.stages.run_stage training --status
    python -m experiments.phase_8.stages.run_stage campaign --describe
    python -m experiments.phase_8.stages.run_stage pilot2  --describe
    python -m experiments.phase_8.stages.run_stage information --describe
    python -m experiments.phase_8.stages.run_stage report  --describe

Exit codes: 0 the stage completed read-only work; 1 incomplete (missing input or
configuration); 2 refused (an authorisation or readiness gate stopped it).
"""

from __future__ import annotations

import sys

STAGES = {
    "pilot1": "stages.pilot1",
    "training": "stages.training_stage",
    "campaign": "stages.composition",
    "pilot2": "stages.pilot2",
    "information": "stages.information",
    "report": "stages.reporting",
}

EXIT_USAGE = 2


def _help_text() -> str:
    lines = [
        "Phase 8 stage harnesses (REV4 §10). Nothing here executes experimental work.",
        "",
        "stages:",
    ]
    lines.extend(f"  {name}" for name in STAGES)
    lines.extend(
        [
            "",
            "run `<stage> --help` for the options of one stage; every execute path",
            "calls the existing refusal gate first.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in ("-h", "--help", "--list"):
        sys.stdout.write(_help_text())
        return 0 if arguments else EXIT_USAGE

    name = arguments[0]
    module_name = STAGES.get(name)
    if module_name is None:
        sys.stderr.write(
            f"unknown stage {name!r}; choose one of {sorted(STAGES)}\n"
        )
        return EXIT_USAGE

    package = __package__ or "experiments.phase_8.stages"
    module = __import__(f"{package}.{module_name.rsplit('.', 1)[-1]}", fromlist=["main"])
    return int(module.main(arguments[1:]))


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["STAGES", "main"]
