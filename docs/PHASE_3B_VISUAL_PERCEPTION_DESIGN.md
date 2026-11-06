# Phase 3B — visual perception design

Status: **proposed design. Not implemented.** No screenshots, perception code,
computer-vision dependency or game integration exists in the repository. This
document is an audit and experimental plan, not a claim that perception works.

## 1. Scope

Phase 3B converts Subway Surfers screenshots into validated `GameState` objects
that the Phase 3A sensory pipeline already accepts. It adds perception as a
separate layer:

```
Subway Surfers screenshot
        |
        v
image validation and preprocessing
        |
        v
object detection
        |
        v
object classification
        |
        v
position and distance estimation
        |
        v
PerceivedScene  ->  GameState  ->  existing Phase 3A encoders
```

The perception pipeline must never write membrane voltages, spikes or synaptic
currents. Its only output contract is a structured scene and, through a
separate adapter, a validated `GameState`.

**Non-goals for Phase 3B:** motor decoding, action selection, reward, learning,
live keyboard control, browser automation, and replacing the Phase 3A
simulator. All remain out of scope.

## 2. Audit of the existing implementation

| Item | Finding |
|---|---|
| `sensory/game_state.py` | Defines the validated scene contract: one player, at most one obstacle, train and coin; no power-ups and no object lists |
| Fields | Player lane/speed/jump/roll; object present/lane/distance; obstacle type low/high |
| Distance convention | Normalised `0` at the player to `1` far away; a game-design convention, not metres |
| Encoders | 14 features, 138 mapped neurons in the delivered configuration |
| Input scheduler | Accepts `(time_ms, GameState)` segments, transitions, masking and deterministic signatures |
| `sensory/visual_encoder.py` | Empty placeholder docstring; no behaviour |
| `environment/`, `motor/`, `learning/` | Placeholder modules; no game loop, action output or learning |
| Dependencies | NumPy, pandas, matplotlib, PyYAML, psutil, pytest; no OpenCV, detector, PyTorch or browser automation |
| Test baseline | 106 tests passing at the time of this design |
| Root README | Read-only for this task; unchanged |

The current schema is deliberately narrow. It can represent the MVPs of Phase
3B, but it cannot represent two obstacles, two coins, or a power-up. That gap
must be handled explicitly rather than hidden by silently discarding objects.

## 3. Reference and technology audit

### 3.1 Reference repositories

| Reference | Visual content | Relevance to Phase 3B |
|---|---|---|
| Fly Hero (`bsgelman/fly-hero`) | No image processing; game events are converted directly into lane-tagged VPN input | Useful as an example of separating scene events from neural input; male-CNS graph and IDs must not be reused |
| Eon fly-brain (`eonsystemspbc/fly-brain`) | No visual perception; Poisson activation of arbitrary neuron sets | Simulation reference only; GPL-2.0-or-later project, no code reuse |
| Drosophila Brain Model | Local directory is empty | No visual material |
| FlyVis (`TuragaLab/flyvis`) | Connectome-constrained deep mechanistic model of the fly visual system | Biologically grounded but not an object detector; audited below and deferred |
| Gymnasium / Stable-Baselines3 | No perception | Future environment/RL baselines only |

No external repository contains a Subway Surfers detector or an
image-to-`GameState` pipeline that could be adopted directly.

### 3.2 FlyVis findings

Local read-only inspection of `references/flyvis-main/flyvis-main`:

- **Licence:** MIT.
- **Model:** PyTorch deep mechanistic network of the fly visual system;
  45,669 cells, 721 ommatidia, 65 cell types, photoreceptor inputs R1–R8 and
  T-cell outputs.
- **Input contract:** movies in receptor/hexagonal space, not arbitrary RGB
  screenshots. Custom stimuli are supported, but a screenshot would need a
  defined projection into the ommatidial layout.
- **Dynamics:** integration timestep is a researcher choice; the code warns
  above 1/50 s, and the published examples use 5–20 ms steps.
- **Dependencies:** PyTorch, torchvision, numba, Hydra, xarray, scikit-learn,
  UMAP and others. The package declares Python `>=3.9,<3.13`; this project uses
  Python 3.13.14, so installation is not currently compatible without a
  separate environment.
- **Pretrained models:** downloaded separately from Google Drive with SHA-256
  checksums; they are not present locally.
- **Compute:** 45,669-cell PyTorch simulation is materially heavier than the
  NumPy LIF simulator and is not a real-time screenshot detector.

**Decision:** do not install or integrate FlyVis in Phase 3B. It is a candidate
for a later, separate biologically inspired representation study, not for the
detection MVP. A future study would need its own environment and an explicit
mapping from screenshots to photoreceptor space.

### 3.3 Candidate perception approaches

