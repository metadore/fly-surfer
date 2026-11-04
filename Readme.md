# 🧠 FLY-SURFER

### Teaching a Fruit Fly Brain to Play Subway Surfers Through Connectome-Based Neural Simulation

<p align="center">
  <strong>Can a biological brain connectome learn to play a modern video game?</strong>
</p>

<p align="center">
  Computational Neuroscience · Connectomics · Spiking Neural Networks · Neuromorphic Computing · Reinforcement Learning · Information Theory
</p>

---

# 1. Project Overview

## 1.1 What is FLY-SURFER?

FLY-SURFER is an experimental computational neuroscience and artificial intelligence project that investigates whether the neural architecture of a real fruit fly (*Drosophila melanogaster*) can be computationally simulated and adapted to control a video game.

The project uses publicly available fruit fly connectome data from **FlyWire**, which provides detailed information about neurons, synaptic connections, neuronal classifications, neurotransmitter predictions, and other anatomical properties.

Instead of constructing an ordinary artificial neural network from scratch, we intend to use biological connectivity information as the foundation of our computational architecture.

The resulting system will:

1. Load and process real fruit fly neural connectivity data.
2. Reconstruct a computational representation of selected biological neural circuits.
3. Simulate neuronal activity using spiking neuron models.
4. Convert visual observations from Subway Surfers into neural sensory signals.
5. Allow simulated neural populations to generate motor decisions.
6. Introduce biologically inspired learning mechanisms.
7. Evaluate whether the network improves its gameplay performance through experience.
8. Compare biological connectivity against alternative network architectures.

Our ultimate objective is to investigate whether a connectome-derived neural system can learn to interact with a game environment through sensory feedback, neural activity, motor outputs, and reward-modulated plasticity.

## 1.2 The Central Research Question

**Can a computationally simulated fruit fly connectome, combined with biologically inspired synaptic plasticity, develop useful game-playing behaviour when connected to a modern gaming environment?**

Additional research questions:

* Does biological connectivity provide an advantage over randomly generated connectivity?
* Can a spiking neural network learn useful action-selection patterns?
* Does dopamine-inspired reward modulation improve behavioural performance?
* Which neural populations become informative about particular game states?
* Can information theory help identify important neural pathways?
* How much of the original biological connectivity needs to be simulated?
* Can a relatively small neural circuit achieve useful behaviour?

## 1.3 What Makes This Project Different?

Conventional game-playing AI generally relies on artificial neural networks, computer vision, reinforcement learning, or combinations of these methods.

FLY-SURFER takes a different approach.

| Conventional Game AI                      | FLY-SURFER                                       |
| ----------------------------------------- | ------------------------------------------------ |
| Artificially designed neural architecture | Connectome-derived architecture                  |
| Conventional neural activations           | Spiking neural activity                          |
| Artificially learned network structure    | Anatomically informed connectivity               |
| Conventional reward optimisation          | Dopamine-inspired reward modulation              |
| Standard feature representations          | Biologically motivated sensory encoding          |
| Artificial action-selection layers        | Connectome-informed motor decoding               |
| Performance-oriented evaluation           | Performance and neuroscience-oriented evaluation |

The objective is not to assume that biological neural architecture is automatically superior.

We want to test that experimentally.

---

# 2. Scientific Foundation

## 2.1 FlyWire Connectome

The primary biological dataset comes from FlyWire.

FlyWire provides a large-scale reconstruction of the adult fruit fly brain using electron microscopy and associated computational annotation.

Our downloaded dataset contains several categories of information.

### Primary datasets

| Dataset                                   | Application in FLY-SURFER                           | Priority |
| ----------------------------------------- | --------------------------------------------------- | -------- |
| Connections (Filtered)                    | Constructing the directed neural connectivity graph | Critical |
| Connections (Unfiltered)                  | Alternative connectivity analysis and validation    | High     |
| Cell Types                                | Identifying neuronal populations                    | Critical |
| Classification / Hierarchical Annotations | Understanding neuronal classifications              | Critical |
| Neurotransmitter Type Predictions         | Assigning predicted neurotransmitter identities     | Critical |
| Connectivity Tags                         | Identifying annotated connectivity properties       | High     |
| Marked Neuron Coordinates                 | Spatial organisation and visualisation              | Medium   |
| Cell Size Measurements                    | Additional biological analysis                      | Low      |
| Proofread Cell Names and Groups           | Identifying documented neuronal groups              | High     |
| Visual Neuron Annotations                 | Understanding visual processing pathways            | High     |
| Visual Neuron Columns                     | Investigating visual system organisation            | Medium   |
| Community Labels                          | Exploring network organisation                      | Medium   |
| Raw Synapse Table                         | Detailed synaptic analysis                          | Later    |
| Neuron Skeletons                          | Morphological analysis                              | Later    |

### Important distinction

The filtered connectivity dataset will be our initial working dataset.

The unfiltered dataset will be retained for comparison.

We will not immediately load every available neuron and synapse into a simulator.

Instead, we will progressively develop:

1. A small test network.
2. A selected biological circuit.
3. A larger connectome-derived network.
4. An expanded simulation if computational resources permit.

This prevents memory exhaustion and makes debugging manageable.

## 2.2 Biological Data Limitations

The downloaded FAFB dataset represents the female adult fruit fly brain.

It should not be treated as a complete representation of every neural structure required for a biological brain-to-muscle simulation.

In particular, we must investigate the availability of descending pathways, motor-related neurons, and the nerve cord.

If additional connectome data is required, we will investigate compatible datasets such as the FlyWire Male CNS connectome.

We must also account for differences between connectome datasets before combining them.

A biological connectivity graph is not automatically a complete physiological model.

