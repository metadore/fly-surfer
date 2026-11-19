"""Phase 4 motor package: populations, decoder, action selection.

The decoder maps BANC motor-neuron population activity to abstract action
labels. ``motor.action_selection`` adds the controller-level conflict and
timing rules. Both are computational constructs, not a description of fly
behaviour; the game binding lives in ``environment.game_controller``.
"""
