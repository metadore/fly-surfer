"""Open-loop replay of recorded Phase 4 motor outputs.

The Phase 4 decoder produced these records from BANC activity in a separate
experiment. This agent cycles them unchanged so the Phase 7 game integration
can be exercised with real decoder records. It is an integration demonstration,
not a controller: it does not observe the game.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = (
    PROJECT_ROOT / "experiments" / "results" / "phase_4" / "motor_output_demo.json"
)


def load_phase4_outputs(path: str | Path | None = None) -> list[dict]:
    source = Path(path) if path is not None else DEFAULT_ARTIFACT
    data = json.loads(source.read_text(encoding="utf-8"))
    probe = data.get("conditions", {}).get("probe")
    if not isinstance(probe, dict):
        raise ValueError(f"{source} has no conditions.probe record")
    outputs = probe.get("decoder_outputs")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError(f"{source} has no decoder outputs")
    records = [dict(record) for record in outputs]
    requested = probe.get("requested_channels", {})
    if not isinstance(requested, dict):
        raise ValueError(f"{source} has malformed requested channels")
    for channel, record in requested.items():
        item = dict(record)
        item["requested_channel"] = channel
        records.append(item)
    return records


class Phase4MotorAgent:
    """Cycle recorded Phase 4 outputs in their recorded order."""

    def __init__(self, outputs: list[dict], *, start: int = 0) -> None:
        if not outputs:
            raise ValueError("outputs must not be empty")
        if not 0 <= start < len(outputs):
            raise ValueError("start index is outside the output list")
        self.outputs = outputs
        self.index = start
        self.n_calls = 0

    def act(self, observation):
        del observation
        record = self.outputs[self.index]
        self.index = (self.index + 1) % len(self.outputs)
        self.n_calls += 1
        return record

    def describe(self) -> dict:
        states = [str(record.get("state")) for record in self.outputs]
        return {
            "agent": "phase4_motor_output_replay",
            "n_records": len(self.outputs),
            "states": states,
            "note": (
                "recorded Phase 4 decoder outputs are replayed open loop; the "
                "agent does not observe the game"
            ),
        }