It does not necessarily provide:

* Exact membrane properties for every neuron.
* Complete synaptic receptor information.
* Exact synaptic conductances.
* Complete neurotransmitter concentrations.
* All neuronal time constants.
* All biological plasticity mechanisms.

Where biological parameters are unavailable, we will explicitly document our computational assumptions.

---

# 3. Overall System Architecture

The project will contain six major subsystems.

```text
                  FLYWIRE DATA
                       |
                       v
               CONNECTOME LOADER
                       |
                       v
              BIOLOGICAL NETWORK
                 CONSTRUCTION
                       |
                       v
              SPIKING NEURAL NETWORK
                       |
             +---------+---------+
             |                   |
             v                   v
       SENSORY INPUT       NEURAL ACTIVITY
             |                   |
             v                   |
       GAME OBSERVATION          |
             |                   |
             +---------+---------+
                       |
                       v
                 NEURAL PROCESSING
                       |
                       v
                  MOTOR DECODER
                       |
                       v
                  GAME ACTION
                       |
                       v
                 SUBWAY SURFERS
                       |
                       v
                  GAME REWARD
                       |
                       v
              DOPAMINE MODULATION
                       |
                       v
              SYNAPTIC PLASTICITY
                       |
                       +-------> NEURAL NETWORK
```

The architecture is divided into:

1. Biological data processing.
2. Neural network construction.
3. Neural activity simulation.
4. Sensory encoding.
5. Motor decoding.
6. Learning and evaluation.

---

# 4. Technology Stack

We will primarily use Python because of its scientific computing ecosystem.

## 4.1 Core Programming Language

**Python 3.11**

Python will handle:

* Dataset processing.
* Connectome reconstruction.
* Neural simulations.
* Mathematical computations.
* Training experiments.
* Statistical evaluation.
* Game interaction.
* Visualisation.

Python 3.11 is our initial target for compatibility with scientific libraries.

## 4.2 Scientific Computing

| Technology | Purpose                                   |
| ---------- | ----------------------------------------- |
| NumPy      | Numerical computation                     |
| Pandas     | Dataset processing                        |
| SciPy      | Sparse matrices and scientific algorithms |
| PyArrow    | Reading and processing Parquet/Arrow data |
| NetworkX   | Directed graph construction and analysis  |
| Matplotlib | Experimental visualisation                |
| Seaborn    | Statistical visualisation                 |

## 4.3 Neural Simulation

We will investigate:

| Technology | Purpose                                              |
| ---------- | ---------------------------------------------------- |
| Brian2     | Spiking neural network simulation                    |
| PyTorch    | Supporting trainable models and numerical components |
| Norse      | PyTorch-based spiking neural networks                |
| NumPy      | Custom neural simulation experiments                 |

**Initial recommendation: Brian2.**

Brian2 is particularly suitable for implementing mathematical neuron models and investigating neuronal dynamics.

We will initially use it for small and medium-sized experimental circuits.

For larger networks, we will benchmark alternative sparse and accelerated simulation approaches.

We will not assume that an entire FlyWire connectome can be simulated efficiently on an ordinary laptop.

## 4.4 Machine Learning

| Technology        | Purpose                                    |
| ----------------- | ------------------------------------------ |
| PyTorch           | Trainable neural components                |
| Stable-Baselines3 | Reinforcement-learning baselines           |
| Scikit-learn      | Feature selection and information analysis |
| SciPy             | Statistical and mathematical methods       |

PPO and other reinforcement-learning algorithms will primarily be used as comparison baselines and experimental components.

We will not automatically replace the biological network with a conventional PPO policy.

## 4.5 Game Interaction

| Technology             | Purpose                                         |
| ---------------------- | ----------------------------------------------- |
| OpenCV                 | Visual observation processing                   |
| MSS                    | Screen capture                                  |
| PyAutoGUI              | Keyboard control                                |
| Selenium or Playwright | Browser automation where appropriate            |
| Gymnasium              | Standardised experimental environment interface |

The exact game interface will depend on the browser version and permitted interaction methods.

We will first develop a controlled Subway Surfers-like environment before integrating the actual game.

## 4.6 Development Tools

* Visual Studio Code
* Git
* GitHub
* PowerShell
* Jupyter Notebook
* Python virtual environment
* pytest

---

# 5. Repository Structure

The repository will be organised into independently testable modules.

