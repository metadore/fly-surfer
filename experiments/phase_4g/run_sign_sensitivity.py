"""Phase 4G.5 addendum — sign sensitivity of the C candidate condition.

Flips the transmitter sign prior of the 64 stimulated VNC intrinsic candidates
from verified excitatory to verified inhibitory and repeats the identical
simulation and decoder call. All other neurons, edges, weights and decoder
parameters stay unchanged. This answers whether the decoded result depends on
the excitatory sign assumption.

Output: ``experiments/results/phase_4g/phase_4g_sign_sensitivity.json``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODULE_PATH = Path(__file__).with_name("run_phase_4g_experiments.py")
spec = importlib.util.spec_from_file_location("phase_4g5_runner", MODULE_PATH)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)

from brain.banc_synapse_policy import (  # noqa: E402
    SignPolicy,
    VERIFIED_INHIBITORY,
    WeightPolicy,
    build_synapse_policy,
)
from motor.motor_decoder import DecoderConfig  # noqa: E402
from motor.populations import PopulationOptions, build_populations  # noqa: E402

OUTPUT = PROJECT_ROOT / "experiments" / "results" / "phase_4g" / "phase_4g_sign_sensitivity.json"
PRIMARY_RESULT = PROJECT_ROOT / "experiments" / "results" / "phase_4g" / "phase_4g_experiment.json"


def main() -> int:
    policy_config = yaml.safe_load(runner.POLICY_CONFIG.read_text(encoding="utf-8"))
    decoder_payload = yaml.safe_load(runner.DECODER_CONFIG.read_text(encoding="utf-8"))
    decoder_config = DecoderConfig.from_config(decoder_payload["decoder"])
    nodes = runner.pd.read_csv(runner.NODES_PATH)

    graph, primary_policy = runner.load_world(
        runner.PRIMARY_THRESHOLD, nodes, policy_config
    )
    populations = build_populations(
        nodes,
        n_neurons=graph.n_nodes,
        threshold=graph.threshold,
        options=PopulationOptions(**decoder_payload["populations"]),
    )
    candidates = runner.build_candidates(
        graph, nodes, primary_policy, populations, runner.SEED
    )
    indices = candidates["indices"]["C"]

    flipped = nodes.copy()
    flipped.loc[indices, "neurotransmitter_verified"] = "gaba"
    policy = build_synapse_policy(
        graph,
        flipped,
        SignPolicy.from_config(policy_config["transmitter_sign_policy"]),
        WeightPolicy.from_config(policy_config["weight_policy"]["primary"]),
    )
    if not np.all(policy.neuron_signs[indices] == -1):
        raise RuntimeError("candidate sign flip did not produce inhibitory signs")
    if not np.all(policy.neuron_codes[indices] == VERIFIED_INHIBITORY):
        raise RuntimeError("candidate sign flip did not produce inhibitory codes")

    _, result = runner.run_simulation(
        graph, policy, indices, label="phase4g5:sign_flip"
    )
    flipped_run = runner.decode_result(
        result,
        populations,
        decoder_config,
        condition="C_vnc_intrinsic_candidate_sign_flipped",
        threshold=runner.PRIMARY_THRESHOLD,
        seed=runner.SEED,
        indices=indices,
    )

    primary = json.loads(PRIMARY_RESULT.read_text(encoding="utf-8"))
    baseline = primary["conditions"]["C_vnc_intrinsic_candidate"]
    payload = {
        "phase": "4G.5-addendum",
        "purpose": (
            "Measure dependence of the condition C result on the excitatory "
            "sign prior of the stimulated neurons."
        ),
        "variant": {
            "stimulated_neurons": 64,
            "changed_field": "neurotransmitter_verified",
            "changed_value": "gaba",
            "unchanged": [
                "graph",
                "edge counts",
                "synaptic weight transform",
                "decoder populations",
                "decoder thresholds",
                "stimulus current and timing",
                "seed",
            ],
        },
        "primary": {
            "spike_hash": baseline["spike_hash"],
            "decoded_states": baseline["decoder_state_counts"],
            "max_scores": baseline["max_scores"],
            "activity": baseline["activity"],
        },
        "sign_flipped": {
            "spike_hash": flipped_run["spike_hash"],
            "decoded_states": flipped_run["decoder_state_counts"],
            "max_scores": flipped_run["max_scores"],
            "activity": flipped_run["activity"],
            "window_records": flipped_run["window_records"],
        },
        "identical_spikes": baseline["spike_hash"] == flipped_run["spike_hash"],
        "verdict": "PASS",
        "note": (
            "The stimulated neurons still receive direct current and spike; "
            "only their outgoing sign changes. A different decoded outcome "
            "therefore measures sign dependence, not excitability."
        ),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "primary_states": baseline["decoder_state_counts"],
                "flipped_states": flipped_run["decoder_state_counts"],
                "primary_max": baseline["max_scores"],
                "flipped_max": flipped_run["max_scores"],
                "flipped_activity": flipped_run["activity"],
                "identical_spikes": payload["identical_spikes"],
                "output": str(OUTPUT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