| Approach | Advantages | Limitations | Compute | Suitability |
|---|---|---|---|---|
| Classical OpenCV | Deterministic, transparent, CPU-only, easy to test, no training data, Apache 2.0 | Brittle to lighting, skins, effects, occlusion and camera changes; hand-tuned thresholds; weak for many classes | Low; must be measured per frame | **Recommended first baseline** |
| Pretrained YOLO-family detector | Strong general detection; fast lightweight variants; large tooling ecosystem | COCO classes do not match game objects; needs labelled fine-tuning; domain shift; Ultralytics models are AGPL-3.0 | Moderate; GPU helps, CPU depends on model size | Good after dataset and licence decision; prefer permissive forks |
| YOLOX (Apache 2.0) | Anchor-free, lightweight variants, permissive licence, ONNX export | Older tooling than current YOLO; still needs fine-tuning | Moderate | **Recommended learned candidate** |
| NanoDet-Plus (Apache 2.0) | Very small models, designed for edge/mobile inference, permissive | Lower accuracy than larger detectors; needs fine-tuning | Low–moderate | Good CPU candidate |
| MediaPipe Object Detector (Apache 2.0) | Simple API, on-device focus, permissive | Pretrained models target common objects; custom training path is less direct | Low | Optional prototype |
| FlyVis | Biologically grounded visual representation | Not an object detector; receptor-space input; PyTorch; Python <3.13; heavy; pretrained weights external | High | Deferred; separate study |
| Generic visual neuroscience models | Potential interpretable representations | Not trained for game objects; would need probes and validation; unclear mapping to `GameState` | High | Research reference only |

Licence facts used above:

- OpenCV 4.5.0 and later is Apache 2.0.
- Ultralytics YOLO code and models default to AGPL-3.0; this is a distribution
  and network-use obligation and requires an explicit project decision.
- YOLOX and NanoDet-Plus are Apache 2.0. MediaPipe is Apache 2.0.

**Recommendation:** implement the classical baseline first. It provides a
transparent, testable lower bound and generates the annotated dataset. Compare
a permissively licensed learned detector only after the dataset exists. Do not
adopt Ultralytics AGPL code or weights without a deliberate licensing review.

### 3.4 Computational requirements

Phase 3B should define a latency budget before choosing a detector:

- Capture and decode: depends on the screenshot source and storage format.
- Preprocess: fixed resize/ROI, colour conversion and validation; expected to
  be small relative to neural simulation but must be measured.
- Detection/classification: measure p50 and p95 latency on the target CPU and,
  if available, GPU; do not assume real-time from model marketing claims.
- State conversion and schema validation: negligible compared with detection.
- Neural simulation remains the dominant cost: Phase 3A retained about
  134.7 MB of arrays and roughly 2 s per 300 ms condition on the development
  machine.

A provisional target is p95 perception latency ≤ 50 ms at 640×360 on CPU,
giving at least 20 FPS before neural simulation. This is a design target to be
tested, not a measured result. If it cannot be met, the report must state the
achieved latency and restrict claims accordingly.

## 4. Proposed architecture

### 4.1 Modules

| Module | Responsibility | Must not do |
|---|---|---|
| `perception/capture.py` | Offline frame/session ingestion and metadata; no live browser control in 3B | Send keyboard input or modify the game |
| `perception/preprocess.py` | Validate resolution, crop UI, resize, colour conversion, deterministic normalisation | Detect objects or write neural state |
| `perception/detectors/base.py` | Detector protocol returning raw boxes, labels and scores | Know about neurons |
| `perception/detectors/classical.py` | Colour/shape/template baseline | Claim semantic understanding |
| `perception/detectors/learned.py` | Optional permissive learned detector adapter | Download weights implicitly at runtime |
| `perception/classify.py` | Map raw detections to game object categories and resolve duplicates | Fabricate a lane or distance |
| `perception/geometry.py` | Lane assignment, ground-plane proxy and normalised distance estimation | Report metres without calibration |
| `perception/state_builder.py` | Build `PerceivedScene` and adapt it to the existing `GameState` | Import or modify the brain simulator |
| `perception/evaluation.py` | Precision, recall, confusion, localisation, distance error, latency | Tune on the test split |
| `perception/pipeline.py` | Orchestrate one frame or a session deterministically | Share mutable state between independent runs |

### 4.2 Proposed data contracts

`PerceivedObject` should carry at least:

- `category`: low barrier, high barrier, train, coin, power-up (extensible)
- `bbox`: pixel coordinates in the original frame
- `confidence`: detector score
- `lane`: left/center/right or `None`
- `distance_proxy`: normalised `[0, 1]` or `None`
- `track_id`: optional temporal identifier, used only in Phase 3C
- `visible` / `occluded` / `truncated` flags

`PerceivedScene` should carry:

- frame identifier, session identifier, timestamp and source resolution
- player lane and inferred jump/roll state, each with confidence
- an ordered list of perceived objects
- a conversion report describing dropped or unrepresentable objects