```text
FLY-SURFER/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── LICENSE
│
├── configs/
│   ├── brain_config.yaml
│   ├── neuron_config.yaml
│   ├── learning_config.yaml
│   ├── environment_config.yaml
│   └── experiment_config.yaml
│
├── datasets/
│   ├── README.md
│   ├── raw/
│   │   ├── connections/
│   │   ├── annotations/
│   │   ├── neurotransmitters/
│   │   ├── visual_system/
│   │   ├── coordinates/
│   │   └── skeletons/
│   │
│   ├── processed/
│   │   ├── neurons/
│   │   ├── edges/
│   │   ├── connectivity/
│   │   └── metadata/
│   │
│   └── samples/
│
├── notebooks/
│   ├── 01_dataset_exploration.ipynb
│   ├── 02_connectome_visualisation.ipynb
│   ├── 03_neural_statistics.ipynb
│   ├── 04_mutual_information.ipynb
│   └── 05_training_analysis.ipynb
│
├── src/
│   └── fly_surfer/
│       │
│       ├── data/
│       │   ├── connectome_loader.py
│       │   ├── annotation_loader.py
│       │   ├── neurotransmitter_loader.py
│       │   ├── dataset_validator.py
│       │   └── preprocessing.py
│       │
│       ├── connectome/
│       │   ├── graph_builder.py
│       │   ├── adjacency_matrix.py
│       │   ├── circuit_extractor.py
│       │   ├── connectivity_analysis.py
│       │   └── network_visualizer.py
│       │
│       ├── brain/
│       │   ├── neuron_model.py
│       │   ├── synapse_model.py
│       │   ├── neural_population.py
│       │   ├── brain_simulator.py
│       │   └── neural_activity.py
│       │
│       ├── sensory/
│       │   ├── screen_capture.py
│       │   ├── obstacle_detector.py
│       │   ├── lane_detector.py
│       │   ├── distance_estimator.py
│       │   ├── visual_encoder.py
│       │   └── sensory_mapping.py
│       │
│       ├── learning/
│       │   ├── dopamine.py
│       │   ├── reward_prediction.py
│       │   ├── eligibility_trace.py
│       │   ├── synaptic_plasticity.py
│       │   ├── reinforcement_baseline.py
│       │   └── mutual_information.py
│       │
│       ├── motor/
│       │   ├── motor_decoder.py
│       │   ├── action_selection.py
│       │   └── game_controller.py
│       │
│       ├── environment/
│       │   ├── game_state.py
│       │   ├── subway_environment.py
│       │   ├── reward_function.py
│       │   └── environment_adapter.py
│       │
│       ├── evaluation/
│       │   ├── performance_metrics.py
│       │   ├── experiment_runner.py
│       │   ├── statistical_analysis.py
│       │   └── comparison.py
│       │
│       └── utils/
│           ├── logging.py
│           ├── reproducibility.py
│           └── checkpoint.py
│
├── experiments/
│   ├── baseline/
│   ├── connectome/
│   ├── plasticity/
│   ├── random_network/
│   └── results/
│
├── tests/
│   ├── test_data_loader.py
│   ├── test_connectome.py
│   ├── test_neuron.py
│   ├── test_synapse.py
│   ├── test_learning.py
│   ├── test_sensory.py
│   └── test_motor.py
│
├── scripts/
│   ├── inspect_dataset.py
│   ├── preprocess_dataset.py
│   ├── build_connectome.py
│   ├── run_simulation.py
│   └── run_experiment.py
│
└── docs/
    ├── ARCHITECTURE.md
    ├── MATHEMATICS.md
    ├── DATASET.md
    ├── EXPERIMENTS.md
    └── RESEARCH_NOTES.md
```

---

# 6. Mathematical Foundation

This project will use mathematical models from computational neuroscience, graph theory, reinforcement learning, and information theory.

All equations and their assumptions will be documented.

## 6.1 Connectome Representation

We represent the biological connectome as a directed weighted graph:

[
G=(V,E,W)
]

Where:

* (V) represents neurons.
* (E) represents directed synaptic connections.
* (W) represents connection weights.

The adjacency matrix is:

[
A_{ij}=
\begin{cases}
1 & \text{if neuron }i\text{ connects to neuron }j\
0 & \text{otherwise}
\end{cases}
]

A weighted representation can use:

[
W_{ij}=f(N_{ij})
]

Where (N_{ij}) is the synapse count between neurons (i) and (j).

A possible initial transformation is:

[
W_{ij}=\log(1+N_{ij})
]

This reduces the influence of extremely large synapse counts.

However, this is a computational transformation, not a biologically measured synaptic conductance.

Where neurotransmitter predictions are available, we can introduce sign or receptor-informed properties.

For example:

[
W_{ij}^{signed}=s_{ij}W_{ij}
]

Where:

[
s_{ij}\in{-1,+1}
]

This is a simplified excitatory/inhibitory representation.

Neurotransmitter identity alone does not always determine the postsynaptic effect. Receptor information and cellular context matter.

## 6.2 Leaky Integrate-and-Fire Neuron Model

Our initial spiking neuron model will use the Leaky Integrate-and-Fire model.

The membrane equation is:

-g_L(V-E_L)+I_{syn}+I_{ext}
]

Where:

* (C_m): Membrane capacitance.
* (V): Membrane potential.
* (g_L): Leak conductance.
* (E_L): Resting potential.
* (I_{syn}): Synaptic input current.
* (I_{ext}): External input current.

When the membrane voltage reaches the firing threshold:

[
V\geq V_{th}
]

The neuron generates a spike.

After firing:

[
V\leftarrow V_{reset}
]

The neuron then enters a refractory period.

This allows us to simulate neural activity over time.

**Why LIF?**

It provides a computationally efficient starting point for large-scale spiking experiments.

It does not reproduce every biological property of a fly neuron, so we will investigate more detailed models where necessary.

## 6.3 Synaptic Transmission

A simplified current-based synaptic model is:

[
I_{syn,i}(t)=
\sum_j W_{ji}s_j(t)
]

Where:

* (W_{ji}) is the synaptic weight from neuron (j) to neuron (i).
* (s_j(t)) represents the presynaptic spike signal.

For a more detailed model, we can introduce synaptic conductances:

[
I_{syn}=g_{syn}(t)(E_{syn}-V)
]

This allows excitatory and inhibitory synaptic currents to depend on membrane potential.

The initial implementation will use a simplified model, followed by more biologically informed alternatives.

## 6.4 Neural Population Activity

We need to understand how individual neurons collectively represent information.

For a population of neurons:

[
R(t)=\frac{1}{N}\sum_{i=1}^{N}S_i(t)
]

Where:

* (N) is the number of neurons.
* (S_i(t)) represents spike activity.

For practical analysis, we will also calculate firing rates over a time window:

[
FR_i=\frac{\text{Number of spikes}}{\text{Observation time}}
]

This will help identify activity patterns associated with game states.

---

# 7. Sensory Encoding Mathematics

The simulated brain requires sensory input.

