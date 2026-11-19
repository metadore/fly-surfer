"""Phase 8 G3: certification boundary for the Condition C null graph.

Stage A checks are cheap invariants on a small fixture. Stage B builds one
60,000-edge exchanged graph — enough edges that R14's absolute 1e-4 plateau
gate is meaningful — and takes it all the way through ``build_certificate``,
``load_certified_graph`` and the Condition C structure check.

These tests do not load BANC and do not certify anything for the campaign.
The certificate they write lives in a pytest temporary directory.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from brain.banc_graph import PROJECT_ROOT, BancConnectome
from experiments.phase_8.conditions.base import ConditionError, _check_structure
from experiments.phase_8_random import (
    CertificationError,
    OutputNamespace,
    certificate_refusal_reason,
    describe_certification,
    describe_randomization,
    graph_digest,
    load_certificate,
    load_certified_graph,
    load_structure,
    rewire_target_exchange,
    structure_record,
    validate_randomization,
    verify_structure_record,
)
from experiments.phase_8_random import certification as cert
from experiments.phase_8_random.certify_banc import _compare_builds
from plasticity.synthetic import synthetic_graph, synthetic_policy

STAGE_B_NODES = 60_000
STAGE_B_EDGES = 60_000
STAGE_B_SEED = 5
STRUCTURE_SEED = 1_258_589_452  # seed_plan(20261116, "C", 1)["structure"]
MASTER_SEED = 20_261_116
CAMPAIGN_SEED = 1
SWAPS_PER_EDGE = 10.0
PLATEAU_INTERVAL = 1_000


def _protocol_path() -> Path:
    return PROJECT_ROOT / cert.PROTOCOL_PATH


@pytest.fixture(scope="module")
def stage_b():
    """Stage B: one graph at a size where R14 can actually be satisfied."""
    original = synthetic_graph(STAGE_B_NODES, STAGE_B_EDGES, seed=STAGE_B_SEED)
    first = rewire_target_exchange(
        original,
        seed=STRUCTURE_SEED,
        swaps_per_edge=SWAPS_PER_EDGE,
        plateau_interval=PLATEAU_INTERVAL,
    )
    second = rewire_target_exchange(
        original,
        seed=STRUCTURE_SEED,
        swaps_per_edge=SWAPS_PER_EDGE,
        plateau_interval=PLATEAU_INTERVAL,
    )
    report = validate_randomization(
        original,
        first,
        policy_original=synthetic_policy(original),
        policy_new=synthetic_policy(first.graph),
        reference_digest=graph_digest(second.graph),
        master_seed=MASTER_SEED,
        campaign_seed=CAMPAIGN_SEED,
    )
    return {
        "original": original,
        "result": first,
        "second": second,
        "report": report,
        "reproducibility": _compare_builds(first.graph, second.graph),
    }


@pytest.fixture(scope="module")
def certified(tmp_path_factory, stage_b):
    """Write the Stage B graph and its certificate into a real namespace."""
    if not _protocol_path().is_file():
        pytest.skip("the frozen REV4 protocol document is not present")

    root = tmp_path_factory.mktemp("phase_8_certification")
    original_path = root / "banc_graph_t5.npz"
    stage_b["original"].save(original_path)

    namespace_dir = root / f"seed_{CAMPAIGN_SEED}"
    namespace = OutputNamespace(namespace_dir)
    graph_path = namespace.path(f"banc_graph_random_t5_seed_{CAMPAIGN_SEED}.npz")
    stage_b["result"].graph.save(graph_path)

    graph_identity = cert.file_identity(graph_path)
    certificate = cert.build_certificate(
        original_identity=cert.file_identity(original_path),
        output_identity=graph_identity,
        protocol_identity=cert.file_identity(_protocol_path(), root=PROJECT_ROOT),
        report=stage_b["report"],
        master_seed=MASTER_SEED,
        campaign_seed=CAMPAIGN_SEED,
        structure_seed=STRUCTURE_SEED,
        swaps_per_edge=SWAPS_PER_EDGE,
        construction={
            "candidate_block": 4096,
            "batch_size": stage_b["result"].batch_size,
            "plateau_interval": PLATEAU_INTERVAL,
            "max_attempts": int(stage_b["result"].max_attempts),
            "graph_npz_name": graph_path.name,
        },
        reproducibility=stage_b["reproducibility"],
        memory={},
        runtime_seconds=1.0,
    )
    certificate_path, certificate_sha = cert.write_certificate(namespace, certificate)
    manifest_path, _ = cert.write_manifest(
        namespace,
        certificate=certificate,
        certificate_identity={
            "path": certificate_path.as_posix(),
            "sha256": certificate_sha,
        },
        graph_identity=graph_identity,
    )
    namespace.complete(required=(graph_path, certificate_path, manifest_path))
    return {
        "root": root,
        "namespace": namespace,
        "graph_path": graph_path,
        "certificate_path": certificate_path,
        "certificate_sha256": certificate_sha,
        "manifest_path": manifest_path,
        "certificate": certificate,
    }


# ---------------------------------------------------------------------------
# Stage A invariants
# ---------------------------------------------------------------------------


def test_batch_size_does_not_change_the_graph():
    original = synthetic_graph(600, 600, seed=11)
    small = rewire_target_exchange(
        original, seed=99, swaps_per_edge=10.0, batch_size=37, plateau_interval=50
    )
    large = rewire_target_exchange(
        original, seed=99, swaps_per_edge=10.0, batch_size=10_000, plateau_interval=50
    )
    assert graph_digest(small.graph) == graph_digest(large.graph)
    assert small.accepted == large.accepted


def test_exchange_rejects_self_loops_duplicates_and_no_change(stage_b):
    rejected = stage_b["result"].rejected
    assert rejected["self_loop"] > 0
    assert rejected["duplicate_pair"] > 0
    assert rejected["no_change"] > 0
    assert rejected["out_of_range"] == 0
    graph = stage_b["result"].graph
    assert not np.any(graph.edge_src == graph.edge_dst)
    keys = np.unique(
        np.asarray(graph.edge_src, dtype=np.int64) * graph.n_nodes
        + np.asarray(graph.edge_dst, dtype=np.int64)
    )
    assert keys.size == graph.n_edges


def test_transmitter_signs_are_preserved(stage_b):
    r8 = stage_b["report"]["gates"]["R8"]
    assert r8["evaluated"] is True
    assert r8["per_node_signs_equal"] is True
    assert r8["per_node_codes_equal"] is True
    assert r8["per_edge_sign_reordering_equal"] is True
    assert r8["signed_edges_original"] == r8["signed_edges_new"]
    assert r8["signed_synapses_original"] == r8["signed_synapses_new"]
    assert "PROPOSED" in r8["parameterisation"]


def test_per_source_weights_and_ungated_checks_are_reported(stage_b):
    gates = stage_b["report"]["gates"]
    assert gates["R9b"]["per_source_weight_multiset_equal"] is True
    assert gates["R9b"]["out_degree_profile_equal"] is True
    assert gates["R9"]["multiset_equal"] is True
    assert gates["R15"]["gated"] is False
    assert gates["R16"]["gated"] is False


# ---------------------------------------------------------------------------
# R1-R18 report
# ---------------------------------------------------------------------------


def test_all_eighteen_requirements_are_reported(stage_b):
    report = stage_b["report"]
    assert set(describe_randomization()["gates"]) <= set(report["gates"])
    assert "R9b" in report["gates"]
    assert report["passed"] is True, report["failures"]
    assert report["failures"] == []
    assert report["integrity"]["match"] is True
    for name in describe_certification()["mandatory_gates"]:
        assert report["gates"][name]["pass"] is True, name
    assert report["gates"]["R14"]["evaluated"] is True
    assert report["gates"]["R14"]["max_abs_change"] < 1.0e-4
    assert report["gates"]["R18"]["derivation_verified"] is True


def test_descriptions_avoid_a_mixing_claim():
    description = describe_randomization()
    assert "not_preserved" in description
    assert "not a proof" in description["plateau_note"]
    certification = describe_certification()
    assert {"R14", "R17"} <= set(certification["mandatory_gates"])
    assert "R14 not evaluated" in certification["refusals"]


# ---------------------------------------------------------------------------
# certificate acceptance
# ---------------------------------------------------------------------------


def test_certificate_round_trip(certified):
    certificate = load_certificate(certified["certificate_path"])
    assert certificate["status"] == "certified"
    assert certificate_refusal_reason(certificate) is None
    assert certificate["randomization_quality"]["u18"] == "PROPOSED — not approved"

    graph, loaded = load_certified_graph(certified["certificate_path"])
    assert isinstance(graph, BancConnectome)
    assert loaded["output_graph"]["graph_digest"] == graph_digest(graph)
    assert graph.n_edges == STAGE_B_EDGES
    assert cert.sha256_file(certified["graph_path"]) == loaded["output_graph"]["sha256"]

    record = structure_record(
        certificate,
        certificate_path=certified["certificate_path"],
        certificate_sha256=certified["certificate_sha256"],
    )
    assert verify_structure_record(record)["status"] == "certified"
    assert record["seed"] == STRUCTURE_SEED
    assert record["u18_status"] == "PROPOSED — not approved"
    _check_structure(record)


def test_one_call_gives_conditions_the_graph_and_its_record(certified):
    graph, record = load_structure(certified["certificate_path"])
    loaded, _ = load_certified_graph(certified["certificate_path"])
    assert graph_digest(graph) == graph_digest(loaded) == record["graph_digest"]
    assert record["campaign_seed"] == CAMPAIGN_SEED
    _check_structure(record)


def test_manifest_records_both_graph_identities(certified):
    payload = json.loads(certified["manifest_path"].read_text(encoding="utf-8"))
    assert payload["original_graph"]["sha256"] != payload["output_graph"]["sha256"]
    assert payload["certificate"]["sha256"] == certified["certificate_sha256"]
    assert payload["protocol"]["sha256"] == cert.EXPECTED_PROTOCOL_SHA256


def test_a_failed_gate_blocks_the_certificate():
    original = synthetic_graph(600, 600, seed=11)
    result = rewire_target_exchange(
        original, seed=1, swaps_per_edge=10.0, plateau_interval=20
    )
    # No policies -> R8 cannot be evaluated, so the report is not passed.
    report = validate_randomization(original, result)
    assert report["passed"] is False
    assert "R8" in report["failures"]
    with pytest.raises(CertificationError, match="failures"):
        cert.build_certificate(
            original_identity={"path": "a", "bytes": 1, "sha256": "a" * 64},
            output_identity={"path": "b", "bytes": 2, "sha256": "b" * 64},
            protocol_identity=cert.file_identity(_protocol_path(), root=PROJECT_ROOT),
            report=report,
            master_seed=MASTER_SEED,
            campaign_seed=CAMPAIGN_SEED,
            structure_seed=STRUCTURE_SEED,
            swaps_per_edge=10.0,
            construction={},
            reproducibility={"byte_identical": True},
            memory={},
            runtime_seconds=0.0,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(status="incomplete"),
        lambda c: c["protocol"].update(sha256="0" * 64),
        lambda c: c["report"].update(failures=["R14"]),
        lambda c: c["report"]["gates"]["R6"].update({"pass": False}),
        lambda c: c["report"]["gates"]["R14"].update(evaluated=False),
        lambda c: c["reproducibility"].update(byte_identical=False),
        lambda c: c["output_graph"].update(sha256=c["original_graph"]["sha256"]),
        lambda c: c["seed"].update(derivation_verified=False),
    ],
)
def test_each_refusal_reason_is_enforced(certified, mutate):
    certificate = copy.deepcopy(certified["certificate"])
    mutate(certificate)
    assert certificate_refusal_reason(certificate) is not None


# ---------------------------------------------------------------------------
# refusal at load and at the condition boundary
# ---------------------------------------------------------------------------


def test_incomplete_namespace_is_refused(certified):
    marker = certified["namespace"].path(cert.MARKER_NAME)
    marker.write_text('{"status": "incomplete"}\n', encoding="utf-8")
    try:
        with pytest.raises(CertificationError, match="marked incomplete"):
            load_certified_graph(certified["certificate_path"])
        record = structure_record(
            certified["certificate"],
            certificate_path=certified["certificate_path"],
            certificate_sha256=certified["certificate_sha256"],
        )
        with pytest.raises(CertificationError, match="marked incomplete"):
            verify_structure_record(record)
        with pytest.raises(ConditionError, match="certificate was refused"):
            _check_structure(record)
    finally:
        marker.unlink()


def test_tampered_graph_file_is_refused(certified):
    backup = certified["graph_path"].read_bytes()
    try:
        certified["graph_path"].write_bytes(backup + b"\x00")
        with pytest.raises(CertificationError, match="SHA-256"):
            load_certified_graph(certified["certificate_path"])
    finally:
        certified["graph_path"].write_bytes(backup)


def test_structure_record_must_name_a_certificate(certified):
    record = structure_record(
        certified["certificate"],
        certificate_path=certified["certificate_path"],
        certificate_sha256=certified["certificate_sha256"],
    )
    del record["certificate_path"]
    with pytest.raises(CertificationError, match="no certificate_path"):
        verify_structure_record(record)
    # A record without a certificate keeps the pre-certification contract.
    assert _check_structure(
        {"graph_digest": "c" * 64, "randomization_quality": {"passed": True}}
    )


def test_structure_record_cannot_forge_the_digest(certified):
    record = structure_record(
        certified["certificate"],
        certificate_path=certified["certificate_path"],
        certificate_sha256=certified["certificate_sha256"],
    )
    record["graph_digest"] = "d" * 64
    with pytest.raises(CertificationError, match="digest"):
        verify_structure_record(record)
    with pytest.raises(ConditionError, match="certificate was refused"):
        _check_structure(record)