`GameState` adaptation for the Phase 3B MVP:

1. Validate the scene and its source metadata.
2. Select the nearest visible obstacle, train and coin independently.
3. Map obstacle subtype to `low`/`high`; reject unknown subtypes rather than
   guessing.
4. Emit `present=False` when no object of that family is visible.
5. Record every additional object and every power-up as unrepresented in
   `SceneConversionReport`; do not silently merge or discard it.
6. Construct the existing `GameState` and let its validators reject impossible
   combinations (for example, jumping and rolling together).

Multi-object support is a proposed additive schema extension for a later
Phase 3B sub-stage. It must not be introduced by bypassing validation or by
placing several objects into one scalar field.

### 4.3 Separation and determinism

- Perception imports the `GameState` contract, not the simulator.
- The neural simulator remains runnable without OpenCV, a detector, a
  screenshot or the game.
- Every stage is independently testable with synthetic arrays.
- Fixed ROI, resize, thresholds and tie-breaking are configuration, not
  hidden constants.
- Detections are sorted deterministically; equal scores use a documented
  tie-break.
- The same frame and configuration must produce the same scene hash.
- No stage may write into the connectome artifact or the Phase 3A mapping.

## 5. Dataset and validation

### 5.1 Capture protocol

- Use one documented game version and platform/emulator build per dataset
  release.
- Record at native resolution and a fixed aspect ratio; store the frame
  timestamp and session identifier.
- Capture multiple sessions, lanes, obstacle types, distances, speeds,
  lighting conditions, effects, occlusion patterns, and multiple simultaneous
  objects.
- Include negative frames with no game objects and transition frames where an
  object enters or leaves view.
- Do not mix camera perspectives in one test split; if perspective changes are
  studied, make them an explicit factor.
- Keep screenshots and annotations local unless the game terms and copyright
  position are reviewed. Do not redistribute game screenshots by default.

### 5.2 Ground truth

Annotations should be JSON Lines or an equivalent validated format with:

- frame/session identity and timestamp
- original resolution and crop parameters
- player lane and jump/roll state
- each object's category, bounding box, lane, distance bin or normalised
  distance proxy, occlusion/truncation flags and annotation confidence
- an `uncertain` flag for ambiguous frames

Distance labels are **not metres**. They are either ordinal bins or a
normalised game-space proxy. Physical distance requires a calibrated camera
model and known object geometry, neither of which exists yet.

### 5.3 Splits and volume

- Split by recording session, never by random frame, to prevent near-duplicate
  leakage.
- Proposed split: 60% train, 20% validation, 20% frozen test, stratified by
  session and scene category.
- Pilot: about 1,000 annotated frames from at least 10 sessions, sufficient to
  test the schema and baseline.
- Full study: 5,000–10,000 frames from 20–40 sessions, depending on class
  balance.
- Double-annotate 10–20% of frames and report box IoU and category agreement.

### 5.4 Metrics

| Metric | Definition |
|---|---|
| Detection precision / recall | Per class and macro, at a fixed confidence threshold |
| mAP@0.5 | Mean average precision at IoU 0.5 |
| Classification accuracy | Correct category among matched detections |
| Confusion matrix | Category × predicted category |
| Localisation error | Centre error in pixels and as a fraction of image diagonal; IoU distribution |
| Player lane accuracy | Correct left/center/right frame classification |
| Jump/roll accuracy | Correct state where visually inferable; `unknown` scored separately |
| Distance error | MAE/RMSE in normalised units for calibrated proxies; ordinal accuracy for bins |
| Distance monotonicity | Spearman correlation between predicted and annotated order |
| Schema validity | Fraction of generated states accepted by `GameState` |
| Latency | p50/p95 end-to-end perception time, warm and cold |
| Throughput | Frames per second at the target resolution |
| Failure taxonomy | Counts by lighting, occlusion, motion blur, effects, missing object |

### 5.5 Provisional acceptance thresholds

These are design gates, not results. They may be revised once the pilot
baseline is measured, but revisions must be recorded before test evaluation.

- Player lane accuracy ≥ 0.95 on the frozen test split.
- Per-class detection precision and recall ≥ 0.85 for obstacle, train and
  coin; mAP@0.5 ≥ 0.75.
- Classification accuracy ≥ 0.85 with a reported confusion matrix.
- Localisation: median IoU ≥ 0.5; median centre error ≤ 5% of image diagonal.
- Normalised distance MAE ≤ 0.10 and monotonic ordering ρ ≥ 0.8 for the
  calibrated proxy.
- 100% of emitted `GameState` objects pass existing validation.
- p95 end-to-end perception latency ≤ 50 ms at 640×360 CPU, if achievable;
  otherwise report the measured value and narrow the claim.