The game environment will provide observations that must be translated into neural signals.

Initial sensory variables:

[
X=[x_1,x_2,\ldots,x_n]
]

Possible features:

* Obstacle presence.
* Obstacle lane.
* Distance to obstacle.
* Obstacle type.
* Coin presence.
* Current character lane.
* Available movement opportunities.

For continuous sensory values, we can use population coding.

For example, a distance value (d) can be converted into neuronal firing rates using Gaussian tuning functions:

[
r_i(d)=r_{max}
\exp\left(
-\frac{(d-\mu_i)^2}{2\sigma_i^2}
\right)
]

Where:

* (r_i(d)) is the response of neuron (i).
* (\mu_i) is its preferred distance.
* (\sigma_i) controls tuning width.
* (r_{max}) is maximum firing rate.

These firing rates can drive simulated sensory neurons.

We will initially use a simplified state encoder before attempting image-to-neuron visual processing.

---

# 8. Motor Decoding

The brain must convert neural activity into game actions.

Possible outputs:

[
A=
{
LEFT,RIGHT,JUMP,ROLL,NO_ACTION
}
]

A simple population-based action decoder can use:

[
a_t=\arg\max_k R_k(t)
]

Where (R_k(t)) is the activity of the neural population assigned to action (k).

However, these action populations must be grounded in identifiable neural pathways where possible.

Initially, the decoder will be an experimental interface rather than a claim that individual fly neurons correspond directly to keyboard keys.

Later, we will investigate descending neurons and motor pathways.

---

# 9. Dopamine-Inspired Learning

This is one of the most important experimental components.

A fixed connectome does not automatically learn a new task.

We will investigate whether biologically inspired plasticity can adapt synaptic strengths while preserving the original connectivity structure.

## 9.1 Reward Signal

The game environment produces a reward:

[
r_t
]

Possible reward components:

* Positive reward for survival.
* Positive reward for collecting coins.
* Positive reward for successfully avoiding obstacles.
* Negative reward for collisions.
* Negative reward for unnecessary or ineffective actions.

The reward function must avoid encouraging unintended behaviour.

For example, surviving longer should matter more than repeatedly collecting easy rewards while avoiding progress.

## 9.2 Temporal-Difference Reward Prediction Error

We can use:

[
\delta_t=
r_t+\gamma V(s_{t+1})-V(s_t)
]

Where:

* (r_t) is the received reward.
* (\gamma) is the discount factor.
* (V(s_t)) is the estimated value of the current state.
* (V(s_{t+1})) is the estimated value of the next state.

This provides a computational reward prediction error.

We can use it as an experimental dopamine-like teaching signal.

It should not be interpreted as a complete model of biological dopamine signalling.

## 9.3 Eligibility Traces

Synaptic eligibility traces allow recent neural activity to influence later learning.

A simplified eligibility model:

-\frac{e_{ij}}{\tau_e}
+
F_{ij}(t)
]

Where:

* (e_{ij}) is the eligibility trace.
* (\tau_e) is its decay time constant.
* (F_{ij}(t)) represents a pre/post-synaptic activity-dependent term.

## 9.4 Three-Factor Plasticity Rule

Our initial experimental learning rule will be:

[
\boxed{
\Delta w_{ij}=\eta\delta_t e_{ij}
}
]

Where:

* (\eta) is the learning rate.
* (\delta_t) is the reward prediction error.
* (e_{ij}) is the eligibility trace.

This combines:

1. Presynaptic and postsynaptic activity.
2. A temporary synaptic eligibility signal.
3. A global reward-related teaching signal.

We will also implement weight constraints:

[
w_{min}\leq w_{ij}\leq w_{max}
]

This prevents uncontrolled weight growth.

### Important experimental constraint

The original connectome topology should remain unchanged in our primary experiments.

We will initially modify synaptic strengths rather than inventing or deleting biological connections.

Structural plasticity can be investigated separately.

---

# 10. Shannon Mutual Information

Mutual Information is an important part of our analysis framework.

We originally considered using it to identify which dataset features are useful for AI training.

In FLY-SURFER, we will extend that idea to investigate information relationships between sensory inputs, neural activity, game states, and actions.

## 10.1 Discrete Mutual Information

The mathematical definition is:

[
\boxed{
I(X;Y)=
\sum_x\sum_y
P(x,y)
\log_2
\left(
\frac{P(x,y)}{P(x)P(y)}
\right)
}
]

Where:

* (P(x,y)) is the joint probability distribution.
* (P(x)) and (P(y)) are marginal probability distributions.
* The logarithm is base 2.
* The result is measured in bits.

Terms with zero joint probability are treated as zero.

Mutual Information can also be expressed as:

[
I(X;Y)=H(X)-H(X|Y)
]

Or:

[
I(X;Y)=H(Y)-H(Y|X)
]

This measures the reduction in uncertainty about one variable when the other is known.

## 10.2 Applications in FLY-SURFER

### Experiment 1: Sensory Information

Calculate:

[
I(S;O)
]

Where:

* (S) is a sensory variable.
* (O) is an obstacle or game-state variable.

Objective:

Investigate whether the sensory encoding preserves information about relevant game events.

### Experiment 2: Neural Information

Calculate:

[
I(N;G)
]

Where:

* (N) is neural activity.
* (G) is a game-state variable.

Objective:

Identify neural populations whose activity contains information about particular game states.

### Experiment 3: Action Information

Calculate:

[
I(N;A)
]

Where:

* (N) is neural population activity.
* (A) is the selected game action.

Objective:

Investigate whether neural activity contains information about the motor decisions produced by the system.

### Experiment 4: Learning Progress

Compare information measures before and after learning.

For example:

