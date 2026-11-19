"""Phase 8 G3: campaign-level checks across the Condition C seed set.

These tests exercise the pure logic of
:mod:`experiments.phase_8_random.campaign_summary` on synthetic entry
dictionaries. They do not load BANC graphs, do not certify anything and do not
assert that any seed of the real campaign is certified.
"""

from __future__ import annotations

from experiments.phase_8_random import certification as cert
from experiments.phase_8_random import campaign_summary as summary


class _Graph:
    n_nodes = 172_433
    n_edges = 1_535_710


def _gates() -> dict:
    return {
        "R1": {"swaps_attempted": 15_456_798},
        "R2": {"swaps_accepted": 15_357_100, "target_accepted": 15_357_100},
        "R3": {
            "swaps_rejected": {
                "duplicate_pair": 97_119,
                "self_loop": 1_069,
                "no_change": 1_510,
                "out_of_range": 0,
            },
            "acceptance_rate": 0.9935,
        },
        "R4": {"fraction_rewired": 0.9979},
        "R5": {"jaccard": 0.001, "intersection": 3_183},
        "R6": {"max_abs_out_degree_change": 0},
        "R7": {"max_abs_in_degree_change": 0},
        "R8": {
            "signed_edges_new": 683_100,
            "signed_synapses_new": 8_426_168,
            "unsigned_edges_new": 852_610,
            "per_node_signs_equal": True,
            "per_node_codes_equal": True,
            "per_edge_sign_reordering_equal": True,
        },
        "R9": {"multiset_equal": True, "synapse_sum": 18_552_546, "min": 5,
               "max": 913},
        "R9b": {"per_source_weight_multiset_equal": True,
                "out_degree_profile_equal": True},
        "R10": {"duplicate_pairs": 0},
        "R11": {"self_edges": 0},
        "R12": {"csr_invariants_pass": True},
        "R13": {
            "mean_out_neighbour_jaccard": 0.0003,
            "mean_out_neighbour_jaccard_all_nodes": 0.24,
            "active_nodes": 130_709,
            "isolated_in_both": 41_724,
        },
        "R14": {"tail_samples": 31, "max_abs_change": 5.1e-05,
                "final_jaccard": 0.001},
        "R15": {
            "before": {"n_components": 24_470, "largest_component": 147_759},
            "after": {"n_components": 24_350, "largest_component": 148_055},
        },
        "R16": {"reciprocity_before": 0.115, "reciprocity_after": 0.0017,
                "degree_assortativity_before": -0.0619,
                "degree_assortativity_after": -0.0102},
        "R17": {"graph_digest": "c" * 64, "reference_digest": "c" * 64},
        "R18": {
            "derivation_verified": True,
            "derived_structure_seed": 1_258_589_454,
            "seed_used": 1_258_589_454,
            "entropy": [20261116, 2, 4],
        },
    }


def _record(seed: int = 2) -> dict:
    return {
        "seed": 1_258_589_452 + seed,
        "campaign_seed": seed,
        "graph_digest": f"{seed:02x}" * 32,
        "graph_sha256": f"{seed:02x}" * 4 + "0" * 56,
        "certificate_sha256": f"{seed + 100:02x}" * 4 + "0" * 56,
        "protocol_sha256": cert.EXPECTED_PROTOCOL_SHA256,
        "construction": {"parameterisation": "target_exchange"},
        "u18_status": "PROPOSED",
    }


def _entry(seed: int = 2, **overrides) -> dict:
    entry = {
        "seed": seed,
        "status": "certified",
        "nodes": 172_433,
        "edges": 1_535_710,
        "accepted": 15_357_100,
        "signed_edges": 683_100,
        "signed_synapses": 8_426_168,
        "weight_sum": 18_552_546,
        "out_degree_max_change": 0,
        "in_degree_max_change": 0,
        "duplicate_pairs": 0,
        "self_edges": 0,
        "csr_invariants": True,
        "unsigned_edges": 852_610,
        "weight_multiset_equal": True,
        "sign_per_node_equal": True,
        "sign_codes_per_node_equal": True,
        "sign_per_edge_reordering_equal": True,
        "r9b_source_weight_multiset_equal": True,
        "r9b_out_degree_profile_equal": True,
        "r17_byte_identical": True,
        "r18_derivation_verified": True,
        "structure_seed": 1_258_589_452 + seed,
        "graph_digest": f"{seed:02x}" * 32,
        "graph_sha256": f"{seed:02x}" * 4 + "0" * 56,
        "certificate_sha256": f"{seed + 100:02x}" * 4 + "0" * 56,
        "provenance": {
            "manifest_sha256": "a" * 64,
            "results_sha256": "b" * 64,
            "created_at": "2026-11-17T00:00:00+00:00",
            "source_check_passed": True,
            "protocol_sha256": cert.EXPECTED_PROTOCOL_SHA256,
            "declared_structure_seed": 1_258_589_452 + seed,
            "declared_campaign_seed": seed,
        },
    }
    entry.update(overrides)
    return entry


