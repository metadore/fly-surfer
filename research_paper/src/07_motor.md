# Chapter 7. Motor Decoding and Game Control

## 7.1 The motor interface

The motor stage exists because the FAFB graph cannot supply it. FAFB contains 110 neurons in a motor super-class, none of which are the leg motor neurons that would drive walking or jumping; the ventral nerve cord is outside the volume. BANC contains 805 neurons annotated as motor, including leg efferents, and the decoder is defined on the BANC graph. This is the one place where the project must switch datasets, and the switch is explicit: no FAFB root identifier appears in a BANC run, and no BANC neuron is selected by FAFB connectivity.

The 805 BANC motor neurons are divided by annotation into three decoded pools and one remainder. LEFT contains 185 neurons, RIGHT 186, and JUMP 20 (ten left and ten right tergotrochanter candidates). The remaining 414 motor neurons carry no LEFT, RIGHT, or JUMP label and are never decoded. There is no ROLL pool and no DUCK pool; the published annotation in this export does not define one, and the project reports them as unsupported rather than inventing a population.

Table 7 lists the pools.

**Table 7.** Decoder-defined motor populations on BANC v888. Pool membership is annotation-derived and is not a functional assignment; an unassigned motor neuron is not evidence that it does nothing. Data source: `configs/motor_decoder.yaml` and `motor/populations.py`; full machine-readable table in `tables/T06_motor_populations.csv`.

| Population | Size | Basis | Role |
|---|---:|---|---|
| LEFT | 185 | annotation: left leg effectors | decoded action |
| RIGHT | 186 | annotation: right leg effectors | decoded action |
| JUMP | 20 | annotation: tergotrochanter candidates (10 L / 10 R) | decoded action |
| unassigned | 414 | motor neurons without LEFT/RIGHT/JUMP label | never decoded |
| **Total** | **805** | annotation-defined motor neurons | |
| ROLL | 0 | unsupported | reported, not invented |
| DUCK | 0 | unsupported | reported, not invented |

The pool definitions are the weakest link in the motor chain. A neuron annotated as innervating a left leg is not thereby a "turn left" command; it may participate in many movements, and the annotation itself is a prediction. The decoder's LEFT, RIGHT, and JUMP labels are therefore labels on populations, not identified commands. This is stated in every Phase 4 and Phase 7 report and is repeated here because it bounds what a decoded action can mean.

## 7.2 The decoding rule

The decoder is a stateless, windowed threshold rule. It divides time into 50 ms half-open windows `[t, t+50)`. For each window it counts spikes in each pool and computes the active fraction — the number of pool neurons that spiked at least once divided by pool size. A pool is eligible for decoding when the window contains at least 5 spikes and at least 3 active neurons, and its active fraction reaches the activation threshold of 0.20. Among eligible pools, the decoder selects the one with the highest active fraction; exact ties are broken by the declared order LEFT, then RIGHT, then JUMP. If no pool is eligible, the action is NO_ACTION. The configuration also declares a release threshold of 0.10 for an optional hysteresis mode, but the characterised and executed decoder runs with smoothing and hysteresis disabled. Every window is therefore decided independently, and the post-drive window is always NO_ACTION.

Two properties follow. First, the decoder cannot invent an action: if no pool crosses threshold, the output is NO_ACTION. Second, the decoder cannot express a graded movement: it emits one of three categorical symbols. The categorical output is what the game consumes, and it is also the reason the decoder is easy to audit.

Figure 18 shows the pools and the decision rule.

![Figure 18. Motor populations and decoder rule. The upper panel shows the three decoded pools (LEFT 185, RIGHT 186, JUMP 20) and the 414 unassigned motor neurons, with ROLL and DUCK marked unsupported. The lower panel is a schematic of the 50 ms window rule: spike count and active fraction per pool, activation threshold 0.20, gate of at least five spikes and three active neurons, highest-fraction arbitration with LEFT/RIGHT/JUMP tie order, and NO_ACTION when no pool is eligible. Pool sizes are annotation counts, not functional assignments. Data source: configs/motor_decoder.yaml; reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md.](figures/F12_motor_decoder.png)

## 7.3 Characterising the rule on controlled drive

