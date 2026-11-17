"""Phase 8 readout package.

SCIENTIFIC STATUS
    A readout is a computational classifier over model motor-population
    activity. Its action labels are decoder labels, not biological motor
    commands, and training a readout is not synaptic plasticity.

The package implements the pieces condition F and control Fβ need:

``features``
    the declared per-decision motor feature vector built from the Phase 8
    ``motor_activity`` block;
``linear``
    the primary linear readout over {LEFT, RIGHT, JUMP, NO_ACTION} and the
    genuinely state-independent bias-only readout used by Fβ;
``ablation``
    the frozen-parameter motor-feature ablation and its four decision labels;
``controller``
    the decision source ``NeuralClosedLoop`` calls instead of the fixed
    decoder;
``trainer``
    a minimal REINFORCE update over the readout parameters only.
"""

from __future__ import annotations

from .ablation import (
    ABLATION_LABELS,
    ablated_logits,
    classify_decision,
)
from .controller import ReadoutController
from .features import (
    ACTION_SPACE,
    MOTOR_ACTIONS,
    MotorFeatureSpec,
)
from .linear import (
    BiasOnlyReadout,
    LinearReadout,
    argmax_action,
    parameter_digest,
)
from .trainer import ReinforceConfig, ReinforceTrainer, discounted_returns

__all__ = [
    "ABLATION_LABELS",
    "ACTION_SPACE",
    "BiasOnlyReadout",
    "LinearReadout",
    "MOTOR_ACTIONS",
    "MotorFeatureSpec",
    "ReadoutController",
    "ReinforceConfig",
    "ReinforceTrainer",
    "ablated_logits",
    "argmax_action",
    "classify_decision",
    "discounted_returns",
    "parameter_digest",
]