[
\Delta I=
I_{after}(N;G)-I_{before}(N;G)
]

This can help us investigate whether neural representations change during learning.

However, an increase in mutual information does not automatically imply better gameplay or more intelligent behaviour.

## 10.3 Continuous Variables

Game distances, membrane voltages, and firing rates are continuous variables.

The discrete formula cannot simply be applied to raw continuous measurements.

We will investigate:

* Histogram-based discretisation.
* Nearest-neighbour mutual information estimators.
* Appropriate continuous-variable estimators.

We must also account for estimation bias, sample size, and temporal dependencies.

## 10.4 Feature Selection

We can use Scikit-learn's `mutual_info_classif` to estimate feature relevance for discrete action labels.

Example:

```python
from sklearn.feature_selection import mutual_info_classif

scores = mutual_info_classif(X_train, y_train)

for name, score in zip(feature_names, scores):
    print(name, score)
```

This will be used as an analysis and feature-selection experiment.

Mutual Information is not our primary neural training algorithm.

It does not independently teach the connectome to play the game.

---

# 11. Game Environment

## 11.1 Initial Environment

Before using the actual Subway Surfers browser game, we will create a simplified experimental environment.

The environment will contain:

* Three lanes.
* A moving character.
* Obstacles.
* Trains.
* Barriers.
* Coins.
* Jumping.
* Rolling.
* Lane switching.
* Collision detection.
* Reward generation.

This allows us to test the neural architecture without browser latency or visual-processing complications.

## 11.2 State Representation

The initial game state can be represented as:

[
s_t=
[
L_t,
O_t,
D_t,
C_t,
V_t
]
]

Where:

* (L_t): Character lane.
* (O_t): Obstacle information.
* (D_t): Obstacle distances.
* (C_t): Coin information.
* (V_t): Game speed.

The actual implementation may use richer observations.

## 11.3 Action Space

```text
LEFT
RIGHT
JUMP
ROLL
NO_ACTION
```

## 11.4 Reward Function

An initial experimental reward function:

\lambda R_{collision}
]

Where the coefficients control the importance of each component.

We will tune these coefficients experimentally.

We must ensure the reward function does not create undesirable shortcuts.

---

# 12. Training Strategy

We will not begin by attempting to train the entire brain.

Training and simulation will proceed through progressively larger experiments.

## Training Stage 1: Neural Functionality

Objective:

Establish that the network can receive inputs and generate neural activity.

Tasks:

* Load a small connectome.
* Construct its graph.
* Initialise neurons.
* Simulate membrane dynamics.
* Observe spikes.
* Validate synaptic transmission.

Success criteria:

* Neurons produce spikes under appropriate input.
* Synaptic connections influence downstream activity.
* The simulation remains numerically stable.

## Training Stage 2: Sensory-Motor Mapping

Objective:

Establish that sensory signals can produce distinguishable motor outputs.

Tasks:

* Encode left, centre, and right obstacles.
* Introduce neural input patterns.
* Simulate activity.
* Decode action populations.
* Test whether outputs are reproducible.

Success criteria:

* Different inputs produce measurable differences in network activity.
* The decoder produces valid actions.
* The system responds within an acceptable simulation time.

This stage validates the interface, not autonomous learning.

## Training Stage 3: Fixed Connectome Experiment

Objective:

Investigate what behaviour can emerge without changing synaptic strengths.

Tasks:

* Preserve initial synaptic weights.
* Provide game-state inputs.
* Observe neural responses.
* Measure action distributions.
* Evaluate game performance.

This is our fixed-network baseline.

## Training Stage 4: Dopamine-Inspired Plasticity

Objective:

Investigate whether reward-modulated plasticity improves behaviour.

Tasks:

* Introduce eligibility traces.
* Introduce reward prediction error.
* Update eligible synaptic strengths.
* Preserve connectivity topology.
* Record every weight update.
* Evaluate performance across episodes.

Success criteria:

* Learning updates remain numerically stable.
* Weight changes are measurable.
* Performance can be compared against the fixed-network baseline.

## Training Stage 5: Random Connectivity Comparison

Objective:

Determine whether the biological network structure contributes to performance.

We will create control networks with:

* Randomised connectivity.
* Degree-preserving rewired connectivity where feasible.
* The same number of neurons.
* Comparable connection counts.
* Identical sensory and motor interfaces.
* The same learning rules.

This will help distinguish the contribution of network architecture from the contribution of the learning algorithm.

## Training Stage 6: Actual Subway Surfers

Objective:

Connect the validated neural system to the browser game.

Tasks:

* Capture gameplay frames.
* Extract relevant observations.
* Encode sensory inputs.
* Run neural simulation.
* Decode motor outputs.
* Send permitted keyboard actions.
* Collect gameplay feedback.
* Record performance.

The actual browser environment will be integrated only after the simplified environment works.

---

# 13. Experimental Design

We will conduct controlled comparisons.

| Experiment | Network                                        | Learning                     |
| ---------- | ---------------------------------------------- | ---------------------------- |
| A          | Biological connectome                          | Fixed weights                |
| B          | Biological connectome                          | Dopamine-inspired plasticity |
| C          | Random network                                 | Fixed weights                |
| D          | Random network                                 | Dopamine-inspired plasticity |
| E          | Conventional artificial neural network         | Conventional training        |
| F          | Biological connectivity with trainable readout | Readout training             |

The conventional model provides a performance baseline.

The trainable-readout experiment helps determine whether useful behaviour can emerge from fixed biological neural activity without modifying the underlying connectome.

## 13.1 Evaluation Metrics

We will measure:

| Metric                  | What it tells us                         |
| ----------------------- | ---------------------------------------- |
| Survival time           | How long the agent survives              |
| Distance travelled      | Progress through the game                |
| Coins collected         | Collection performance                   |
| Collision count         | Failure frequency                        |
| Obstacles avoided       | Hazard avoidance                         |
| Action accuracy         | Correctness against a defined reference  |
| Training stability      | Whether learning remains controlled      |
| Inference latency       | Time required to produce an action       |
| Neural firing rates     | Activity of simulated neurons            |
| Synaptic weight changes | Degree of plasticity                     |
| Mutual Information      | Information relationships in the network |

We will use multiple random seeds and repeated trials.

Results will be reported using means, standard deviations, and appropriate statistical comparisons.

We will not claim that a network is superior based on a single successful game.

---

# 14. Detailed Development Phases

## PHASE 0 — Environment and Dataset Audit

**Goal:** Establish the project environment and understand the downloaded data.

Tasks:

* Create the repository.
* Set up Python.
* Create a virtual environment.
* Install basic scientific libraries.
* Identify every downloaded dataset file.
* Inspect file formats and schemas.
* Check dataset versions.
* Verify neuron identifiers.
* Verify connection identifiers.
* Inspect missing values.
* Identify annotations and neurotransmitter fields.
* Document the dataset source and citation requirements.

Files:

```text
datasets/README.md
src/fly_surfer/data/connectome_loader.py
src/fly_surfer/data/dataset_validator.py
scripts/inspect_dataset.py
configs/brain_config.yaml
```

Completion criteria:

* Every downloaded dataset is identified.
* Connectivity schema is understood.
* Neuron identifiers are validated.
* Original data remains unchanged.
* A reproducible dataset inventory exists.

## PHASE 1 — Connectome Processing

**Goal:** Convert downloaded biological data into a computational network.

Tasks:

1. Load filtered connectivity data.
2. Load neuronal annotations.
3. Load neurotransmitter predictions.
4. Match identifiers across datasets.
5. Remove or flag invalid records.
6. Construct directed connectivity edges.
7. Calculate synapse counts.
8. Construct sparse adjacency matrices.
9. Extract selected neuronal populations.
10. Visualise small network sections.

Files:

```text
src/fly_surfer/data/preprocessing.py
src/fly_surfer/connectome/graph_builder.py
src/fly_surfer/connectome/adjacency_matrix.py
src/fly_surfer/connectome/circuit_extractor.py
src/fly_surfer/connectome/connectivity_analysis.py
src/fly_surfer/connectome/network_visualizer.py
```

Completion criteria:

* A validated directed graph exists.
* Neurons and connections can be queried.
* Sparse connectivity matrices are generated.
* Neuronal annotations are associated with graph nodes.
* The selected biological circuit can be exported.

## PHASE 2 — Spiking Neural Network

**Goal:** Make the reconstructed biological network computationally active.

Tasks:

1. Implement LIF neurons.
2. Implement synaptic transmission.
3. Introduce excitatory and inhibitory properties where supported.
4. Initialise neural populations.
5. Introduce time-stepped simulation.
6. Generate spike trains.
7. Monitor membrane potentials.
8. Record firing rates.
9. Validate numerical stability.
10. Compare small simulations against expected mathematical behaviour.

Files:

```text
src/fly_surfer/brain/neuron_model.py
src/fly_surfer/brain/synapse_model.py
src/fly_surfer/brain/neural_population.py
src/fly_surfer/brain/brain_simulator.py
src/fly_surfer/brain/neural_activity.py
```

Completion criteria:

* Neural activity can be simulated.
* Synaptic inputs affect neuronal behaviour.
* Spike trains can be recorded.
* Simulation parameters are configurable.
* The system can run reproducibly.

## PHASE 3 — Sensory System

**Goal:** Translate game observations into simulated neural inputs.

Tasks:

1. Build the game observation interface.
2. Detect obstacles.
3. Identify lanes.
4. Estimate distances.
5. Identify coins.
6. Encode obstacle categories.
7. Convert continuous variables into population-coded activity.
8. Map observations to selected sensory populations.
9. Validate sensory responses.

Files:

```text
src/fly_surfer/sensory/screen_capture.py
src/fly_surfer/sensory/obstacle_detector.py
src/fly_surfer/sensory/lane_detector.py
src/fly_surfer/sensory/distance_estimator.py
src/fly_surfer/sensory/visual_encoder.py
src/fly_surfer/sensory/sensory_mapping.py
```

Completion criteria:

* Game observations can be extracted.
* Sensory features can be encoded.
* Encoded signals can activate simulated neurons.
* Different game situations produce distinguishable input patterns.

## PHASE 4 — Motor System

**Goal:** Convert neural activity into game actions.

Tasks:

1. Investigate descending pathways.
2. Identify relevant neuronal populations.
3. Investigate available motor annotations.
4. Design an experimental motor mapping.
5. Implement action decoding.
6. Add action thresholds.
7. Prevent conflicting simultaneous actions.
8. Add action timing constraints.
9. Test the complete sensory-to-motor loop.

Files:

```text
src/fly_surfer/motor/motor_decoder.py
src/fly_surfer/motor/action_selection.py
src/fly_surfer/motor/game_controller.py
```

Completion criteria:

* Neural activity produces valid actions.
* Action selection is reproducible.
* The controller handles action timing.
* Sensory and motor systems operate together.

## PHASE 5 — Reward and Synaptic Plasticity

**Goal:** Introduce learning mechanisms.

Tasks:

1. Implement reward signals.
2. Implement reward prediction.
3. Implement temporal-difference error.
4. Implement eligibility traces.
5. Implement three-factor plasticity.
6. Add weight bounds.
7. Record synaptic changes.
8. Compare fixed and adaptive networks.
9. Investigate dopamine-inspired learning parameters.