Before the decoder was connected to the connectome, Phase 4F characterised it on synthetic population drive. Eleven scenarios were defined: no drive; left; right; jump; left plus jump; right plus jump; bilateral; an ambiguous competition at half of each pool; a uniform drive at 0.3 of every pool; a weak left drive at 2% of the pool; and a weak jump drive at 5%. Each scenario was run at six current amplitudes from 120 to 220 pA, with and without a seeded ±25 pA per-neuron jitter, for 66 declared runs and 66 jitter runs. The drive was applied to neurons chosen by ascending node index, so the characterisation isolates the rule from graph structure.

The response matrix is clean at and above 180 pA. At 120 and 140 pA no driven neuron reaches the 150 pA rheobase, and every scenario returns NEUTRAL. At 160 pA the first window is still empty because the membrane needs time to charge, and the first non-neutral window appears at `[100,150)`; this is charging latency, not decoder delay. At 180, 200, and 220 pA every driven scenario returns its declared active set. The two weak scenarios remain NEUTRAL at every amplitude because their active fractions (0.02 and 0.05) are below the 0.20 activation threshold.

Two edge cases are instructive and are reported as arithmetic, not biology. The ambiguous competition requests half of each pool, but 185 is odd: `round(0.5 × 185) = 92` and `round(0.5 × 186) = 93`, giving active fractions 0.4973 and 0.5000. RIGHT therefore wins because its fraction is strictly higher, not because the decoder prefers RIGHT. The uniform scenario activates all three pools, and LEFT wins because 56/185 = 0.3027 is the highest fraction; the reason field records `simultaneous_actions`, flagging that this is arbitration. Every post-drive window is NEUTRAL in every run, confirming the stateless behaviour.

Jitter changes 24 of 66 primary sequences and leaves 42 of 66 fully identical. The changes are onset shifts and near-tie flips at fractions differing by a few percent; no run produces an action whose pool produced no spikes. This is the expected sensitivity of a threshold rule with categorical output, and it is a reason to treat single-window decoder outputs as noisy.

The synthetic characterisation shows that the decoder implements its declared rule. It does not show that the rule is a good motor decoder, and it says nothing about whether the connectome can drive the pools.

## 7.4 Driving the decoder from BANC structure

Phase 4G connected the decoder to the BANC graph and asked which structural routes can recruit the pools. Six conditions were run for 300 ms on the BANC t5 graph with signed edges, 300 pA stimulation from 50 to 250 ms, and the unchanged decoder. No motor neuron was stimulated. The candidates were 64-neuron groups chosen by structure, not by output: descending neurons ranked by direct motor synapses, VNC intrinsic neurons ranked by direct motor synapses, a random matched group, and a shuffled descending group.

The outcomes are shown in Figure 30 and summarised in Table 8.

![Figure 30. Phase 4G condition outcomes on the BANC graph, including the positive control. Bars show total, motor, and decoded-state counts for conditions A–F. Only condition C (VNC intrinsic candidate) recruited the decoder pools, producing 492 motor spikes across 82 motor neurons and four JUMP windows; condition B produced 18 motor spikes, all in unassigned motor neurons; A, D, E, and F produced no decoder-pool activity. This establishes that the decoder fires when motor tissue is driven directly; it does not establish a sensory-to-motor pathway. Data source: experiments/results/phase_4g/phase_4g_experiment.json (signal_overview).](figures/F24_phase4g_positive_control.png)

**Table 8.** Phase 4G condition outcomes on the BANC t5 graph. Six conditions of 300 ms with 300 pA stimulation of 64 selected neurons, each scored by the unchanged decoder over five 50 ms windows. "Active motor neurons" counts motor cells that spiked at least once. Data source: `experiments/results/phase_4g/phase_4g_experiment.json` (signal_overview).

| Condition | Input | Total spikes | Motor spikes | Active motor neurons | Decoded states |
|---|---|---:|---:|---:|---|
| A | none | 0 | 0 | 0 | NEUTRAL ×5 |
| B | 64 descending candidates | 781 | 18 | 3 | NEUTRAL ×5 |
| C | 64 VNC intrinsic candidates | 1,296 | 492 | 82 | JUMP ×4, NEUTRAL ×1 |
| D | 64 random matched | 704 | 0 | 0 | NEUTRAL ×5 |
| E | 64 shuffled descending | 728 | 0 | 0 | NEUTRAL ×5 |
| F | background/noise only | 0 | 0 | 0 | NEUTRAL ×5 |