## 6. Experimental protocol

### 6.1 Sub-stages

| Sub-stage | Work | Exit condition |
|---|---|---|
| 3B.0 | Dataset schema, capture protocol, pilot annotations, split manifest | Pilot dataset validates and splits are frozen |
| 3B.1 | Preprocessing and classical baseline | Baseline metrics and failure taxonomy reported |
| 3B.2 | Optional permissive learned detector comparison | Same test split; licence and weights documented |
| 3B.3 | `PerceivedScene` and `GameState` adapter | 100% schema validity; Phase 3A encoder accepts output |
| 3B.4 | End-to-end offline evaluation and report | Acceptance gates met or limitations documented |

### 6.2 Integration test with Phase 3A

For a held-out sequence of annotated frames:

1. Run perception to produce `GameState` objects.
2. Validate every state.
3. Encode with the existing Phase 3A encoders and map to the fixed neuron
   populations.
4. Run the existing simulator for a fixed duration.
5. Compare the resulting schedule and spikes with the same sequence supplied
   from ground-truth states.

The comparison measures how perception errors propagate into the sensory
schedule. It does not claim that the neural response is correct or biological.

### 6.3 Ablations

- Ground-truth states versus perceived states.
- Classical baseline versus learned detector.
- With and without lane geometry.
- With and without distance normalisation.
- Per-class removal to identify which errors dominate.
- Confidence-threshold sweep with precision/recall trade-off.

## 7. Acceptance criteria

Phase 3B is accepted only when all of the following hold:

1. Screenshots from the frozen test split can be processed consistently and
   deterministically.
2. Obstacles, trains and coins are identified with measured precision and
   recall; power-ups are reported as perceived but explicitly unencoded.
3. Lane and normalised distance proxies are estimated and their errors are
   reported.
4. Valid `GameState` objects are generated from perception output.
5. Detection, classification, localisation and distance errors are measured
   against annotations, with a confusion matrix and failure taxonomy.
6. The existing Phase 3A encoders accept the generated states without any
   change to the Phase 3A tests or interfaces.
7. The perception pipeline is independently testable without running the
   neural simulator, and the simulator remains runnable without perception
   dependencies.
8. No claim of real-time or biological visual processing is made without
   measured latency and validation.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| No annotated data exists | Build a pilot first; freeze schema before scaling |
| Game screenshots are copyrighted or restricted | Keep data local; do not redistribute; review game terms before release |
| Domain shift between game versions | Version and session metadata; separate test set per version |
| Hand-tuned classical CV overfits one skin/lighting | Report per-condition metrics; include negative and effect-heavy frames |
| AGPL contamination from YOLO | Use permissive detectors or make a deliberate licence decision |
| Distance is reported as metres without calibration | Use normalised proxies and ordinal labels; state the limitation |
| Multiple objects exceed `GameState` | Report unrepresented objects; propose an additive schema extension |
| Detection latency blocks real-time use | Measure p95; run offline first; decouple capture from simulation |
| Perception errors are hidden by aggregate metrics | Report per-class confusion, failure taxonomy and downstream schedule differences |

## 9. Expected computational cost

- Dataset capture and annotation: dominated by human time, not compute.
- Classical baseline: CPU-only, no training; per-frame cost to be measured.
- Learned detector: one training run on a small dataset, plus inference; GPU
  recommended but not assumed.
- FlyVis: excluded from Phase 3B; a separate environment and a substantial
  compute budget would be required.
- Neural simulation: unchanged from Phase 3A, about 135 MB retained arrays and
  seconds per short condition on the development machine.

## 10. Deliverables

- This design document.
- A versioned screenshot/annotation manifest and split definition.
- Preprocessing, detection, classification and state-conversion modules.
- Evaluation report with the metrics above.
- A `GameState` compatibility test against the Phase 3A encoder.
- Explicit documentation of unrepresented objects, distance limitations and
  any unmet acceptance gate.

## 11. Technology references

- OpenCV licence: <https://opencv.org/license/>
- Ultralytics licence: <https://www.ultralytics.com/license>
- YOLOX: <https://github.com/Megvii-BaseDetection/YOLOX>
- NanoDet-Plus: <https://github.com/RangiLyu/nanodet>
- MediaPipe object detection: <https://developers.google.com/edge/mediapipe/solutions/vision/object_detector>
- FlyVis: <https://github.com/TuragaLab/flyvis>
- Lappalainen et al., *Nature* (2024): <https://doi.org/10.1038/s41586-024-07939-3>

## 12. Claims this design does not make

- It does not claim that any detector works on Subway Surfers yet.
- It does not claim that normalised distance is physical distance.
- It does not claim that FlyVis can consume ordinary screenshots unchanged.
- It does not claim that a perceived `GameState` reproduces the real game
  state.
- It does not claim that downstream neural activity is biologically correct.