def test_parse_seeds_accepts_range_and_list():
    assert summary._parse_seeds("1-3") == [1, 2, 3]
    assert summary._parse_seeds("2,5,9") == [2, 5, 9]


def test_seed_1_keeps_its_historical_graph_filename():
    assert summary._paths(1)["graph"].name == "banc_graph_random_t5_seed_1.npz"
    assert summary._paths(2)["graph"].name == "banc_graph_random_t5_seed_2.npz"
    assert summary._paths(16)["marker"].name == cert.MARKER_NAME


def test_invariant_fields_reads_every_reported_measurement():
    fields = summary._invariant_fields(_record(2), _gates(), _Graph())
    assert fields["nodes"] == 172_433
    assert fields["attempted"] == 15_456_798
    assert fields["rejected"]["duplicate_pair"] == 97_119
    assert fields["intersection"] == 3_183
    assert fields["weight_min"] == 5
    assert fields["weight_max"] == 913
    assert fields["unsigned_edges"] == 852_610
    assert fields["sign_per_node_equal"] is True
    assert fields["r9b_out_degree_profile_equal"] is True
    assert fields["r17_byte_identical"] is True
    assert fields["r18_entropy"] == [20261116, 2, 4]
    assert fields["r18_derivation_verified"] is True
    assert fields["structure_seed"] == 1_258_589_454


def test_cross_seed_checks_pass_for_distinct_seeds():
    cross = summary.cross_seed_checks([_entry(seed) for seed in (1, 2, 3)])
    assert cross["certified_seeds"] == [1, 2, 3]
    assert cross["unique_structure_seeds"] is True
    assert cross["unique_graph_digests"] is True
    assert cross["no_duplicate_artifacts"] is True
    assert cross["all_invariants_shared"] is True
    assert cross["provenance_complete"] is True
    assert cross["regeneration_attempted"] is False
    assert cross["deterministic_regeneration_all"] is False


def test_cross_seed_checks_detect_a_duplicated_artifact():
    entries = [
        _entry(1),
        _entry(2, graph_digest=_entry(1)["graph_digest"]),
        _entry(3, graph_sha256=_entry(1)["graph_sha256"]),
    ]
    cross = summary.cross_seed_checks(entries)
    assert cross["unique_graph_digests"] is False
    assert cross["unique_graph_sha256"] is False
    assert cross["no_duplicate_artifacts"] is False


def test_cross_seed_checks_detect_a_changed_invariant():
    entries = [_entry(1), _entry(2, nodes=172_434), _entry(3)]
    cross = summary.cross_seed_checks(entries)
    assert cross["single_valued_invariants"]["node_counts"] is False
    assert cross["all_invariants_shared"] is False


def test_cross_seed_checks_exclude_uncertified_entries():
    entries = [_entry(1), {"seed": 2, "status": "missing", "missing": ["certificate"]}]
    cross = summary.cross_seed_checks(entries)
    assert cross["certified_seeds"] == [1]
    assert cross["entries"] == 2
    assert cross["required_seeds"] == list(range(1, 17))


def test_cross_seed_checks_record_regeneration_outcome():
    entries = [
        _entry(1, regenerated_matches=True),
        _entry(2, regenerated_matches=False),
    ]
    cross = summary.cross_seed_checks(entries)
    assert cross["regeneration_attempted"] is True
    assert cross["deterministic_regeneration_all"] is False


def test_cross_seed_checks_require_complete_provenance():
    broken = _entry(2)
    broken["provenance"]["declared_campaign_seed"] = 99
    cross = summary.cross_seed_checks([_entry(1), broken])
    assert cross["provenance_complete"] is False


def test_load_seed_reports_a_missing_namespace():
    entry = summary.load_seed(99)
    assert entry["status"] == "missing"
    assert "certificate" in entry["missing"]


def test_write_summary_is_atomic(tmp_path):
    path = summary.write_summary({"schema_version": 1}, tmp_path / "summary.json")
    assert path.read_text(encoding="utf-8").strip().endswith("}")
    assert not path.with_suffix(".json.tmp").exists()