Only condition C recruited the decoder. Its 492 motor spikes came from 71 neurons in LEFT (27), RIGHT (32), and JUMP (12) plus 11 unassigned motor neurons, and the decoder produced JUMP in four of five windows. Condition B, despite being selected for direct descending-to-motor synapses, produced 18 motor spikes all in unassigned neurons and no decoder action. Conditions D and E produced no motor spikes at all. The silent baseline conditions A and F show that the model has no spontaneous motor activity under this policy, even with 50 pA background and 50 pA noise.

The correct reading of condition C is narrow. It is a positive control for the decoder and for BANC propagation: when 64 VNC intrinsic neurons are driven strongly, current reaches motor tissue and the decoder fires. It is not a sensory pathway, because the 64 neurons were selected by their motor synapses, not by their response to game events. Chapter 14 shows that when the sensory mapping is used instead, the current dies before the motor pools.

The result also localises the problem. BANC has 17,745 direct descending-to-motor edges at t1, and the motor population is reachable from many directions. The failure in the sensory-to-motor direction is not a lack of anatomical routes; it is a failure to deliver enough current through the routes that the sensory mapping happens to engage. That distinction is developed in Chapter 14.

## 7.5 The sensory-to-motor round trip

Phase 4H.4 ran the actual sensory mapping on the BANC graph. It stimulated the 232 mapped neurons with the seven supported features across two 100-frame segments and compared the actual mapping against five controls: no events, temporal shuffle, feature-identity shuffle, random matched mapping, and constant matched charge. The stimulated population was 232 neurons, of which 171 fired on the full stream; total spikes were 3,562, all in stimulated neurons. No motor neuron fired in any condition. The first-hop targets received current, but the maximum first-hop current was below what the earlier synthetic studies delivered, and the second hop received none. Chapter 14 quantifies the funnel on the Pilot 1 run, where the same pattern appears with a peak somatic depolarisation of −56.926 mV against a −50 mV threshold.

Phase 4H.4 is therefore the bridge between the positive control and the pilots. It shows that the mapping can drive its own neurons, that those neurons can drive first-hop targets weakly, and that the signal does not reach motor populations. The paper treats this as an execution-level result about this mapping and this model, not as a statement about the fly.

## 7.6 The controlled game

The game environment is a standalone endless runner in the Subway Surfers [29] genre, built on the open `endless-surfer` code base. It has three lanes, a fixed timestep of 1/60 s, a player who runs automatically, and obstacles of type barrier, overhead, and train. Coins are collected by lane; collisions end the episode; survival contributes a small per-step reward. The reward is synthetic and defined by the game rules: +1.0 for a coin, −1.0 for a collision, +0.01 per surviving step. It is not a biological dopamine signal, and the paper never treats it as one.

The environment exposes actions LEFT, RIGHT, JUMP, ROLL, and NO_ACTION. The motor adapter passes LEFT, RIGHT, JUMP, and NO_ACTION through unchanged; ROLL is a supported game action but has no BANC population, so a decoded ROLL cannot arise. UNMAPPED and DUCK execute NO_ACTION with a recorded reason, and unknown or invalid outputs also execute NO_ACTION. The adapter records the requested state and the executed action separately, so no unsupported state can silently become a different action.

The observation adapter reports the nearest visible object of each kind, its lane, and a distance proxy normalised by a 25-unit horizon. It does not know future obstacle positions, and it cannot report player pose from the detector. In the game-integration demonstrations the observation came from the game state directly; in the perception replay it came from the detector. The two paths are separate and are not mixed in any single result.

Phase 7 ran fixed-seed demonstrations with four agent types: a random agent, a rule-based agent, a replay of recorded Phase 4 decoder outputs, and a live neural closed loop. Table 9 reports the outcomes.