Files:

```text
src/fly_surfer/learning/dopamine.py
src/fly_surfer/learning/reward_prediction.py
src/fly_surfer/learning/eligibility_trace.py
src/fly_surfer/learning/synaptic_plasticity.py
```

Completion criteria:

* Reward signals reach the learning mechanism.
* Synaptic updates are measurable.
* Weight changes remain controlled.
* Original connectivity is preserved in the primary experiment.
* Fixed and plastic networks can be compared.

## PHASE 6 — Information-Theoretic Analysis

**Goal:** Investigate how information is represented and processed by the simulated brain.

Tasks:

1. Implement discrete Mutual Information.
2. Implement continuous-variable estimators.
3. Analyse sensory information.
4. Analyse neural population activity.
5. Analyse neural activity against game states.
6. Analyse neural activity against selected actions.
7. Compare before-learning and after-learning activity.
8. Identify informative neural populations.
9. Visualise information relationships.

Files:

```text
src/fly_surfer/learning/mutual_information.py
notebooks/04_mutual_information.ipynb
```

Completion criteria:

* MI calculations are validated.
* Estimation methods are documented.
* Neural activity can be analysed.
* Before-and-after learning comparisons are available.

## PHASE 7 — Controlled Game Environment

**Goal:** Test the simulated brain in a manageable game environment.

Tasks:

1. Build a three-lane environment.
2. Implement character movement.
3. Implement obstacle generation.
4. Implement collisions.
5. Implement coins.
6. Implement jumping and rolling.
7. Implement game rewards.
8. Connect sensory inputs.
9. Connect motor outputs.
10. Record complete game episodes.

Files:

```text
src/fly_surfer/environment/game_state.py
src/fly_surfer/environment/subway_environment.py
src/fly_surfer/environment/reward_function.py
src/fly_surfer/environment/environment_adapter.py
```

Completion criteria:

* The game environment operates independently.
* The neural network controls the character.
* Game rewards are recorded.
* Episodes can be reproduced.

## PHASE 8 — Training and Comparison

**Goal:** Conduct the main scientific experiments.

Tasks:

* Train the biological network with plasticity.
* Test the fixed biological network.
* Test randomised networks.
* Test a conventional AI baseline.
* Compare performance across multiple episodes.
* Analyse firing patterns.
* Analyse weight changes.
* Analyse information measures.
* Record experimental configurations.
* Generate graphs and reports.

Files:

```text
experiments/baseline/
experiments/connectome/
experiments/plasticity/
experiments/random_network/
experiments/results/
src/fly_surfer/evaluation/
```

Completion criteria:

* All major experimental conditions are implemented.
* Results are reproducible.
* Comparisons use equivalent environments.
* Statistical results are documented.

## PHASE 9 — Actual Subway Surfers Integration

**Goal:** Deploy the validated neural controller into the actual browser game.

Tasks:

1. Inspect the browser game interface.
2. Implement screen capture.
3. Implement visual observation extraction.
4. Connect sensory encoding.
5. Run the neural simulation.
6. Connect motor decoding.
7. Send permitted keyboard actions.
8. Collect rewards and game-state feedback.
9. Record gameplay.
10. Evaluate performance.

Files:

```text
src/fly_surfer/sensory/screen_capture.py
src/fly_surfer/environment/environment_adapter.py
src/fly_surfer/motor/game_controller.py
```

Completion criteria:

* The neural controller can observe the browser game.
* The simulated brain produces actions.
* Actions are executed correctly.
* Game feedback is recorded.
* Gameplay performance can be measured.

---

# 15. Dataset Management

Biological datasets can become very large.

We will therefore separate raw, processed, and experimental data.

| Directory               | Purpose                             |
| ----------------------- | ----------------------------------- |
| datasets/raw            | Original downloaded datasets        |
| datasets/processed      | Validated and transformed datasets  |
| datasets/samples        | Small test datasets                 |
| experiments/results     | Experimental outputs                |
| experiments/checkpoints | Simulation and learning checkpoints |

### Important rules

1. Never overwrite original FlyWire files.
2. Preserve original neuron identifiers.
3. Record the dataset version.
4. Record preprocessing parameters.
5. Record every connectivity transformation.
6. Record simulation parameters.
7. Keep large datasets outside Git.
8. Use Git LFS only when appropriate.
9. Use manifests and download instructions for large files.
10. Never publish restricted or improperly redistributed data.

The GitHub repository will contain the code, documentation, configurations, and small reproducible examples.

Large biological datasets will remain separately stored.

---

# 16. Reproducibility

Every experiment must record:

* Dataset version.
* Dataset source.
* Selected neuron population.
* Number of neurons.
* Number of connections.
* Neuron model.
* Simulation time step.
* Synaptic parameters.
* Learning rate.
* Discount factor.
* Reward configuration.
* Random seed.
* Training episodes.
* Hardware configuration.
* Software versions.

A configuration file should allow experiments to be repeated without manually changing source code.

Example:

```yaml
brain:
  neuron_model: LIF
  simulation_dt: 0.001
  use_connectome: true

connectome:
  dataset: FAFB
  connection_type: filtered
  preserve_topology: true

learning:
  enabled: true
  method: three_factor_plasticity
  learning_rate: 0.001
  gamma: 0.99

environment:
  lanes: 3
  actions:
    - LEFT
    - RIGHT
    - JUMP
    - ROLL
    - NO_ACTION

experiment:
  episodes: 100
  random_seed: 42
```

These are initial configuration examples, not scientifically optimised parameters.

---

# 17. Expected Challenges

This project has several major technical challenges.

