"""Shannon information analysis for archived FLY-SURFER artifacts.

This package estimates entropy and mutual information on data that already
exists on disk. It performs no simulation and creates no observations.

Provenance labels used by every result:
  recorded    - run metadata written by an earlier experiment
  measured    - a value derived from detector or recorded output
  simulated   - a value produced by the model
  derived     - a value computed from other stored quantities
"""

from information.bias_correction import (
    bias_table,
    entropy_bias_correction,
    mi_bias_floor,
    required_sample_size,
)
from information.diagnostics import (
    PROVENANCE,
    degeneracy,
    effective_sample_size,
    support_table,
)
from information.discretization import (
    Discretized,
    categorical,
    count_capped,
    declared,
    equal_width,
    ordinal_thresholds,
    quantile,
)
from information.entropy import (
    conditional_entropy,
    entropy,
    entropy_report,
    entropy_sensitivity,
    joint_entropy,
    joint_entropy_report,
)
from information.matching import (
    match_keys,
    validate_cluster_coverage,
    validate_equal_lengths,
)
from information.mutual_information import (
    conditional_mutual_information,
    conditional_mutual_information_report,
    mutual_information,
    mutual_information_report,
)
from information.permutation import cluster_bootstrap_ci, permutation_null
from information.population import (
    level_pattern_codes,
    pattern_codes,
    population_information,
)
from information.statistics import holm, sign_flip_test, summarise

__all__ = [
    "Discretized",
    "categorical",
    "count_capped",
    "declared",
    "equal_width",
    "ordinal_thresholds",
    "quantile",
    "entropy",
    "joint_entropy",
    "conditional_entropy",
    "entropy_report",
    "joint_entropy_report",
    "entropy_sensitivity",
    "mutual_information",
    "conditional_mutual_information",
    "mutual_information_report",
    "conditional_mutual_information_report",
    "pattern_codes",
    "level_pattern_codes",
    "population_information",
    "match_keys",
    "validate_equal_lengths",
    "validate_cluster_coverage",
    "permutation_null",
    "cluster_bootstrap_ci",
    "holm",
    "sign_flip_test",
    "summarise",
    "effective_sample_size",
    "degeneracy",
    "support_table",
    "PROVENANCE",
    "mi_bias_floor",
    "entropy_bias_correction",
    "required_sample_size",
    "bias_table",
]