**Table 9.** Phase 7 controlled-game demonstration runs. All runs are headless, fixed-seed, recorded, and replayable with the game's own replay function. The neural closed loop used the BANC graph with fixed weights and no plasticity. Data source: `experiments/results/phase_7/game_integration_demo.json` and `experiments/results/phase_7/neural_closed_loop.json`; full machine-readable table in `tables/T09_phase7_demonstration.csv`.

| Agent | Seed | Steps | End | Score | Coins | Collisions | Reward |
|---|---:|---:|---|---:|---:|---:|---:|
| random | 42 | 213 | collision | 5.55 | 2 | 1 | 3.12 |
| random | 7 | 332 | collision | 7.53 | 2 | 1 | 4.31 |
| random | 123 | 218 | collision | 4.63 | 1 | 1 | 2.17 |
| rule-based | 42 | 432 | collision | 14.20 | 7 | 1 | 10.31 |
| rule-based | 7 | 531 | collision | 16.85 | 8 | 1 | 12.30 |
| rule-based | 123 | 432 | collision | 14.20 | 7 | 1 | 10.31 |
| Phase 4 replay | 42 | 300 | time limit | 8.00 | 3 | 0 | 6.00 |
| Phase 4 replay | 7 | 300 | time limit | 5.00 | 0 | 0 | 3.00 |
| neural loop | 42 | 213 | collision | 5.55 | 2 | 1 | 3.12 |

The rule-based agent is the strongest, reaching 432–531 steps and 14.20–16.85 score. The random agent reaches 213–332 steps. The Phase 4 replay is open loop and is truncated at 300 steps; its recorded action stream is 200 JUMP and 100 NO_ACTION, with ROLL requests mapped to NO_ACTION because no ROLL pool exists.

The neural closed loop is the critical row. It advanced 213 game updates, which required 7,100 neural steps over 3,550 ms of game time. It recorded 2,852 spikes, all in stimulated neurons, 71 active neurons out of 232 stimulated, 10,215 transmitted spikes, and zero motor spikes. Every one of the 213 decoder states was NO_ACTION. The weights were unchanged from start to end (identical SHA-256), the run repeated deterministically, and the checks `decoder_received_motor_activity` and `decoded_action_supported` were both false while the execution checks were true. The episode ended by collision with reward 3.12, decomposed into 2.0 coin, −1.0 collision, and 2.12 survival.

The neural row coincides numerically with the random-baseline row at seed 42. The source records do not explain the equality, and this paper does not interpret it; it is noted as a documentation issue rather than used as evidence. What the row establishes on its own is simpler and more important: the closed loop executed, the game advanced, and the decoder received no motor activity, so every action was NO_ACTION. A pipeline that always outputs NO_ACTION cannot play the game, regardless of how its score compares to a baseline.

## 7.7 What the motor stage established

Three conclusions follow from this chapter.

First, the decoder works as specified. On synthetic drive it returns the declared action sets at and above 180 pA, remains neutral below rheobase, and behaves statelessly across windows. On BANC structure it fires when motor tissue is driven strongly through VNC intrinsic neurons. The rule is not the bottleneck.

Second, the structural route from the sensory mapping to the motor pools does not deliver enough current. Phase 4H.4 drove 232 neurons, produced 3,562 spikes, and recruited no motor neuron. Phase 7 repeated the result in closed loop with 2,852 spikes and no motor activity. The failure is at the sensory-to-motor stage, not at the decoder.

Third, a decoded action is not a motor command. LEFT, RIGHT, and JUMP are labels on annotation-defined populations, the game consumes categorical symbols, and no limb model exists. Even if a pool had fired, the paper could claim a decoded action, not a movement. The next chapter turns to the learning mechanisms that were supposed to bridge this gap, and shows that they did not.

## 7.8 Summary

The motor interface is an annotation-defined, three-pool decoder on the BANC graph. It is characterised, positive-controlled, and connected to a controlled game. It fires when driven directly and is silent when driven through the sensory mapping or in closed loop. The game demonstrations show a functioning environment and a functioning adapter chain, with a neural agent that always chose NO_ACTION. The chapter's result is a localisation: the decoder is not the failure point; the sensory-to-motor current is.
