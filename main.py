"""Command-line entry point for the FLY-SURFER simulation layer.

Runs the reproducible Phase 2 experiment. Arguments are forwarded to
``experiments.baseline`` (use ``--help`` for the full list).
"""

from __future__ import annotations

from experiments.baseline import main as run_experiment


def main(argv: list[str] | None = None) -> int:
    return run_experiment(argv)


if __name__ == "__main__":
    raise SystemExit(main())