| Challenge                        | Proposed solution                           |
| -------------------------------- | ------------------------------------------- |
| Extremely large connectome       | Begin with selected circuits                |
| High memory consumption          | Sparse matrices and efficient data formats  |
| Missing physiological parameters | Documented computational assumptions        |
| Unknown sensory mapping          | Build and validate an explicit encoder      |
| Unknown motor mapping            | Investigate descending pathways             |
| Unstable neural activity         | Parameter tuning and numerical validation   |
| Weak learning performance        | Compare learning rules and baselines        |
| Browser latency                  | Start with a controlled environment         |
| Large experimental outputs       | Store results separately                    |
| Information estimation bias      | Use suitable estimators and repeated trials |

## 17.1 Computational Constraints

A full connectome-scale simulation may exceed the capabilities of our available hardware.

Therefore, our first objective is not to simulate every neuron.

We will progressively increase network size while measuring:

* RAM usage.
* CPU utilisation.
* Simulation speed.
* Neural update time.
* Memory requirements.

We will consider GPU acceleration or specialised simulation tools only when justified by benchmarking.

---

# 18. Project Milestones

| Milestone | Deliverable                             |
| --------- | --------------------------------------- |
| M0        | Dataset inventory and environment setup |
| M1        | Processed biological connectivity graph |
| M2        | Functional spiking neural network       |
| M3        | Sensory encoding                        |
| M4        | Motor decoding                          |
| M5        | Reward-modulated learning               |
| M6        | Mutual Information analysis             |
| M7        | Controlled game environment             |
| M8        | Comparative experiments                 |
| M9        | Actual Subway Surfers integration       |

### First Major Achievement

A selected section of the real FlyWire connectome is reconstructed as a functioning computational neural network.

### Second Major Achievement

The simulated network receives game-state information and produces measurable action outputs.

### Third Major Achievement

The network learns through reward-modulated synaptic plasticity.

### Final Achievement

The connectome-derived system controls Subway Surfers and its performance is evaluated against appropriate control networks.

---

# 19. Research and Scientific Integrity

FLY-SURFER is an experimental research project.

We must distinguish:

* Biological observations.
* Computational approximations.
* Experimental assumptions.
* Measured results.
* Hypotheses.

We will not describe the simulated system as a complete biological brain.

We will not claim that dopamine-inspired plasticity is an exact reproduction of biological dopamine signalling.

We will not claim that increased Mutual Information necessarily represents increased intelligence.

We will document negative results as well as successful experiments.

### FlyWire Attribution

If FlyWire data is used in publications, presentations, or other research outputs, the official FlyWire citation guidelines and principles must be followed.

References:

* [FlyWire Citation Guidelines](https://codex.flywire.ai/about_flywire)
* [FlyWire Principles](https://flywire.ai/principles.html)
* [FlyWire Data Portal](https://codex.flywire.ai/)
* [Dorkenwald et al. (2024), FlyWire connectome publication](https://www.nature.com/articles/s41586-024-07558-y)
* [FlyWire Annotations](https://github.com/flyconnectome/flywire_annotations)

The exact dataset version and retrieval date must be recorded because the live portal is continually updated.

---

# 20. Expected Final Outcome

At the end of this project, we aim to have:

1. A computationally reconstructed fruit fly neural network.
2. A connectome-derived spiking neural simulation.
3. A sensory interface that translates game observations into neural signals.
4. A motor interface that converts neural activity into game actions.
5. A dopamine-inspired synaptic learning mechanism.
6. An information-theoretic analysis framework.
7. A controlled game environment.
8. Comparative experiments against random and conventional networks.
9. A working integration with Subway Surfers.
10. A reproducible experimental report.

The project will also provide opportunities to investigate how biological connectivity, neural dynamics, information processing, and learning mechanisms interact.

---

# 21. Initial Installation

Our initial environment will use Python 3.11.

Create a virtual environment:

```bash
python -m venv .venv
```

Activate on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install the initial scientific stack:

```bash
pip install numpy pandas scipy pyarrow networkx
```

Install the neural simulation framework:

```bash
pip install brian2
```

Install machine learning and analysis tools:

```bash
pip install torch scikit-learn matplotlib seaborn
```

Install game interaction and testing tools:

```bash
pip install opencv-python mss pyautogui gymnasium pytest
```

Additional browser automation dependencies will be installed when the browser integration phase begins.

We will later pin tested versions in `requirements.txt` or `pyproject.toml`.

---

# 22. Immediate Next Steps

We will not attempt to implement all nine phases simultaneously.

Our immediate development sequence is:

**Step 1:** Inspect every downloaded FlyWire file.

**Step 2:** Identify the schema of the filtered connectivity dataset.

**Step 3:** Identify the neuron IDs and annotation fields.

**Step 4:** Build a dataset inventory and validation script.

**Step 5:** Construct a small directed connectivity graph.

**Step 6:** Visualise the graph and verify that its connections match the original data.

**Step 7:** Implement and test the first LIF neuron.

**Step 8:** Connect a small group of neurons and observe their activity.

Only after these steps will we begin building the larger simulated brain.

---

# 23. Project Philosophy

> We are not building an artificial brain that merely imitates the appearance of biological intelligence. We are investigating whether the structural organisation of a real biological neural network can be computationally repurposed to produce useful behaviour in an unfamiliar environment.

The central experiment is to preserve biologically derived connectivity, introduce appropriate sensory and motor interfaces, and investigate how learning changes the behaviour of the resulting system.

**From a fruit fly connectome to a game-playing neural system.**

**From biological connections to computational behaviour.**

**From neural activity to autonomous action.**

---

<p align="center">
  <strong>FLY-SURFER</strong><br>
  A Computational Neuroscience Experiment
</p>
